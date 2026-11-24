"""FastAPI application factory for the synthetic ledger."""

from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from demo_api.errors import ApiError
from demo_api.routers import accounts, auth, health, transactions, users
from demo_api.store import get_store

_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
}


def create_app() -> FastAPI:
    app = FastAPI(
        title="Demo Ledger API",
        version="1.0.0",
        summary="Synthetic banking-style API for automation practice.",
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(accounts.router)
    app.include_router(transactions.router)

    @app.middleware("http")
    async def correlation_header(request: Request, call_next: Any) -> Any:
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    @app.exception_handler(ApiError)
    async def handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content=exc.body())

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for error in exc.errors():
            location = [str(part) for part in error.get("loc", [])]
            details.append(
                {
                    "loc": location,
                    "msg": str(error.get("msg", "")),
                    "type": str(error.get("type", "")),
                }
            )
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "message": "Invalid request",
                "details": details,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": _STATUS_CODES.get(exc.status_code, "error"),
                "message": message,
                "details": [],
            },
        )

    @app.post("/test/reset", status_code=204)
    def reset_store() -> Response:
        if os.getenv("DEMO_ALLOW_RESET", "true").lower() != "true":
            return JSONResponse(
                status_code=404,
                content={"code": "not_found", "message": "Not found", "details": []},
            )
        get_store().reset()
        return Response(status_code=204)

    return app
