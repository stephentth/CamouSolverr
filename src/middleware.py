"""Middleware for CamouSolverr."""

import time

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests."""

    async def dispatch(self, request: Request, call_next):
        """Log request and response details."""
        # Generate request ID if not already set
        request_id = request.headers.get("X-Request-ID", "")

        # Log incoming request
        logger.info(
            f"→ {request.method} {request.url.path} "
            f"[{request.client.host if request.client else 'unknown'}]"
        )

        # Track request duration
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        logger.info(
            f"← {request.method} {request.url.path} [{response.status_code}] {duration:.3f}s"
        )

        return response
