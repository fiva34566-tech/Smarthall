import asyncio
from plugp100.new.device_factory import connect, DeviceConnectConfiguration
from plugp100.common.credentials import AuthCredential
import json
import logging

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

logger = logging.getLogger("SmartHall")


class TapoManager:
    def __init__(self):
        self.devices = []
        self.is_connected = False

    async def connect_devices(self):
        if self.is_connected:
            return

        for dev in config["tapo"]:
            try:
                credentials = AuthCredential(
                    username=dev["email"],
                    password=dev["password"]
                )

                device_config = DeviceConnectConfiguration(
                    host=dev["ip"],
                    credentials=credentials
                )

                device = await connect(device_config)
                await device.update()

                self.devices.append(device)
                self.is_connected = True

                status = "ВКЛ" if device.is_on else "ВЫКЛ"
                logger.info(f"Подключено: {dev['ip']} - {device.model} [{status}]")

            except Exception as e:
                logger.error(f"Ошибка подключения {dev['ip']}: {e}")

    async def turn_on_all(self):
        if not self.devices:
            return

        for device in self.devices:
            try:
                if not device.is_on:
                    await device.turn_on()
                    await asyncio.sleep(0.5)
                    await device.update()
                    logger.info("Устройство включено")

            except Exception as e:
                logger.error(f"Ошибка включения: {e}")

    async def turn_off_all(self):
        if not self.devices:
            return

        for device in self.devices:
            try:
                if device.is_on:
                    await device.turn_off()
                    await asyncio.sleep(0.5)
                    await device.update()
                    logger.info("Устройство выключено")

            except Exception as e:
                logger.error(f"Ошибка выключения: {e}")

    async def disconnect_all(self):
        for device in self.devices:
            try:
                if hasattr(device, '_session'):
                    await device._session.close()
            except Exception:
                pass

            try:
                if hasattr(device, '_client'):
                    await device._client.close()
            except Exception:
                pass

        self.devices.clear()
        self.is_connected = False
        await asyncio.sleep(0.2)