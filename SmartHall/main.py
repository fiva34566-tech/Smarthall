import asyncio
from tapo_manager import TapoManager
from calendar_manager import CalendarManager
import logging
import os
import sys
import json
from datetime import datetime

os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("SmartHall")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        os.path.join("logs", "smart_hall.log"),
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

CHECK_INTERVAL = config["schedule"]["check_interval_seconds"]


class SmartHallController:
    def __init__(self):
        self.calendar = CalendarManager()
        self.tapo = TapoManager()
        self.executed_on = set()
        self.executed_off = set()
        self.check_count = 0

    async def process_actions(self):
        self.check_count += 1

        actions = self.calendar.get_current_actions()

        for summary, event_time in actions["turn_on"]:
            action_id = f"on_{summary}_{event_time.isoformat()}"
            if action_id not in self.executed_on:
                logger.info(f">>> ВКЛЮЧЕНИЕ: {summary}")
                await self.tapo.connect_devices()
                await self.tapo.turn_on_all()
                self.executed_on.add(action_id)

        for summary, event_time in actions["turn_off"]:
            action_id = f"off_{summary}_{event_time.isoformat()}"
            if action_id not in self.executed_off:
                logger.info(f">>> ВЫКЛЮЧЕНИЕ: {summary}")
                await self.tapo.connect_devices()
                await self.tapo.turn_off_all()
                self.executed_off.add(action_id)

        if not actions["turn_on"] and not actions["turn_off"]:
            self.executed_on.clear()
            self.executed_off.clear()

    async def run(self):
        logger.info("SmartHall запущен")
        logger.info(f"Интервал проверки: {CHECK_INTERVAL} сек")
        logger.info(f"Включение за {config['schedule']['turn_on_before_minutes']} мин до события")
        logger.info(f"Выключение через {config['schedule']['turn_off_after_minutes']} мин после события")
        logger.info("-" * 50)

        while True:
            try:
                await self.process_actions()
                await asyncio.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Остановка...")
                break
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await asyncio.sleep(CHECK_INTERVAL)

        await self.tapo.disconnect_all()


if __name__ == "__main__":
    controller = SmartHallController()
    asyncio.run(controller.run())