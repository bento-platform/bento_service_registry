import logging

from bento_lib.logging import log_level_from_str
from fastapi import Depends
from functools import lru_cache
from typing import Annotated

from .config import ConfigDependency

__all__ = [
    "get_logger",
    "LoggerDependency",
]

logging.basicConfig(level=logging.DEBUG)


@lru_cache
def get_logger(config: ConfigDependency) -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level_from_str(config.log_level))
    return logger


LoggerDependency = Annotated[logging.Logger, Depends(get_logger)]
