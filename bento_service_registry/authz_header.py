from fastapi import Depends, Request
from typing import Annotated, Literal, Type


__all__ = [
    "OptionalAuthzHeader",
    "get_authz_header",
    "OptionalAuthzHeaderDependency",
]


HEADER_AUTHORIZATION: Literal["Authorization"] = "Authorization"

OptionalAuthzHeader = dict[Type[HEADER_AUTHORIZATION], str] | None


def get_authz_header(request: Request) -> OptionalAuthzHeader:
    authz_header: str | None = request.headers.get(HEADER_AUTHORIZATION)
    return {HEADER_AUTHORIZATION: authz_header} if authz_header is not None else None


OptionalAuthzHeaderDependency = Annotated[OptionalAuthzHeader, Depends(get_authz_header)]
