"""Request logging middleware (pure ASGI, SSE-safe)."""

import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.lib import get_logger

logger = get_logger("gateway.middleware.logging")


class RequestLoggingMiddleware:
    """Log each request with method, path, status code, and duration.

    Pure ASGI implementation -- does not buffer response bodies, safe for SSE/streaming.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        status_code = 500  # default in case response.start is never sent

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.monotonic() - start) * 1000, 2)
            method: str = scope.get("method", "")
            path: str = scope.get("path", "")
            logger.info(
                "%s %s %s %sms",
                method,
                path,
                status_code,
                duration_ms,
                extra={
                    "method": method,
                    "path": path,
                    "status": status_code,
                    "duration_ms": duration_ms,
                },
            )
