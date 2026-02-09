import asyncio
import logging
import sys

# Configure logging to show info/debug messages
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stdout
)

# Add the current directory to sys.path so we can import custom_components
# This is usually needed if running from the root of the repo
import os  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402
import aiohttp  # noqa: E402

sys.path.append(os.getcwd())

# !!! HACK !!!
# Disable SSL verification for local testing because of:
# [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate
original_init = aiohttp.ClientSession.__init__


def new_init(self, *args, **kwargs):
    if "connector" not in kwargs:
        # Force fail-safe SSL context
        kwargs["connector"] = aiohttp.TCPConnector(ssl=False)
    original_init(self, *args, **kwargs)


aiohttp.ClientSession.__init__ = new_init
# !!! END HACK !!!

# Mock homeassistant to allow imports
# This is necessary because importing custom_components.lviv_poweroff executes __init__.py,
# which imports homeassistant modules.
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.config_entries"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"] = MagicMock()
sys.modules["homeassistant.components"] = MagicMock()
sys.modules["homeassistant.components.calendar"] = MagicMock()
sys.modules["homeassistant.util"] = MagicMock()
sys.modules["homeassistant.util.dt"] = MagicMock()

from custom_components.lviv_poweroff.loe_scrapper import LoeScrapper  # noqa: E402
from custom_components.lviv_poweroff.const import PowerOffGroup  # noqa: E402


async def main():
    # You can change the group here or pass it as an argument
    group = PowerOffGroup.OneOne
    print(f"Fetching power off periods for group {group}...")

    scrapper = LoeScrapper(group=group)

    # Optional: validate connection
    is_valid = await scrapper.validate()
    print(f"API Connection Valid: {is_valid}")

    if is_valid:
        periods = await scrapper.get_power_off_periods()

        print("\nFound Periods:")
        if not periods:
            print("No power off periods found (or maybe no outages scheduled).")

        for p in periods:
            print(f"  - {p}")


if __name__ == "__main__":
    asyncio.run(main())
