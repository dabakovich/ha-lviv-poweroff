from pathlib import Path
from datetime import datetime

from aioresponses import aioresponses
import pytest

from custom_components.lviv_poweroff.energyua_scrapper import EnergyUaScrapper
from custom_components.lviv_poweroff.entities import PowerOffPeriod


def load_energyua_page(test_page: str) -> str:
    test_file = Path(__file__).parent / test_page

    with open(test_file, encoding="utf-8") as file:
        return file.read()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "group,test_page,expected_result",
    [
        (
            "1.2",
            "energyua_12_page.html",
            [
                PowerOffPeriod(
                    datetime(2024, 2, 9, 23, 0),
                    datetime(2024, 2, 10, 0, 0),
                ),
                PowerOffPeriod(
                    datetime(2024, 2, 9, 0, 0),
                    datetime(2024, 2, 9, 2, 0),
                ),
                PowerOffPeriod(
                    datetime(2024, 2, 9, 6, 0),
                    datetime(2024, 2, 9, 8, 0),
                ),
                PowerOffPeriod(
                    datetime(2024, 2, 9, 11, 0),
                    datetime(2024, 2, 9, 14, 0),
                ),
                PowerOffPeriod(
                    datetime(2024, 2, 9, 16, 0),
                    datetime(2024, 2, 9, 20, 0),
                ),
                PowerOffPeriod(
                    datetime(2024, 2, 9, 22, 0),
                    datetime(2024, 2, 10, 0, 0),
                ),
                PowerOffPeriod(
                    datetime(2024, 2, 10, 7, 0),
                    datetime(2024, 2, 10, 9, 0),
                ),
                PowerOffPeriod(
                    datetime(2024, 2, 10, 19, 0),
                    datetime(2024, 2, 10, 21, 0),
                ),
            ],
        ),
        (
            "1.1",
            "energyua_11_page.html",
            [
                PowerOffPeriod(
                    datetime(2024, 2, 9, 0, 0),
                    datetime(2024, 2, 9, 1, 0),
                ),
                PowerOffPeriod(
                    datetime(2024, 2, 9, 7, 0),
                    datetime(2024, 2, 9, 9, 0),
                ),
                PowerOffPeriod(
                    datetime(2024, 2, 9, 14, 0),
                    datetime(2024, 2, 9, 15, 0),
                ),
                PowerOffPeriod(
                    datetime(2024, 2, 9, 19, 0),
                    datetime(2024, 2, 9, 22, 0),
                ),
            ],
        ),
        (
            "1.2",
            "energyua_12_nodata_page.html",
            [],
        ),
    ],
)
async def test_energyua_scrapper(group, test_page, expected_result) -> None:
    # Given a response from the EnergyUa website
    with aioresponses() as mock:
        mock.get(f"https://lviv.energy-ua.info/grupa/{group}", body=load_energyua_page(test_page))
        # When scrapper is called for power-off periods
        scrapper = EnergyUaScrapper(group)
        poweroffs = await scrapper.get_power_off_periods()

    # Then the power-off periods are extracted correctly
    assert poweroffs is not None
    assert len(poweroffs) == len(expected_result)
    assert poweroffs == expected_result
