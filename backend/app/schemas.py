from pydantic import BaseModel, Field
from typing import Optional

class RuleIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    rule_type: str = Field(pattern="^(prohibited|required|claim|style)$")
    pattern: str = Field(min_length=1, max_length=300)
    replacement: str = ""
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    explanation: str = Field(min_length=3, max_length=1000)
    enabled: bool = True

class ReviewIn(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    content: str = Field(min_length=1, max_length=30000)
    created_by: str = "Creator"

class ContentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=30000)
    actor: str = "Creator"

class StatusUpdate(BaseModel):
    status: str = Field(pattern="^(in_review|changes_requested|approved|rejected)$")
    actor: str = "Reviewer"
    reason: str = ""

class CommentIn(BaseModel):
    actor: str = "Reviewer"
    body: str = Field(min_length=1, max_length=3000)
