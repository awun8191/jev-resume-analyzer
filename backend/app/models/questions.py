from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Answer = Literal["present", "absent", "not_applicable", "unable_to_assess"]
Probability = Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)]
Count = Annotated[int, Field(strict=True, ge=0)]


class Distribution(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    present: Probability
    absent: Probability
    not_applicable: Probability
    unable_to_assess: Probability

    @model_validator(mode="after")
    def sums_to_one(self):
        if abs(sum(self.model_dump().values()) - 1) > 0.001:
            raise ValueError("Invalid distribution")
        return self


class ChoiceAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["choice"]
    choice: Answer
    probabilities: Distribution | None = None
    confidence: Probability | None = None

    @model_validator(mode="after")
    def choice_is_maximum(self):
        if self.probabilities is not None:
            values = self.probabilities.model_dump()
            if values[self.choice] < max(values.values()):
                raise ValueError("Selected answer does not match distribution")
        return self


class Usage(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    input_tokens: Count | None = None
    output_tokens: Count | None = None


class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    model: str = Field(min_length=1, max_length=100)
    answers: dict[str, ChoiceAnswer]
    usage: Usage | None = None
