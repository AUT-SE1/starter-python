"""Session 05 — contract test against the NEIGHBOURING TEAM's running sandbox.

This is not a mock. It sends real HTTP to a service you did not write and
checks the answer against the OpenAPI document both teams agreed on.

Run it:
    NEIGHBOR_BASE_URL=http://10.0.0.42:8080 make contract-test

With no NEIGHBOR_BASE_URL set, every test here skips, so `make test` stays
green on a laptop with no neighbour in reach. A skipped contract test is not a
passing one — your report must show it running against a real address.

TODO(team): two things to change, and nothing else.
  1. NEIGHBOR_ORDERS_PATH, if your neighbour's service names its routes
     differently from the shared contract.
  2. valid_order_body(), if their CreateOrderRequest carries extra fields.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest

from .openapi_check import OpenAPIDocument

NEIGHBOR_ORDERS_PATH = "/orders"  # TODO(team): confirm against their OpenAPI
SPEC_PATH = Path(__file__).resolve().parents[2] / "openapi.json"
REQUEST_TIMEOUT = 10.0


def valid_order_body() -> dict[str, Any]:
    # TODO(team): match your neighbour's CreateOrderRequest schema.
    return {"item": "contract-test-item", "quantity": 2}


@pytest.fixture(scope="module")
def base_url() -> str:
    url = os.environ.get("NEIGHBOR_BASE_URL")
    if not url:
        pytest.skip(
            "NEIGHBOR_BASE_URL is not set — skipping the contract test. "
            "Set it to your neighbour's sandbox, e.g. http://10.0.0.42:8080"
        )
    return url.rstrip("/")


@pytest.fixture(scope="module")
def document() -> OpenAPIDocument:
    return OpenAPIDocument(SPEC_PATH)


def send(method: str, url: str, json_body: Any = None) -> tuple[httpx.Response, Any]:
    try:
        response = httpx.request(
            method, url, json=json_body, timeout=REQUEST_TIMEOUT, trust_env=False
        )
    except httpx.HTTPError as error:  # pragma: no cover - network failure path
        pytest.fail(
            f"{method} {url} failed to reach the neighbour's sandbox: {error}\n"
            "Is their service running, listening on 0.0.0.0 and allowed through the firewall?"
        )

    # A timestamp belongs in the report, so print one with every call.
    stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    print(f"{stamp}  {method} {url} -> {response.status_code}")

    try:
        return response, response.json()
    except ValueError:  # pragma: no cover - contract violation path
        pytest.fail(f"{method} {url} did not return JSON. Body was: {response.text[:400]!r}")


def assert_matches(document: OpenAPIDocument, schema_name: str, value: Any) -> None:
    problems = document.validate(schema_name, value)
    assert not problems, (
        f"response does not match the agreed {schema_name} schema:\n  "
        + "\n  ".join(problems)
    )


# --- the contract -----------------------------------------------------------


def test_neighbor_create_order_returns_201_and_an_order_matching_the_contract(base_url, document):
    response, body = send("POST", base_url + NEIGHBOR_ORDERS_PATH, valid_order_body())

    assert response.status_code == 201, f"expected 201, got {response.status_code} — body: {body}"
    assert_matches(document, "Order", body)


def test_neighbor_create_order_with_quantity_zero_returns_400_and_an_error(base_url, document):
    invalid = valid_order_body() | {"quantity": 0}

    response, body = send("POST", base_url + NEIGHBOR_ORDERS_PATH, invalid)

    # The contract fixes the status code and the error shape. It says nothing
    # about the wording of the message — that is their business, not ours.
    assert response.status_code == 400, (
        f"expected 400 for an invalid quantity, got {response.status_code} — body: {body}"
    )
    assert_matches(document, "Error", body)


def test_neighbor_get_order_after_creating_returns_the_same_order(base_url, document):
    _, created = send("POST", base_url + NEIGHBOR_ORDERS_PATH, valid_order_body())
    order_id = created.get("id")
    assert order_id, f"the create response carried no usable id: {created}"

    response, body = send("GET", f"{base_url}{NEIGHBOR_ORDERS_PATH}/{order_id}")

    assert response.status_code == 200, (
        f"expected 200 when reading back order {order_id!r}, got {response.status_code}"
    )
    assert_matches(document, "Order", body)
    assert body["id"] == order_id


def test_neighbor_get_order_with_an_unknown_id_returns_404(base_url, document):
    response, body = send(
        "GET", f"{base_url}{NEIGHBOR_ORDERS_PATH}/ord_definitely_not_real"
    )

    assert response.status_code == 404, (
        f"expected 404 for an unknown id, got {response.status_code} — body: {body}"
    )
    assert_matches(document, "Error", body)
