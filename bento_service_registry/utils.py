__all__ = [
    "right_slash_normalize_url",
]


def right_slash_normalize_url(url: str) -> str:
    return url.rstrip("/") + "/"
