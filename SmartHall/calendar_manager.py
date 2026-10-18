from caldav import DAVClient
from datetime import datetime, timedelta
import json
import pytz
import logging
import asyncio

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

logger = logging.getLogger("SmartHall")


class CalendarManager:
    def __init__(self):
        self.client = DAVClient(
            url=config["calendar"]["url"],
            username=config["calendar"]["username"],
            password=config["calendar"]["password"]
        )
        self.principal = self.client.principal()
        self.calendars = self.principal.calendars()

        if not self.calendars:
            logger.error("Календари не найдены")
            raise ValueError("Не удалось найти календари")

        self.calendar = self.calendars[0]
        self.tz = pytz.timezone("Europe/Moscow")

        self.turn_on_before = timedelta(minutes=config["schedule"]["turn_on_before_minutes"])
        self.turn_off_after = timedelta(minutes=config["schedule"]["turn_off_after_minutes"])

    def get_events_with_timing(self):
        now = datetime.now(self.tz)
        start = now - timedelta(hours=2)
        end = now + timedelta(hours=24)

        try:
            events = self.calendar.date_search(start=start, end=end)
        except Exception as e:
            logger.error(f"Ошибка получения событий: {e}")
            return [], []

        turn_on_events = []
        turn_off_events = []

        turn_on_commands = ["включить", "вкл", "on", "start", "старт"]
        turn_off_commands = ["выключить", "выкл", "off", "stop", "стоп"]

        for event in events:
            try:
                vevent = event.vobject_instance.vevent
                summary = vevent.summary.value
                dtstart = vevent.dtstart.value
                dtend = vevent.dtend.value

                if isinstance(dtstart, datetime) and dtstart.tzinfo is None:
                    dtstart = self.tz.localize(dtstart)
                if isinstance(dtend, datetime) and dtend.tzinfo is None:
                    dtend = self.tz.localize(dtend)

                event_lower = summary.lower()

                if any(cmd in event_lower for cmd in turn_on_commands):
                    turn_on_time = dtstart - self.turn_on_before
                    turn_off_time = dtend + self.turn_off_after
                    turn_on_events.append((turn_on_time, turn_off_time, summary, dtstart, dtend))

                elif any(cmd in event_lower for cmd in turn_off_commands):
                    turn_off_time = dtend + self.turn_off_after
                    turn_off_events.append((turn_off_time, summary, dtstart, dtend))

            except Exception as e:
                logger.warning(f"Ошибка обработки события: {e}")
                continue

        return turn_on_events, turn_off_events

    def get_current_actions(self):
        now = datetime.now(self.tz)

        turn_on_events, turn_off_events = self.get_events_with_timing()

        actions = {"turn_on": [], "turn_off": []}

        for turn_on_time, turn_off_time, summary, event_start, event_end in turn_on_events:
            if turn_on_time <= now <= event_end:
                actions["turn_on"].append((summary, event_start))
                logger.info(f"Включение активно: {summary} (до {event_end.strftime('%H:%M')})")

            if event_end <= now <= turn_off_time + timedelta(minutes=30):
                actions["turn_off"].append((summary, event_end))
                logger.info(f"Автовыключение после: {summary}")

        for turn_off_time, summary, event_start, event_end in turn_off_events:
            if event_end <= now <= turn_off_time + timedelta(minutes=30):
                actions["turn_off"].append((summary, event_end))
                logger.info(f"Выключение по событию: {summary}")

        return actions