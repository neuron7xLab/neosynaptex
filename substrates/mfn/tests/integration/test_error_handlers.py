import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from mycelium_fractal_net.integration.error_handlers import (
    create_error_response,
    internal_error_handler,
    pydantic_validation_exception_handler,
    register_error_handlers,
    validation_exception_handler,
    value_error_handler,
)
from mycelium_fractal_net.integration.schemas import ErrorCode


class Payload(BaseModel):
    value: int


@pytest.fixture
def app_with_handlers() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.post("/items")
    def create_item(payload: Payload):
        return payload

    @app.get("/value-error")
    def value_error_endpoint():
        raise ValueError("invalid state")

    @app.get("/runtime-error")
    def runtime_error_endpoint():
        raise RuntimeError("boom")

    @app.get("/pydantic-error")
    def pydantic_error_endpoint():
        Payload.model_validate({"value": "oops"})
        return {"ok": True}

    return app


def test_create_error_response_includes_core_fields():
    response = create_error_response(
        error_code=ErrorCode.INVALID_REQUEST,
        message="failure",
        details=[],
        request_id="req-123",
    )

    assert response.error_code == ErrorCode.INVALID_REQUEST
    assert response.message == "failure"
    assert response.detail == "failure"
    assert response.details == []
    assert response.request_id == "req-123"
    assert response.timestamp is not None


def test_register_error_handlers_registers_expected_handlers(
    app_with_handlers: FastAPI,
):
    assert (
        app_with_handlers.exception_handlers[RequestValidationError] is validation_exception_handler
    )
    assert (
        app_with_handlers.exception_handlers[ValidationError]
        is pydantic_validation_exception_handler
    )
    assert app_with_handlers.exception_handlers[ValueError] is value_error_handler
    assert app_with_handlers.exception_handlers[Exception] is internal_error_handler


@pytest.mark.parametrize(
    ("endpoint", "status", "code", "message"),
    [
        ("/items", 422, ErrorCode.VALIDATION_ERROR, "Validation failed: 1 error(s)"),
        ("/value-error", 400, ErrorCode.INVALID_REQUEST, "invalid state"),
        (
            "/runtime-error",
            500,
            ErrorCode.INTERNAL_ERROR,
            "An internal error occurred. Please try again later.",
        ),
    ],
)
def test_error_handlers_apply_standard_error_schema(
    app_with_handlers: FastAPI, endpoint: str, status: int, code: str, message: str
):
    client = TestClient(app_with_handlers, raise_server_exceptions=False)
    headers = {"X-Request-ID": "req-0"}
    response = (
        client.post(endpoint, json={}, headers=headers)
        if endpoint == "/items"
        else client.get(endpoint, headers=headers)
    )
    payload = response.json()

    assert response.status_code == status
    assert payload["error_code"] == code
    assert payload["detail"] == message
    assert payload["message"] == message
    assert payload["timestamp"]

    assert payload["request_id"] == "req-0"


def test_validation_exception_handler_includes_details(app_with_handlers: FastAPI):
    client = TestClient(app_with_handlers, raise_server_exceptions=False)
    response = client.post(
        "/items", json={"value": "not-an-int"}, headers={"X-Request-ID": "req-1"}
    )

    payload = response.json()
    assert response.status_code == 422
    assert payload["error_code"] == ErrorCode.VALIDATION_ERROR
    assert payload["message"].startswith("Validation failed: ")
    assert payload["detail"] == payload["message"]
    assert payload["request_id"] == "req-1"

    details = payload.get("details")
    assert isinstance(details, list)
    assert details[0]["field"] == "body.value"
    assert details[0]["message"]
    assert details[0]["value"] == "not-an-int"


def test_pydantic_validation_exception_handler_handles_model_errors(
    app_with_handlers: FastAPI,
):
    client = TestClient(app_with_handlers, raise_server_exceptions=False)
    response = client.get("/pydantic-error", headers={"X-Request-ID": "req-2"})
    payload = response.json()

    assert response.status_code == 422
    assert payload["error_code"] == ErrorCode.VALIDATION_ERROR
    assert payload["request_id"] == "req-2"
    assert payload["details"]
    assert payload["details"][0]["field"] == "value"
    assert payload["details"][0]["message"]


def test_value_error_handler_prefers_internal_error_for_wrong_type(
    app_with_handlers: FastAPI,
):
    client = TestClient(app_with_handlers, raise_server_exceptions=False)

    # Trigger ValidationError and ensure it is routed to the appropriate handler
    response = client.get("/pydantic-error")
    assert response.status_code == 422
    assert response.json()["error_code"] == ErrorCode.VALIDATION_ERROR

    # Direct ValueError uses the value_error_handler
    response = client.get("/value-error")
    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorCode.INVALID_REQUEST
