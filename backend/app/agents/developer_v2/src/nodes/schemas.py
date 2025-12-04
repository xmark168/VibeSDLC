"""Pydantic schemas for structured LLM output."""
from pydantic import BaseModel, Field
from typing import List, Optional


class ImplementationStep(BaseModel):
    """Single implementation step in the plan."""
    order: int = Field(description="Step order number (1, 2, 3...)")
    description: str = Field(description="What to implement in this file")
    file_path: str = Field(description="Exact file path (e.g., src/app/api/books/route.ts)")
    action: str = Field(description="'create' for new files, 'modify' for existing")
    dependencies: List[str] = Field(
        default=[],
        description="Files to read as context before implementing"
    )


class AnalyzePlanOutput(BaseModel):
    """Structured output for analyze_and_plan node.
    
    This schema ensures reliable JSON extraction from LLM responses
    using LangChain's with_structured_output() method.
    """
    story_summary: str = Field(
        description="Brief 1-sentence summary of the feature to implement"
    )
    logic_analysis: List[List[str]] = Field(
        default=[],
        description="Logic analysis: [[file_path, 'use client if needed, functions, components'], ...]"
    )
    steps: List[ImplementationStep] = Field(
        description="Ordered list of implementation steps (database → API → components → pages)"
    )


class ReviewOutput(BaseModel):
    """Structured output for code review."""
    decision: str = Field(description="'LGTM' to approve, 'LBTM' to request changes")
    review: str = Field(description="Review comments and observations")
    feedback: str = Field(default="", description="Specific feedback if LBTM")


class SummarizeOutput(BaseModel):
    """Structured output for code summarization."""
    summary: str = Field(description="Brief summary of what was implemented")
    todos: dict = Field(default={}, description="Dict of {file_path: issue} if any TODOs found")
    is_pass: str = Field(description="'YES' if complete, 'NO' if needs more work")
    feedback: str = Field(default="", description="What needs to be fixed if NO")
