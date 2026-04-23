from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from internal.domain.errors import DomainRuleViolation


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.amount <= Decimal("0"):
            raise DomainRuleViolation("Price amount must be greater than zero")
        normalized_currency = self.currency.strip().upper()
        if not normalized_currency:
            raise DomainRuleViolation("Price currency is required")
        object.__setattr__(self, "currency", normalized_currency)
