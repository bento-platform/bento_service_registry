from __future__ import annotations

from typing import TypedDict


# TODO: py3.10(?): optional TypedDict props

# required props for chord_services.json entries
class BaseBentoService(TypedDict):
    url_template: str
    repository: str
    data_service: bool


# optional props for chord_services.json entries
class BentoService(BaseBentoService, total=False):
    manageable_tables: bool


BentoServices = dict[str, BentoService]
