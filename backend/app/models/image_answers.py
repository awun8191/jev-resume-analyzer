"""Answer types for Box and Noul questions. Spike only.

The production ProviderResponse accepts Choice answers only. This module adds the
Box and Noul shapes documented at https://docs.typesafe.ai/primitives/box and
https://docs.typesafe.ai/primitives/noul so the spike can validate a real answer set
without relaxing the production contract.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.questions import Probability, Usage


class BoxEdges(BaseModel):
    """One bounding box, as fractions of the image width and height."""

    model_config = ConfigDict(extra="forbid", strict=True)
    top: Probability
    bottom: Probability
    left: Probability
    right: Probability

    @model_validator(mode="after")
    def edges_are_ordered(self):
        if not (self.left < self.right and self.top < self.bottom):
            raise ValueError("Box edges are not ordered")
        return self


class BoxAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["box"]
    box: BoxEdges
    confidence: Probability | None = None


class NoulAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["noul"]
    noul: Probability


class OptionAnswer(BaseModel):
    """A Choice answer whose options are chosen by the request, not the four canonical ones."""

    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["choice"]
    choice: str = Field(min_length=1, max_length=120)
    probabilities: dict[str, Probability] | None = None
    confidence: Probability | None = None


ImageAnswer = Annotated[BoxAnswer | NoulAnswer | OptionAnswer, Field(discriminator="type")]


class ImageResponse(BaseModel):
    """Answers from an image request. Extra provider fields are ignored."""

    model_config = ConfigDict(extra="ignore", strict=True)
    model: str = Field(min_length=1, max_length=100)
    answers: dict[str, ImageAnswer]
    usage: Usage | None = None
