import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.database.redis_client import redis_client


logger = logging.getLogger("socialpilot.security.middleware")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for:
    - Rate limiting
    - Security headers
    - Swagger UI compatibility
    - Request processing time
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        # ---------------------------------------------------------
        # 1. Rate Limiting
        # ---------------------------------------------------------
        client_ip = (
            request.client.host
            if request.client
            else "127.0.0.1"
        )

        rate_key = f"rate_limit:{client_ip}:{int(time.time() // 60)}"

        try:
            current_count = redis_client.incr(rate_key)

            if current_count == 1:
                redis_client.expire(rate_key, 60)

            # 300 requests per minute
            if current_count > 300:
                return Response(
                    content=(
                        '{"success": false, '
                        '"message": "Rate limit exceeded. '
                        'Please try again later."}'
                    ),
                    status_code=429,
                    media_type="application/json",
                )

        except Exception as e:
            # Redis should not stop the application during local development
            logger.debug(
                "Redis rate limit check skipped: %s",
                e,
            )

        # ---------------------------------------------------------
        # 2. Process Request
        # ---------------------------------------------------------
        response = await call_next(request)

        process_time = time.time() - start_time

        response.headers["X-Process-Time"] = (
            f"{process_time:.4f}s"
        )

        # ---------------------------------------------------------
        # 3. Security Headers
        # ---------------------------------------------------------

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Legacy XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Only use HSTS when running behind HTTPS in production.
        # Keeping it disabled for local HTTP avoids browser issues.
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # ---------------------------------------------------------
        # 4. Content Security Policy
        # ---------------------------------------------------------
        #
        # FastAPI Swagger UI uses jsDelivr CDN for:
        # swagger-ui.css
        # swagger-ui-bundle.js
        #
        # Therefore CDN must be allowed.
        #
        # This fixes:
        # "Loading the stylesheet ... violates CSP"
        # "Loading the script ... violates CSP"
        # "SwaggerUIBundle is not defined"
        #

        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https://cdn.jsdelivr.net; "
            "connect-src 'self' http://localhost:8000 "
            "http://127.0.0.1:8000; "
            "frame-ancestors 'none';"
        )

        return response