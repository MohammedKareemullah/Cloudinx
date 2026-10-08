from pydantic import BaseModel
from typing import Literal


class AssessRequest(BaseModel):
    provider: Literal["aws", "azure", "both"] = "aws"
    aws_region: str | None = None
    azure_region: str | None = None
    scenarios: list[Literal["cost", "balanced", "performance"]] = ["cost", "balanced", "performance"]
    group_name: str | None = None


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None


class ChatResponse(BaseModel):
    text: str
