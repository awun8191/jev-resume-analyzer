"""Observed document facts, never inferred visual verdicts."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Number = Annotated[float, Field(allow_inf_nan=False)]
Box = Annotated[list[Number], Field(min_length=4, max_length=4)]


class EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Span(EvidenceModel):
    id: str = Field(max_length=80)
    text: str = Field(max_length=10000)
    page: int | None = Field(default=None, ge=1)
    bbox: Box | None = None
    font_name: str | None = Field(default=None, max_length=200)
    font_size_pt: Number | None = None
    location: str = Field(default="body", max_length=100)
    alignment: str | None = Field(default=None, max_length=80)


class Link(EvidenceModel):
    label: str = Field(max_length=5000)
    target: str | None = Field(default=None, max_length=4000)
    page: int | None = Field(default=None, ge=1)
    bbox: Box | None = None
    kind: Literal["external", "internal", "unresolved"] = "unresolved"


class Page(EvidenceModel):
    number: int = Field(ge=1)
    width_pt: Number | None = None
    height_pt: Number | None = None
    rotation: int | None = None
    margins_pt: Box | None = None  # left, top, right, bottom
    margin_kind: Literal["configured", "estimated_content_whitespace", "not_assessed"]


class DocumentEvidence(EvidenceModel):
    version: Literal["1"] = "1"
    source_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_format: Literal["pdf", "docx"]
    pages: list[Page] = Field(default_factory=list, max_length=100)
    spans: list[Span] = Field(default_factory=list, max_length=5000)
    links: list[Link] = Field(default_factory=list, max_length=500)
    limitations: list[str] = Field(default_factory=list, max_length=30)
