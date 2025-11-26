"""Artifact schemas for structured agent outputs."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class RequirementItem(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    type: str


class PRDArtifact(BaseModel):
    title: str
    overview: str
    goals: List[str]
    target_users: List[str]
    requirements: List[RequirementItem]
    acceptance_criteria: List[str]
    constraints: List[str]
    risks: List[str]
    next_steps: Optional[List[str]] = Field(default_factory=list)


class ArchitectureComponent(BaseModel):
    name: str
    type: str
    technology: str
    description: str
    dependencies: List[str] = Field(default_factory=list)
    interfaces: Optional[List[str]] = Field(default_factory=list)


class ArchitectureArtifact(BaseModel):
    title: str
    overview: str
    components: List[ArchitectureComponent]
    data_flow: str
    deployment: str
    scalability_considerations: str
    security_considerations: Optional[str] = None


class UserStoryItem(BaseModel):
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    priority: str
    story_points: Optional[int] = None


class UserStoryArtifact(BaseModel):
    epic_title: str
    epic_description: str
    stories: List[UserStoryItem]
    total_story_points: Optional[int] = None


class AnalysisSection(BaseModel):
    title: str
    content: str
    findings: Optional[List[str]] = Field(default_factory=list)
    recommendations: Optional[List[str]] = Field(default_factory=list)


class AnalysisArtifact(BaseModel):
    title: str
    summary: str
    sections: List[AnalysisSection]
    conclusion: str
    next_steps: List[str]


class CodeFile(BaseModel):
    filename: str
    filepath: str
    language: str
    content: str
    description: Optional[str] = None


class CodeArtifact(BaseModel):
    title: str
    description: str
    files: List[CodeFile]
    dependencies: Optional[List[str]] = Field(default_factory=list)
    setup_instructions: Optional[str] = None


class TestCase(BaseModel):
    id: str
    title: str
    description: str
    steps: List[str]
    expected_result: str
    priority: str


class TestPlanArtifact(BaseModel):
    title: str
    scope: str
    test_cases: List[TestCase]
    test_data_requirements: Optional[List[str]] = Field(default_factory=list)
    environment_requirements: Optional[str] = None
