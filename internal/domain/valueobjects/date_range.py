from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from internal.domain.errors import DomainRuleViolation


@dataclass(frozen=True, slots=True)
class DateRange:
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if self.end_date <= self.start_date:
            raise DomainRuleViolation("Availability end date must be after start date")
