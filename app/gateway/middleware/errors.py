"""Error handling middleware for FastAPI gateway (pure ASGI, SSE-safe)."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.gateway.models import ErrorDetail, ErrorResponse
from app.lib import AutoBuilderError, ConflictError, NotFoundError, get_logger
from app.lib.exceptions import ConfigurationError, ValidationError, WorkerError
from app.models.enums import ErrorCode

logger = get_logger("gateway.middleware.errors")

# Exception type -> HTTP status code
_STATUS_MAP: dict[type[AutoBuilderError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    ValidationError: 422,
    ConfigurationError: 500,
    WorkerError: 500,
}


class ErrorHandlingMiddleware:
    """Catch AutoBuilderError subclasses and return structured JSON error responses.

    Pure ASGI implementation -- does not buffer response bodies, safe for SSE/streaming.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except AutoBuilderError as exc:
            status_code = _STATUS_MAP.get(type(exc), 500)
            error_response = ErrorResponse(
                error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details)
            )
            response = JSONResponse(
                status_code=status_code,
                content=error_response.model_dump(mode="json"),
            )
            await response(scope, receive, send)
        except Exception:
            logger.error("Unhandled exception", exc_info=True)
            error_response = ErrorResponse(
                error=ErrorDetail(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="An internal error occurred",
                )
            )
            response = JSONResponse(status_code=500, content=error_response.model_dump(mode="json"))
            await response(scope, receive, send)
