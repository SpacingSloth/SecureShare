from typing import Optional
from fastapi import Request
from app.core.config import settings

def external_base_url(request: Request) -> str:
    if settings.PUBLIC_BASE_URL:
        return settings.PUBLIC_BASE_URL.rstrip("/")

    fwd = request.headers.get("forwarded")
    if fwd:
        proto = host = None
        for part in fwd.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip().lower()
                v = v.strip().strip('"')
                if k == "proto":
                    proto = v
                elif k == "host":
                    host = v
        if proto and host:
            return f"{proto}://{host}".rstrip("/")

    proto = request.headers.get("x-forwarded-proto")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if proto and host:
        return f"{proto}://{host}".rstrip("/")

    return str(request.base_url).rstrip("/")


def build_external_url(request: Request, path: str) -> str:
    base = external_base_url(request)
    if not path.startswith("/"):
        path = "/" + path
    return base + path
