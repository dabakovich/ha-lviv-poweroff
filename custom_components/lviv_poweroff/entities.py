"""Module for power off period entities."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PowerOffPeriod:
    """Class for power off period."""

    start_datetime: datetime
    end_datetime: datetime
