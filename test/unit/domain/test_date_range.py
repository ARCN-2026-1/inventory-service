from datetime import date

import pytest

from internal.domain.errors import DomainRuleViolation
from internal.domain.valueobjects.date_range import DateRange


def test_date_range_accepts_end_date_after_start_date() -> None:
    availability = DateRange(start_date=date(2026, 4, 23), end_date=date(2026, 4, 24))

    assert availability.start_date == date(2026, 4, 23)
    assert availability.end_date == date(2026, 4, 24)


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        (date(2026, 4, 24), date(2026, 4, 24)),
        (date(2026, 4, 25), date(2026, 4, 24)),
    ],
)
def test_date_range_rejects_non_increasing_dates(
    start_date: date, end_date: date
) -> None:
    with pytest.raises(
        DomainRuleViolation, match="Availability end date must be after start date"
    ):
        DateRange(start_date=start_date, end_date=end_date)
