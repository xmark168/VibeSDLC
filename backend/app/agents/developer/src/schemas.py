"""Developer V2 Schemas"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field

class PlanStep(BaseModel):
    """Single step in implementation plan."""
    order: int = Field(ge=1)
    description: str
    file_path: Optional[str] = None
    action: Literal["create", "modify", "delete", "test", "config", "review"] = "modify"

class SimpleStep(BaseModel):
    """Minimal step schema"""
    file_path: str = Field(description="Target file path")
    action: str = Field(description="'create' or 'modify'")
    task: str = Field(description="What to implement")
    dependencies: List[str] = Field(default=[], description="Files this step needs")

class SimplePlanOutput(BaseModel):
    """Optimized plan output."""
    steps: List[SimpleStep] = Field(description="Ordered implementation steps")


class SimpleReviewOutput(BaseModel):
    """Optimized review output."""
    decision: str = Field(description="'LGTM' or 'LBTM'")
    feedback: str = Field(default="", description="Fix suggestion if LBTM")


class ImplementOutput(BaseModel):
    """LLM output for implement step."""
    content: str = Field(description="Complete file content")

class StoryChatResponse(BaseModel):
    """Response for story chat message."""
    response: str = Field(description="Reply message to user in Vietnamese")
    action: str = Field(default="none", description="'pause' | 'cancel' | 'info' | 'none'")
    details: str = Field(default="", description="Additional context if action needed")
