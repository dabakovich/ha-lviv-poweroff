"""Provides classes for scraping power off periods from the Lvivoblenergo API."""

import logging
import re
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup

from .const import PowerOffGroup
from .entities import PowerOffPeriod

URL = "https://api.loe.lviv.ua/api/menus?page=1&type=photo-grafic"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


_LOGGER = logging.getLogger(__name__)


class LoeScrapper:
    """Class for scraping power off periods from the Lvivoblenergo API."""

    def __init__(self, group: PowerOffGroup) -> None:
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
                if not data or "hydra:member" not in data or not data["hydra:member"]:
                    _LOGGER.error("Invalid API response structure")
                    return []

                # Get the main menu object
                menu = data["hydra:member"][0]

                # Candidates: the menu object itself and its menuItems
                candidates: list = []
                if "menuItems" in menu and isinstance(menu["menuItems"], list):
                    # Append items in reverse order (newest first)
                    candidates.extend(reversed(menu["menuItems"]))

                # Append the menu object itself as the LAST resort?
                # Actually, based on observation, the Menu object often has the *latest* aggregated data.
                # So we should probably check it FIRST or treat it as a candidate.
                # Let's verify: The menu.rawHtml had 18.01.2026. The menuItems might be history.
                # Prioritize the menu object itself by putting it first in the list to check.
                candidates.insert(0, menu)

                results: list[PowerOffPeriod] = []
                today = datetime.now().date()
                found_today = False
                found_tomorrow = False

                for item in candidates:
                    if found_today and found_tomorrow:
                        break

                    raw_html = item.get("rawHtml")
                    if not raw_html:
                        continue

                    date_match = re.search(r"на (\d{2}\.\d{2}\.\d{4})", raw_html)
                    if not date_match:
                        continue

                    try:
                        item_date = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
                    except ValueError:
                        continue

                    day_delta = (item_date - today).days

                    is_today = day_delta == 0
                    is_tomorrow = day_delta == 1

                    if is_today and not found_today:
                        periods = self._parse_html(raw_html)
                        # Add today flag
                        for p in periods:
                            p.today = True
                        results.extend(periods)
                        found_today = True

                    elif is_tomorrow and not found_tomorrow:
                        periods = self._parse_html(raw_html)
                        # Add today (False) flag
                        for p in periods:
                            p.today = False
                        results.extend(periods)
                        found_tomorrow = True

                return self._merge_periods(results)

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Error fetching power off periods: %s", err)
            return []

    def _parse_html(self, html: str) -> list[PowerOffPeriod]:
        """Parse HTML content to extract periods for the group."""
        periods: list[PowerOffPeriod] = []
        soup = BeautifulSoup(html, "html.parser")

        # Regex to find the group line.
        # Example: "Група 1.1. Електроенергії немає з 01:00 до 04:30, з 08:00 до 11:30."
        # We look for paragraphs containing the group name.
        group_pattern = re.compile(rf"Група {re.escape(self.group)}\.")

        # Find all paragraphs or text nodes
        paragraphs = soup.find_all("p")
        for p in paragraphs:
            text = p.get_text().strip()
            if group_pattern.search(text):
                # Found the line for this group
                if "Електроенергія є" in text:
                    # No power outages
                    continue

                # Extract intervals: "з HH:MM до HH:MM"
                matches = re.findall(r"з (\d{2}:\d{2}) до (\d{2}:\d{2})", text)
                for start_str, end_str in matches:
                    try:
                        start = datetime.strptime(start_str, "%H:%M").time()
                        end = datetime.strptime(end_str, "%H:%M").time()
                        periods.append(PowerOffPeriod(start, end, today=True))  # Default to True, corrected in caller
                    except ValueError:
                        continue

        return periods

    @staticmethod
    def _merge_periods(periods: list[PowerOffPeriod]) -> list[PowerOffPeriod]:
        """Merge overlapping or contiguous periods."""
        if not periods:
            return []

        # Separate today and tomorrow periods to merge them separately
        today_periods = sorted([p for p in periods if p.today], key=lambda x: x.start)
        tomorrow_periods = sorted([p for p in periods if not p.today], key=lambda x: x.start)

        def merge(p_list):
            if not p_list:
                return []
            merged = [p_list[0]]
            for current in p_list[1:]:
                last = merged[-1]
                # Check for overlap or contiguity
                # Logic: if current.start <= last.end
                if current.start <= last.end:
                    last.end = max(last.end, current.end)
                else:
                    merged.append(current)
            return merged

        return merge(today_periods) + merge(tomorrow_periods)
