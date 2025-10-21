from typing import NotRequired, TypedDict


# required props for chord_services.json entries
class BentoService(TypedDict):
    url_template: str
    repository: str
    # optional props for chord_services.json entries
    service_kind: NotRequired[str]
    url: NotRequired[str]
    disabled: NotRequired[bool]


BentoServices = dict[str, BentoService]
