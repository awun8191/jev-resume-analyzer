from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.documents import WarningItem
from app.models.evidence import DocumentEvidence
from app.models.questions import Answer, Count, Distribution, Probability

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
        return value


class RubricExplanation(BaseModel):
    kind: Literal["rubric"] = "rubric"
    template_ref: Text
    text: Text


class Finding(BaseModel):
    question_id: Text
    dimension: Text
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


class AnalysisReport(BaseModel):
    analysis_id: Text
    rubric_version: Literal["v1", "v2"] = "v2"
    model: Text
    findings: list[Finding]
    overview: Overview
    warnings: list[WarningItem]
    metrics: Metrics
