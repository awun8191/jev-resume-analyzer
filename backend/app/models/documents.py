from pydantic import BaseModel, Field


class WarningItem(BaseModel):
    model_config = {"extra": "forbid"}
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ExtractionResponse(BaseModel):
    model_config = {"extra": "forbid"}
    text: str
    page_count: int | None = Field(default=None, ge=1)
    source_format: str
    warnings: list[WarningItem]
