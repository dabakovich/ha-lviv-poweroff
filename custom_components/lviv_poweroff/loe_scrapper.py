"""Provides classes for scraping power off periods from the Lvivoblenergo API."""

import logging
import re
from datetime import datetime, timedelta

import aiohttp
from bs4 import BeautifulSoup

from .entities import PowerOffPeriod

URL = "https://api.loe.lviv.ua/api/menus?page=1&type=photo-grafic"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


_LOGGER = logging.getLogger(__name__)


class LoeScrapper:
    """Class for scraping power off periods from the Lvivoblenergo API."""

    def __init__(self, group: str) -> None:
        """Initialize the LoeScrapper object."""
        self.group = group

    async def validate(self) -> bool:
        """Validate that we can connect to the API."""
        try:
            async with (
                aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session,
                session.get(URL) as response,
            ):
                return response.status == 200
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error validating LOE API: %s", err)
            return False

    async def get_power_off_periods(self) -> list[PowerOffPeriod]:
        """Get power off periods."""
        try:
            async with (
                aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session,
                session.get(URL) as response,
            ):
                if response.status != 200:
                    _LOGGER.error("Failed to fetch LOE API: status %s", response.status)
                    return []

                data = await response.json()
                menu = None

                if "hydra:member" in data and data["hydra:member"]:
                    menu = data["hydra:member"][0]
                elif "menuItems" in data[0]:
                    menu = data[0]
                else:
                    _LOGGER.error("Invalid API response structure")
                    return []

                raw_periods = []

                # 1. Фільтруємо лише актуальні блоки (Today / Tomorrow)
                items_to_process = [item for item in menu["menuItems"] if item["name"] in ["Today", "Tomorrow"]]

                # Регулярний вираз для пошуку конкретної групи
                # Шукаємо "Група <значення_енуму>. Електроенергії немає з <часи>."
                group_pattern = rf"Група {re.escape(self.group)}\. Електроенергії немає з (.*?)\."
                date_pattern = re.compile(r"на (\d{2}\.\d{2}\.\d{4})")

                for item in items_to_process:
                    soup = BeautifulSoup(item["rawHtml"], "html.parser")
                    text = soup.get_text()

                    # Витягуємо дату з тексту (наприклад, 09.02.2026)
                    date_match = date_pattern.search(text)
                    if not date_match:
                        continue
                    date_str = date_match.group(1)

                    # Шукаємо рядок з графіком для нашої групи
                    group_match = re.search(group_pattern, text)
                    if group_match:
                        time_ranges = group_match.group(1).split(", ")

                        for r in time_ranges:
                            times = re.findall(r"(\d{2}:\d{2})", r)
                            if len(times) == 2:
                                start_str, end_str = times

                                start_dt = datetime.strptime(f"{date_str} {start_str}", "%d.%m.%Y %H:%M")

                                # Обробка "24:00": перетворюємо на 00:00 наступного дня
                                if end_str == "24:00":
                                    end_dt = datetime.strptime(f"{date_str} 00:00", "%d.%m.%Y %H:%M") + timedelta(
                                        days=1
                                    )
                                else:
                                    end_dt = datetime.strptime(f"{date_str} {end_str}", "%d.%m.%Y %H:%M")

                                raw_periods.append(PowerOffPeriod(start_datetime=start_dt, end_datetime=end_dt))

                # 2. Сортуємо та об'єднуємо суміжні періоди
                if not raw_periods:
                    return []

                raw_periods.sort(key=lambda x: x.start_datetime)

                merged_periods = []
                current = raw_periods[0]

                for i in range(1, len(raw_periods)):
                    nxt = raw_periods[i]
                    # Якщо кінець поточного періоду збігається з початком наступного — зливаємо
                    if current.end_datetime == nxt.start_datetime:
                        current.end_datetime = nxt.end_datetime
                    else:
                        merged_periods.append(current)
                        current = nxt

                merged_periods.append(current)

                return merged_periods

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Error fetching power off periods: %s", err)
            return []
