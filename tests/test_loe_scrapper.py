import asyncio
import logging
import sys
import os
from unittest.mock import MagicMock

# Add the project root to the python path BEFORE importing custom_components
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock homeassistant module because it is imported by __init__.py
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.config_entries"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.exceptions"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"] = MagicMock()
sys.modules["homeassistant.util"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.components"] = MagicMock()
sys.modules["homeassistant.components.calendar"] = MagicMock()

from custom_components.lviv_poweroff.loe_scrapper import LoeScrapper  # noqa: E402
from custom_components.lviv_poweroff.const import PowerOffGroup  # noqa: E402


logging.basicConfig(level=logging.DEBUG)


async def main():
    # Use a group that likely has outages or just the first one
    group = PowerOffGroup.OneOne
    print(f"Initializing scrapper for group {group}")
    scrapper = LoeScrapper(group)

    print("Validating...")
    is_valid = await scrapper.validate()
    print(f"Is valid: {is_valid}")

    if is_valid:
        print("Fetching periods...")
        periods = await scrapper.get_power_off_periods()
        print(f"Periods found: {len(periods)}")
        for p in periods:
            print(f"Start: {p.start_datetime}, End: {p.end_datetime}, Today: {p.today}")


if __name__ == "__main__":
    asyncio.run(main())
