"""Optional shared password for the whole API.

When ACCESS_PASSWORD is set, every /api route except the open ones below needs it, either in the
`X-Access-Password` header or, for links a browser opens directly (evidence PDFs), as `?access=`.
When it is not set, the API is open, as in local development.
"""
import hmac
import os

from fastapi import Request

HEADER = "X-Access-Password"
QUERY = "access"
OPEN_PATHS = {"/api/health", "/api/access"}


def password() -> str:
    return os.environ.get("ACCESS_PASSWORD", "").strip()


def supplied(request: Request) -> str:
    return request.headers.get(HEADER) or request.query_params.get(QUERY) or ""


def granted(request: Request) -> bool:
    expected = password()
    return not expected or hmac.compare_digest(supplied(request).encode(), expected.encode())


def blocks(request: Request) -> bool:
    """True when this request must be refused. CORS preflights and non-API paths always pass."""
    if request.method == "OPTIONS" or not request.url.path.startswith("/api/"):
        return False
    return request.url.path not in OPEN_PATHS and not granted(request)
