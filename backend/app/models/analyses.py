from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.documents import WarningItem
from app.models.evidence import DocumentEvidence
from app.models.image_answers import BoxEdges
from app.models.questions import Answer, Count, Distribution, Probability
from app.rubrics.cv_review_v3 import Section

Text = Annotated[str, Field(strict=True, min_length=1)]


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    document_evidence: DocumentEvidence | None = None
    cv_text: Text
    job_text: Text = None  # omission allowed; explicit null is not
    mode: Literal["review"]

    @field_validator("cv_text", "job_text")
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Text must not be blank")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            # This body is decoded here, not by FastAPI, so a lone surrogate would
            # otherwise reach the provider encoder as an unhandled error.
            raise ValueError("Text must be valid Unicode") from None
        return value


class RubricExplanation(BaseModel):
    kind: Literal["rubric"] = "rubric"
    template_ref: Text
    text: Text


class Finding(BaseModel):
    question_id: Text
    dimension: Text
    section: Section | None = None
    scope: Literal["general_review", "job_alignment"]
    assessment_level: Literal["full_document", "bullet"] = "full_document"
    source_text: str | None = None
    source: Literal["provider", "document_metadata"] = "provider"
    question: Text
    criteria: list[Text] = Field(min_length=1)
    answer: Answer
    probabilities: Distribution | None
    confidence: Probability | None
    rubric_explanation: RubricExplanation | None


class Overview(BaseModel):
    questions_total: Count
    questions_answered: Count
    questions_assessable: Count
    rating: None = None


class Metrics(BaseModel):
    duration_ms: float = Field(ge=0, allow_inf_nan=False)
    input_tokens: Count | None
    output_tokens: Count | None
    cost_usd: None = None


class ContentScore(BaseModel):
    """Weighted content score over the v3 checks that could be decided."""

    model_config = ConfigDict(extra="forbid")
    value: int | None = Field(default=None, ge=0, le=100)
    band: str | None = None
    range: tuple[int, int] | None = None
    coverage: float = Field(ge=0, le=1)
    assessed_weight: int = Field(ge=0, le=100)


class StructureScore(BaseModel):
    """Structure score, or null with the reason it is missing."""

    model_config = ConfigDict(extra="forbid")
    value: int | None = Field(default=None, ge=0, le=100)
    band: str | None = None
    reason: str | None = None
    assessed_weight: int = Field(default=0, ge=0, le=100)


class TotalScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int | None = Field(default=None, ge=0, le=100)
    band: str | None = None
    mode: Literal["combined", "content_only", "structure_only", "unavailable"]


class Scores(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: ContentScore
    structure: StructureScore
    total: TotalScore


class DimensionRow(BaseModel):
    """One row of the report breakdown, owned by exactly one score."""

    model_config = ConfigDict(extra="forbid")
    key: Text
    label: Text
    owner: Literal["content", "structure"]
    weight: int = Field(ge=0, le=100)
    value: int | None = Field(default=None, ge=0, le=100)
    section: Section | None = None


class StructureFindingItem(BaseModel):
    """One structure check outcome. Page index is 0-based, as on a content finding."""

    model_config = ConfigDict(extra="forbid")
    id: Text
    label: Text
    severity: Literal["pass", "minor", "major", "unassessable"]
    points_lost: int = Field(ge=0, le=100)
    page: int | None = Field(default=None, ge=0)
    box: BoxEdges | None = None
    confidence: Probability | None = None
    evidence: Text


class AnalysisReport(BaseModel):
    analysis_id: Text
    rubric_version: Literal["v1", "v2", "v3"] = "v3"
    model: Text
    findings: list[Finding]
    overview: Overview
    warnings: list[WarningItem]
    metrics: Metrics
    scores: Scores
    dimensions: list[DimensionRow] = Field(default_factory=list)
    structure_findings: list[StructureFindingItem] = Field(default_factory=list)
