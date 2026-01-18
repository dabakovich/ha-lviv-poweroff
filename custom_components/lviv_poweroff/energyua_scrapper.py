"""Provides classes for scraping power off periods from the Energy UA website."""


import aiohttp
from bs4 import BeautifulSoup

from .const import PowerOffGroup
from .entities import PowerOffPeriod

URL = "https://lviv.energy-ua.info/grupa/{}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class EnergyUaScrapper:
    """Class for scraping power off periods from the Energy UA website."""

    def __init__(self, group: PowerOffGroup) -> None:
        """Initialize the EnergyUaScrapper object."""
        self.group = group

    async def validate(self) -> bool:
        async with (
            aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session,
            session.get(URL.format(self.group)) as response,
        ):
            return response.status == 200

    @staticmethod
    def merge_periods(periods: list[PowerOffPeriod]) -> list[PowerOffPeriod]:
        if not periods:
            return []

        periods.sort(key=lambda x: x.start)

        merged_periods = [periods[0]]
        for current in periods[1:]:
            last = merged_periods[-1]
            if current.start <= last.end:  # type: ignore[operator] # Overlapping or contiguous periods
                last.end = max(last.end, current.end)
                continue
            merged_periods.append(current)

        return merged_periods

    async def get_power_off_periods(self) -> list[PowerOffPeriod]:
        async with (
            aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session,
            session.get(URL.format(self.group)) as response,
        ):
            content = await response.text()
            soup = BeautifulSoup(content, "html.parser")
            results = []
            scale_hours = soup.find_all("div", class_="scale_hours")
            if len(scale_hours) > 0:
                scale_hours_el = scale_hours[0].find_all("div", class_="scale_hours_el")
                for item in scale_hours_el:
                    if item.find("span", class_="hour_active"):
                        start, end = self._parse_item(item)
                        results.append(PowerOffPeriod(start, end, today=True))
                results = self.merge_periods(results)
            if len(scale_hours) > 1:
                tomorrow_results = []
                scale_hours_el_tomorrow = scale_hours[1].find_all("div", class_="scale_hours_el")
                for item in scale_hours_el_tomorrow:
                    if item.find("span", class_="hour_active"):
                        start, end = self._parse_item(item)
                        tomorrow_results.append(PowerOffPeriod(start, end, today=False))
                results += self.merge_periods(tomorrow_results)

            return results

    def _parse_item(self, item: BeautifulSoup) -> tuple[int, int]:
        start_hour = item.find("i", class_="hour_info_from")
        end_hour = item.find("i", class_="hour_info_to")
        if start_hour and end_hour:
            return int(start_hour.text.split(":")[0]), int(end_hour.text.split(":")[0])
        raise ValueError(f"Time period not found in the input string: {item.text}")
