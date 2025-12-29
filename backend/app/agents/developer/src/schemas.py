"""Developer V2 Schemas"""

from dataclasses import dataclass
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


# Error Analysis Schemas

@dataclass
class ParsedError:
    """Parsed error information from build/test logs."""
    file_path: str
    line: Optional[int]
    column: Optional[int]
    error_code: Optional[str]
    error_type: str
    message: str


class ErrorAnalysisOutput(BaseModel):
    """Structured output for error analysis."""
    error_type: Literal["TEST_ERROR", "SOURCE_ERROR", "IMPORT_ERROR", "CONFIG_ERROR", "UNFIXABLE"] = Field(description="Error category")
    file_to_fix: str = Field(description="Primary file to fix")
    root_cause: str = Field(description="Brief root cause explanation")
    should_continue: bool = Field(description="True if error is fixable")
    fix_steps: List[PlanStep] = Field(default_factory=list, description="Steps to fix the error")
