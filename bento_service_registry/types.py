from typing import TypedDict


# TODO: py3.11(?): optional TypedDict props


# required props for chord_services.json entries
class BaseBentoService(TypedDict):
    url_template: str
    repository: str


# optional props for chord_services.json entries
class BentoService(BaseBentoService, total=False):
    service_kind: str
    url: str
    disabled: bool


BentoServices = dict[str, BentoService]
