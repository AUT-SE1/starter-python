"""Health and order endpoints for the Software Engineering Lab."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from orders import ERR_NOT_FOUND, OrderStore, ValidationError, validate_create_order

app = FastAPI(
    title="Starter Service",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    redirect_slashes=False,
)

store = OrderStore()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/orders", status_code=201)
async def create_order(request: Request) -> JSONResponse:
    # The body is read by hand rather than through a Pydantic model so that
    # validate_create_order stays the single place the contract is enforced,
    # in every language, with the same error shape.
    try:
        payload: Any = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "error": "validation_failed",
                "field": "body",
                "message": "request body is not valid JSON",
            },
        )

    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=400,
            content={
                "error": "validation_failed",
                "field": "body",
                "message": "request body must be a JSON object",
            },
        )

    try:
        item, quantity = validate_create_order(
            item=payload.get("item"),
            quantity=payload.get("quantity"),
        )
    except ValidationError as failure:
        return JSONResponse(status_code=400, content=failure.as_body())

    return JSONResponse(status_code=201, content=store.create(item, quantity).as_body())


@app.get("/orders/{order_id}")
async def get_order(order_id: str) -> JSONResponse:
    order = store.get(order_id)
    if order is None:
        return JSONResponse(
            status_code=404,
            content={"error": ERR_NOT_FOUND, "message": "no order with that id"},
        )
    return JSONResponse(status_code=200, content=order.as_body())
