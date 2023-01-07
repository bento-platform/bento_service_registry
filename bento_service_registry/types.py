from typing import TypedDict


# TODO: py3.10(?): optional TypedDict props

# required props for chord_services.json entries
class BaseBentoService(TypedDict):
    url_template: str
    repository: str
    data_service: bool


# optional props for chord_services.json entries
class BentoService(BaseBentoService, total=False):
    artifact: str
    url: str
    manageable_tables: bool
    disabled: bool


BentoServices = Dict[str, BentoService]
