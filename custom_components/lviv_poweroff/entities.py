"""Module for power off period entities."""

from dataclasses import dataclass
from datetime import datetime, timedelta, time


@dataclass
class PowerOffPeriod:
    """Class for power off period."""

    start: time | int
    end: time | int
    today: bool

    def to_datetime_period(self, tz_info) -> tuple[datetime, datetime]:
        """Convert to datetime period."""
        now = datetime.now().replace(tzinfo=tz_info)
        if not self.today:
            now += timedelta(days=1)

        if isinstance(self.start, int):
            start = now.replace(hour=self.start, minute=0, second=0, microsecond=0)
        else:
            start = now.replace(hour=self.start.hour, minute=self.start.minute, second=0, microsecond=0)

        if isinstance(self.end, int):
            end = now.replace(hour=self.end, minute=0, second=0, microsecond=0)
        else:
            end = now.replace(hour=self.end.hour, minute=self.end.minute, second=0, microsecond=0)

        if end < start:
            end += timedelta(days=1)
        return start, end
