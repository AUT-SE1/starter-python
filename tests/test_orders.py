"""Unit tests: validation and storage, with no HTTP in sight."""

import pytest

from orders import (
    MAX_QUANTITY,
    MIN_QUANTITY,
    STATUS_CREATED,
    OrderStore,
    ValidationError,
    validate_create_order,
)


def test_validate_create_order_when_request_is_valid_returns_cleaned_values():
    item, quantity = validate_create_order(item="  notebook  ", quantity=3)

    assert item == "notebook"
    assert quantity == 3


@pytest.mark.parametrize(
    ("item", "quantity", "expected_field"),
    [
        (None, 1, "item"),
        ("", 1, "item"),
        ("   ", 1, "item"),
        ("a" * 65, 1, "item"),
        (123, 1, "item"),
        ("book", None, "quantity"),
        ("book", 0, "quantity"),
        ("book", -5, "quantity"),
        ("book", MAX_QUANTITY + 1, "quantity"),
        ("book", "two", "quantity"),
        ("book", 1.5, "quantity"),
        ("book", True, "quantity"),
    ],
)
def test_validate_create_order_when_input_is_invalid_names_the_field(item, quantity, expected_field):
    with pytest.raises(ValidationError) as caught:
        validate_create_order(item=item, quantity=quantity)

    assert caught.value.field == expected_field


@pytest.mark.parametrize("quantity", [MIN_QUANTITY, MAX_QUANTITY])
def test_validate_create_order_at_the_quantity_boundaries_succeeds(quantity):
    _, accepted = validate_create_order(item="book", quantity=quantity)

    assert accepted == quantity


def test_validate_create_order_when_item_is_non_ascii_keeps_it_intact():
    # The limit is 64 characters, not 64 bytes — a Persian item name must fit.
    item, _ = validate_create_order(item="کتاب", quantity=1)

    assert item == "کتاب"


def test_order_store_after_create_returns_the_same_order():
    store = OrderStore()

    created = store.create("notebook", 2)

    assert store.get(created.id) == created
    assert created.id.startswith("ord_")
    assert created.status == STATUS_CREATED


def test_order_store_when_id_is_unknown_returns_none():
    store = OrderStore()

    assert store.get("ord_does_not_exist") is None


def test_order_store_gives_each_order_its_own_id():
    store = OrderStore()

    first = store.create("book", 1)
    second = store.create("book", 1)

    assert first.id != second.id
