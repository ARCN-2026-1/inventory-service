from decimal import Decimal

import pytest

from internal.domain.errors import DomainRuleViolation
from internal.domain.valueobjects.money import Money


def test_money_accepts_positive_amount_and_normalizes_currency() -> None:
    money = Money(amount=Decimal("149.99"), currency="usd")

    assert money.amount == Decimal("149.99")
    assert money.currency == "USD"


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-1.00")])
def test_money_rejects_non_positive_amount(amount: Decimal) -> None:
    with pytest.raises(
        DomainRuleViolation, match="Price amount must be greater than zero"
    ):
        Money(amount=amount, currency="USD")


def test_money_rejects_blank_currency() -> None:
    with pytest.raises(DomainRuleViolation, match="Price currency is required"):
        Money(amount=Decimal("149.99"), currency="   ")
