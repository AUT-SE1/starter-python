"""Integration tests: routing, JSON encoding and the store, working together."""

import pytest
from fastapi.testclient import TestClient

from main import app, store


@pytest.fixture
def client():
    # Each test starts from an empty store, so no test inherits another's
    # state and the order they run in does not matter.
    store.clear()
    with TestClient(app) as test_client:
        yield test_client
    store.clear()


def test_post_orders_with_a_valid_body_returns_201_and_the_order(client):
    response = client.post("/orders", json={"item": "notebook", "quantity": 3})

    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["item"] == "notebook"
    assert body["quantity"] == 3
    assert body["status"] == "created"
    assert body["id"]


def test_post_orders_with_an_invalid_quantity_returns_400(client):
    response = client.post("/orders", json={"item": "notebook", "quantity": 0})

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "validation_failed"
    assert body["field"] == "quantity"


def test_post_orders_with_malformed_json_returns_400(client):
    response = client.post(
        "/orders",
        content=b'{"item":',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400


def test_get_order_after_creating_returns_the_same_order(client):
    created = client.post("/orders", json={"item": "کتاب", "quantity": 7}).json()

    response = client.get(f"/orders/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_order_when_id_is_unknown_returns_404(client):
    response = client.get("/orders/ord_missing")

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_health_returns_200_and_status_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
