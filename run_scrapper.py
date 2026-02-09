import asyncio
import logging
import aiohttp

from homeassistant.util import dt as dt_util
from custom_components.lviv_poweroff.loe_scrapper import LoeScrapper  # Замініть на правильний шлях
from custom_components.lviv_poweroff.const import PowerOffGroup
# from your_module.entities import PowerOffPeriod

original_init = aiohttp.ClientSession.__init__


def new_init(self, *args, **kwargs):
    if "connector" not in kwargs:
        # Force fail-safe SSL context
        kwargs["connector"] = aiohttp.TCPConnector(ssl=False)
    original_init(self, *args, **kwargs)


aiohttp.ClientSession.__init__ = new_init

# Налаштування логування
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


async def main():
    """Головна функція."""

    # Виберіть вашу групу
    group = PowerOffGroup.OneOne  # Змініть на вашу групу

    scraper = LoeScrapper(group=group.value, time_zone=dt_util.get_time_zone("Europe/Kyiv"))

    # Перевірка API
    if await scraper.validate():
        print("✓ API доступне")

        # Отримання графіків
        periods = await scraper.get_power_off_periods()

        for i, period in enumerate(periods, 1):
            print(f"{i}. {period.start_datetime} → {period.end_datetime}")
    else:
        print("✗ Помилка підключення")


if __name__ == "__main__":
    asyncio.run(main())
