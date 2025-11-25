"""
Artifact schemas for structured agent outputs.

Each artifact type has a Pydantic schema defining its structure.
This ensures consistent, validated output from agents.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ==================== PRD SCHEMA ====================

class RequirementItem(BaseModel):
    """Individual requirement item"""
    id: str
    title: str
    description: str
    priority: str = Field(description="high, medium, low")
    type: str = Field(description="functional, non-functional")


class PRDArtifact(BaseModel):
    """Product Requirements Document structure"""
    title: str
    overview: str
    goals: List[str]
    target_users: List[str]
    requirements: List[RequirementItem]
    acceptance_criteria: List[str]
    constraints: List[str]
    risks: List[str]
    next_steps: Optional[List[str]] = Field(default_factory=list)


# ==================== ARCHITECTURE SCHEMA ====================

class ArchitectureComponent(BaseModel):
    """Architecture component description"""
    name: str
    type: str = Field(description="frontend, backend, database, service, cache")
    technology: str
    description: str
    dependencies: List[str] = Field(default_factory=list)
    interfaces: Optional[List[str]] = Field(default_factory=list)


class ArchitectureArtifact(BaseModel):
    """System architecture design"""
    title: str
    overview: str
    components: List[ArchitectureComponent]
    data_flow: str
    deployment: str
    scalability_considerations: str
    security_considerations: Optional[str] = None


# ==================== USER STORIES SCHEMA ====================

class UserStoryItem(BaseModel):
    """Individual user story"""
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    priority: str
    story_points: Optional[int] = None


class UserStoryArtifact(BaseModel):
    """Collection of user stories"""
    epic_title: str
    epic_description: str
    stories: List[UserStoryItem]
    total_story_points: Optional[int] = None


# ==================== ANALYSIS SCHEMA ====================

class AnalysisSection(BaseModel):
    """Section in an analysis document"""
    title: str
    content: str
    findings: Optional[List[str]] = Field(default_factory=list)
    recommendations: Optional[List[str]] = Field(default_factory=list)


class AnalysisArtifact(BaseModel):
    """General analysis document"""
    title: str
    summary: str
    sections: List[AnalysisSection]
    conclusion: str
    next_steps: List[str]


# ==================== CODE SCHEMA ====================

class CodeFile(BaseModel):
    """Individual code file"""
    filename: str
    filepath: str
    language: str
    content: str
    description: Optional[str] = None


class CodeArtifact(BaseModel):
    """Code artifact with multiple files"""
    title: str
    description: str
    files: List[CodeFile]
    dependencies: Optional[List[str]] = Field(default_factory=list)
    setup_instructions: Optional[str] = None


# ==================== TEST PLAN SCHEMA ====================

class TestCase(BaseModel):
    """Individual test case"""
    id: str
    title: str
    description: str
    steps: List[str]
    expected_result: str
    priority: str


class TestPlanArtifact(BaseModel):
    """Test plan document"""
    title: str
    scope: str
    test_cases: List[TestCase]
    test_data_requirements: Optional[List[str]] = Field(default_factory=list)
    environment_requirements: Optional[str] = None
