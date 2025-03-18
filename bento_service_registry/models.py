from pydantic import BaseModel, Field

__all__ = [
    "DataTypeWithServiceURL",
]


class DataTypeWithServiceURL(BaseModel):
    label: str | None = None
    queryable: bool
    item_schema: dict = Field(..., alias="schema")
    metadata_schema: dict
    id: str
    count: int | None
    last_ingested: str | None = None  # TODO: datetime?
    # Injected rather than from service:
    service_base_url: str
