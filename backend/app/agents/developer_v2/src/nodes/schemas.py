"""Pydantic schemas for LLM structured output in graph nodes."""
from pydantic import BaseModel, Field
from typing import List, Optional


class ImplementationStep(BaseModel):
    """Single implementation step. Order: database -> API -> components -> pages."""
    order: int = Field(description="Step order number")
    description: str = Field(description="What to implement")
    file_path: str = Field(description="Target file path")
    action: str = Field(description="'create' or 'modify'")
    dependencies: List[str] = Field(default=[], description="Context files to pre-load")


class AnalyzePlanOutput(BaseModel):
    """Output schema for analyze_and_plan node with MetaGPT-style logic analysis."""
    story_summary: str = Field(description="Brief summary")
    logic_analysis: List[List[str]] = Field(default=[], description="[[file_path, description], ...]")
    steps: List[ImplementationStep] = Field(description="Ordered implementation steps")


class ReviewOutput(BaseModel):
    """Code review output. LGTM=approve, LBTM=reject. Max 2 LBTM/step."""
    decision: str = Field(description="'LGTM' or 'LBTM'")
    review: str = Field(description="Review comments")
    feedback: str = Field(default="", description="Fix feedback if LBTM")


class SummarizeOutput(BaseModel):
    """IS_PASS gate output. YES=complete, NO=needs work. Max 2 NO iterations."""
    summary: str = Field(description="Implementation summary")
    todos: dict = Field(default={}, description="{file_path: issue}")
    is_pass: str = Field(description="'YES' or 'NO'")
    feedback: str = Field(default="", description="Fix feedback if NO")
