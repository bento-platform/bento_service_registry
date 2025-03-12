from fastapi import Depends, Request
from typing import Annotated


__all__ = [
    "OptionalHeaders",
    "get_authz_header",
    "OptionalAuthzHeaderDependency",
]


HEADER_AUTHORIZATION = "Authorization"

OptionalHeaders = dict[str, str] | None


def get_authz_header(request: Request) -> OptionalHeaders:
    authz_header: str | None = request.headers.get(HEADER_AUTHORIZATION)
    return {HEADER_AUTHORIZATION: authz_header} if authz_header is not None else None


OptionalAuthzHeaderDependency = Annotated[OptionalHeaders, Depends(get_authz_header)]
