"""Pydantic schemas for Tester agent structured outputs."""

from typing import List, Literal
from pydantic import BaseModel, Field


# =============================================================================
# Router schemas
# =============================================================================

class RoutingDecision(BaseModel):
    """Routing decision for tester."""
    action: str = Field(description="PLAN_TESTS | TEST_STATUS | CONVERSATION")
    reason: str = Field(description="Brief reason for routing decision")


# =============================================================================
# Plan schemas
# =============================================================================

class TestPlanStep(BaseModel):
    """Single test plan step."""
    order: int
    type: str  # "integration" or "unit"
    story_id: str
    story_title: str
    file_path: str
    description: str
    scenarios: List[str]
    dependencies: List[str] = []


class TestPlanOutput(BaseModel):
    """Test plan output from LLM."""
    test_plan: List[TestPlanStep]


# =============================================================================
# Implement schemas
# =============================================================================

class TestFileOutput(BaseModel):
    """Structured output for test file generation. NO tool calling needed."""
    file_path: str = Field(description="Relative path to the test file")
    content: str = Field(description="Complete test file content (TypeScript/JavaScript)")
    summary: str = Field(default="", description="Brief summary of what was tested")


# =============================================================================
# Review schemas
# =============================================================================

class ReviewDecision(BaseModel):
    """Structured review decision output."""
    decision: Literal["LGTM", "LBTM"] = Field(description="LGTM (Looks Good To Me) or LBTM (Looks Bad To Me)")
    feedback: str = Field(default="", description="Brief explanation of decision")
    issues: List[str] = Field(default_factory=list, description="List of specific issues found")


# =============================================================================
# Analyze errors schemas
# =============================================================================

class FixStep(BaseModel):
    """Single fix step."""
    file_path: str = Field(description="Path to file to fix")
    description: str = Field(default="Fix error", description="Description of the fix")
    action: str = Field(default="modify", description="Action: create/modify/delete")
    find_code: str = Field(default="", description="Code to find and replace")
    replace_with: str = Field(default="", description="Replacement code")


class ErrorAnalysisOutput(BaseModel):
    """Structured output for error analysis."""
    root_cause: str = Field(description="Root cause of the error")
    error_code: str = Field(default="UNKNOWN", description="Error classification code")
    fix_steps: List[FixStep] = Field(description="List of fix steps")
