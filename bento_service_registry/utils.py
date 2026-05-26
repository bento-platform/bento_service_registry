from bento_service_registry.authz_header import HEADER_AUTHORIZATION, OptionalHeaders
from hashlib import sha256

__all__ = [
    "right_slash_normalize_url",
    "authz_header_digest",
]


def right_slash_normalize_url(url: str) -> str:
    return url.rstrip("/") + "/"


def authz_header_digest(headers: OptionalHeaders) -> str:
    return sha256((headers or {}).get(HEADER_AUTHORIZATION, "").encode("ascii"), usedforsecurity=True).hexdigest()
