"""
Production security headers middleware.
Adds HSTS, CSP, and security headers to all responses while permitting
Google OAuth, CDN media, and cross-domain identity workflows.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import os


def _remove_header(headers, key: str):
    """Safely remove a header from Starlette MutableHeaders."""
    if key in headers:
        try:
            del headers[key]
        except KeyError:
            pass


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add production security headers to every response."""

    def __init__(self, app):
        super().__init__(app)
        self.is_production = os.environ.get("ENVIRONMENT", "development") == "production"

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Check if this is an OAuth or Auth endpoint
        path = request.url.path
        is_auth_route = path.startswith("/auth") or "/auth/" in path

        if not is_auth_route:
            # Prevent clickjacking for normal API routes
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
        else:
            # Allow OAuth popups and redirects without frame blockage
            _remove_header(response.headers, "X-Frame-Options")

        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy - essential for OAuth redirect state preservation
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"

        # Permissions policy
        response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"

        if self.is_production:
            # HSTS - force HTTPS for 1 year
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

            # Content Security Policy - explicitly permit Google Identity and CDN assets
            if not is_auth_route:
                response.headers["Content-Security-Policy"] = (
                    "default-src 'self' https: data:; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com https://apis.google.com https://cdn.jsdelivr.net; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://accounts.google.com; "
                    "img-src 'self' data: https: res.cloudinary.com lh3.googleusercontent.com; "
                    "font-src 'self' data: https://fonts.gstatic.com; "
                    "connect-src 'self' https: wss: https://accounts.google.com https://oauth2.googleapis.com; "
                    "frame-src 'self' https://accounts.google.com https://content.googleapis.com; "
                    "frame-ancestors 'self' https://accounts.google.com;"
                )
            else:
                # Completely omit CSP on OAuth redirects so browser / Google handles authentication natively
                _remove_header(response.headers, "Content-Security-Policy")

            # Remove server header
            _remove_header(response.headers, "server")

        return response
