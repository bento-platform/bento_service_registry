from pydantic import BaseModel, Field

__all__ = [
    "DataTypeDefinitionWithServiceURL",
]


class DataTypeDefinitionWithServiceURL(BaseModel):
    label: str | None = None
    queryable: bool
    item_schema: dict = Field(..., alias="schema")
    metadata_schema: dict
    id: str
    count: int | None
    # Injected rather than from service:
    service_base_url: str
