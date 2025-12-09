"""Pydantic schemas for LLM structured output in graph nodes."""
from pydantic import BaseModel, Field
from typing import List, Optional


class SimpleStep(BaseModel):
    """Minimal step schema - reduces output tokens by 70-80%."""
    file_path: str = Field(description="Target file path")
    action: str = Field(description="'create' or 'modify'")
    task: str = Field(description="What to implement (1-2 sentences)")
    dependencies: List[str] = Field(default=[], description="Files this step needs as context")


class SimplePlanOutput(BaseModel):
    """Optimized plan output - only steps, no summary/analysis."""
    steps: List[SimpleStep] = Field(description="Ordered implementation steps")


# Legacy schemas (kept for backward compatibility)
class ImplementationStep(BaseModel):
    """Single implementation step. Order: database -> API -> components -> pages."""
    order: int = Field(description="Step order number")
    description: str = Field(description="What to implement")
    file_path: str = Field(description="Target file path")
    action: str = Field(description="'create' or 'modify'")
    dependencies: List[str] = Field(default=[], description="Context files to pre-load")
    skills: List[str] = Field(default=[], description="Skills to preload")


class AnalyzePlanOutput(BaseModel):
    """Legacy schema - use SimplePlanOutput instead."""
    story_summary: str = Field(description="Brief summary")
    logic_analysis: List[List[str]] = Field(default=[], description="[[file_path, description], ...]")
    steps: List[ImplementationStep] = Field(description="Ordered implementation steps")


class SimpleReviewOutput(BaseModel):
    """Optimized review output - only decision + feedback (~30 tokens vs ~300)."""
    decision: str = Field(description="'LGTM' or 'LBTM'")
    feedback: str = Field(default="", description="Fix suggestion if LBTM (1 sentence)")


class ReviewOutput(BaseModel):
    """Legacy - use SimpleReviewOutput instead."""
    decision: str = Field(description="'LGTM' or 'LBTM'")
    review: str = Field(description="Review comments")
    feedback: str = Field(default="", description="Fix feedback if LBTM")


class SummarizeOutput(BaseModel):
    """IS_PASS gate output. YES=complete, NO=needs work. Max 2 NO iterations."""
    summary: str = Field(description="Implementation summary")
    todos: dict = Field(default={}, description="{file_path: issue}")
    is_pass: str = Field(description="'YES' or 'NO'")
    feedback: str = Field(default="", description="Fix feedback if NO")
