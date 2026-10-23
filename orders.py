"""Order domain logic for the Software Engineering Lab starter service.

Validation lives here, apart from the web framework, so the tests for it are
unit tests: no HTTP, no network, no storage.
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, asdict

# The validation bounds are part of the shared contract in openapi.yaml.
# Keep them and the specification in step with each other.
MIN_QUANTITY = 1
MAX_QUANTITY = 1000
MAX_ITEM_LENGTH = 64

STATUS_CREATED = "created"
ERR_VALIDATION = "validation_failed"
ERR_NOT_FOUND = "not_found"

MISSING = object()
"""Sentinel telling a missing field apart from an explicit null or zero."""


class ValidationError(Exception):
    """Raised when a request body does not satisfy the contract."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message

    def as_body(self) -> dict[str, str]:
        return {"error": ERR_VALIDATION, "field": self.field, "message": self.message}


@dataclass(frozen=True)
class Order:
    id: str
    item: str
    quantity: int
    status: str = STATUS_CREATED

    def as_body(self) -> dict[str, object]:
        return asdict(self)


def validate_create_order(item: object = MISSING, quantity: object = MISSING) -> tuple[str, int]:
    """Check one request body and return the cleaned values.

    Raises ValidationError naming the first field that is wrong.
    """
    if item is MISSING or item is None:
        raise ValidationError("item", "item is required")
    if not isinstance(item, str):
        raise ValidationError("item", "item must be a string")
    cleaned_item = item.strip()
    if not cleaned_item:
        raise ValidationError("item", "item must not be empty")
    if len(cleaned_item) > MAX_ITEM_LENGTH:
        raise ValidationError("item", "item is longer than 64 characters")

    if quantity is MISSING or quantity is None:
        raise ValidationError("quantity", "quantity is required")
    # bool is a subclass of int in Python, so True would slip through without
    # this check and become quantity 1.
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise ValidationError("quantity", "quantity must be an integer")
    if quantity < MIN_QUANTITY or quantity > MAX_QUANTITY:
        raise ValidationError("quantity", "quantity must be between 1 and 1000")

    return cleaned_item, quantity


class OrderStore:
    """Orders held in memory. A real service would use a database."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self._lock = threading.Lock()

    def create(self, item: str, quantity: int) -> Order:
        order = Order(id=f"ord_{secrets.token_hex(8)}", item=item, quantity=quantity)
        with self._lock:
            self._orders[order.id] = order
        return order

    def get(self, order_id: str) -> Order | None:
        with self._lock:
            return self._orders.get(order_id)

    def clear(self) -> None:
        """Reset between tests, so no test inherits another test's state."""
        with self._lock:
            self._orders.clear()
