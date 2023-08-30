from fastapi import Depends, Request
from typing import Annotated, Literal


__all__ = [
    "OptionalAuthzHeader",
    "get_authz_header",
    "OptionalAuthzHeaderDependency",
]


HeaderAuthorizationType = Literal["Authorization"]
HEADER_AUTHORIZATION: HeaderAuthorizationType = "Authorization"

OptionalAuthzHeader = dict[HeaderAuthorizationType, str] | None


def get_authz_header(request: Request) -> OptionalAuthzHeader:
    authz_header: str | None = request.headers.get(HEADER_AUTHORIZATION)
    return {HEADER_AUTHORIZATION: authz_header} if authz_header is not None else None


OptionalAuthzHeaderDependency = Annotated[OptionalAuthzHeader, Depends(get_authz_header)]
