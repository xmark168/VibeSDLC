"""Pydantic schemas for BA agent LLM structured output.

Following the pattern from Developer V2 agent for reliable JSON parsing.
Using with_structured_output() instead of manual regex + json.loads().
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# =============================================================================
# INTENT ANALYSIS
# =============================================================================

class IntentOutput(BaseModel):
    """Output schema for analyze_intent node."""
    intent: Literal[
        "conversational", "interview", "prd_create", "prd_update",
        "extract_stories", "stories_update", "stories_approve", "domain_analysis"
    ] = Field(description="Classified user intent")
    reasoning: str = Field(description="Brief explanation of why this intent was chosen")


# =============================================================================
# INTERVIEW / QUESTIONS
# =============================================================================

class Question(BaseModel):
    """Single interview question."""
    text: str = Field(description="Question text in Vietnamese")
    type: Literal["open", "multichoice"] = Field(default="multichoice", description="Question type")
    options: Optional[List[str]] = Field(default=None, description="Options for multichoice")
    allow_multiple: bool = Field(default=False, description="Allow multiple selections")
    category: Optional[str] = Field(default=None, description="Category: target_users, main_features, risks, etc.")


class QuestionsOutput(BaseModel):
    """Output schema for interview_requirements node."""
    questions: List[Question] = Field(description="List of clarification questions")


# =============================================================================
# PRD (Product Requirements Document)
# =============================================================================

class PRDFeature(BaseModel):
    """Single feature in PRD."""
    name: str = Field(description="Feature name")
    description: str = Field(description="Short description (1-2 sentences)")
    priority: Literal["high", "medium", "low"] = Field(default="medium")
    requirements: List[str] = Field(default=[], description="Feature requirements")


class PRDOutput(BaseModel):
    """Output schema for generate_prd node."""
    project_name: str = Field(description="Project name")
    version: str = Field(default="1.0")
    overview: str = Field(description="Brief overview (1-2 sentences)")
    objectives: List[str] = Field(default=[], description="Project objectives (2-5 items)")
    target_users: List[str] = Field(default=[], description="Target user types")
    features: List[PRDFeature] = Field(description="Core features (5-7 for MVP)")
    constraints: List[str] = Field(default=[], description="Technical/business constraints")
    success_metrics: List[str] = Field(default=[], description="Success metrics")
    risks: List[str] = Field(default=[], description="Identified risks")
    message: str = Field(description="Natural message to user (Vietnamese, with emoji)")


class PRDUpdateOutput(BaseModel):
    """Output schema for update_prd node."""
    updated_prd: PRDOutput = Field(description="Complete updated PRD")
    change_summary: str = Field(description="Summary of changes made (Vietnamese)")
    message: str = Field(description="Natural message to user (Vietnamese, with emoji)")


# =============================================================================
# DOCUMENT ANALYSIS
# =============================================================================

class CollectedInfo(BaseModel):
    """Information extracted from document."""
    target_users: Optional[str] = Field(default=None)
    main_features: Optional[str] = Field(default=None)
    business_model: Optional[str] = Field(default=None)
    priorities: Optional[str] = Field(default=None)
    constraints: Optional[str] = Field(default=None)


class DocumentAnalysisOutput(BaseModel):
    """Output schema for analyze_document_content."""
    document_type: Literal["complete_requirements", "partial_requirements", "not_requirements"] = Field(
        description="Type of document detected"
    )
    detected_doc_kind: str = Field(default="", description="Brief description if not_requirements")
    collected_info: CollectedInfo = Field(default_factory=CollectedInfo)
    completeness_score: float = Field(ge=0.0, le=1.0, description="0.0 to 1.0")
    is_comprehensive: bool = Field(default=False)
    summary: str = Field(description="Brief summary in Vietnamese")
    extracted_items: List[str] = Field(default=[], description="Items successfully extracted")
    missing_info: List[str] = Field(default=[], description="Missing categories")


# =============================================================================
# USER STORIES
# =============================================================================

class UserStory(BaseModel):
    """Single user story following INVEST criteria."""
    id: str = Field(description="Unique ID, e.g., EPIC-001-US-001")
    epic_id: str = Field(description="Parent epic ID")
    title: str = Field(description="As a [user], I want [goal] so that [benefit]")
    description: str = Field(description="Business-focused description")
    requirements: List[str] = Field(default=[], description="5-8 requirements")
    acceptance_criteria: List[str] = Field(default=[], description="4-6 Given/When/Then scenarios")
    priority: int = Field(default=2, ge=1, le=3, description="1=High, 2=Medium, 3=Low")
    story_point: int = Field(default=3, description="Fibonacci: 1,2,3,5,8,13")
    dependencies: List[str] = Field(default=[], description="Story IDs that must complete first")


class Epic(BaseModel):
    """Epic containing multiple user stories."""
    id: str = Field(description="Unique ID, e.g., EPIC-001")
    title: str = Field(description="Short descriptive title")
    description: str = Field(description="Business value (1-2 sentences)")
    domain: str = Field(description="Feature domain: Homepage, Dashboard, Auth, Product, Cart, etc.")
    feature_refs: List[str] = Field(default=[], description="Related PRD feature names (for Phase 1)")
    stories: List[UserStory] = Field(default=[], description="User stories in this epic")


class EpicsOnlyOutput(BaseModel):
    """Output schema for extract_epics_only (Phase 1 of batch processing)."""
    epics: List[Epic] = Field(description="Epics without stories (stories field empty)")
    message_template: str = Field(
        description="Message template with {epic_count} and {story_count} placeholders"
    )
    approval_template: str = Field(
        description="Approval message template with {epic_count} and {story_count} placeholders"
    )


class StoriesForEpicOutput(BaseModel):
    """Output schema for generate_stories_for_epic (Phase 2)."""
    stories: List[UserStory] = Field(description="Stories for this specific epic")


class FullStoriesOutput(BaseModel):
    """Output schema for extract_stories (single-call mode) and update_stories."""
    epics: List[Epic] = Field(description="Epics with stories populated")
    message_template: str = Field(
        default="",
        description="Message template with {epic_count} and {story_count} placeholders"
    )
    approval_template: str = Field(
        default="",
        description="Approval message template with {epic_count} and {story_count} placeholders"
    )
    change_summary: str = Field(default="", description="Summary of changes (for updates)")


# =============================================================================
# STORY VERIFICATION
# =============================================================================

class INVESTIssue(BaseModel):
    """Single INVEST criterion issue."""
    code: Literal["I", "N", "V", "E", "S", "T"] = Field(description="INVEST criterion code")
    issue: str = Field(description="Issue description in Vietnamese")


class VerifyStoryOutput(BaseModel):
    """Output schema for verify_story_simple."""
    is_duplicate: bool = Field(default=False)
    duplicate_of: Optional[str] = Field(default=None, description="Title of similar story if duplicate")
    duplicate_reason: Optional[str] = Field(default=None, description="Explanation if duplicate")
    invest_score: int = Field(ge=1, le=6, description="1-6 INVEST score")
    invest_issues: List[INVESTIssue] = Field(default=[], description="INVEST issues found")
    suggested_title: Optional[str] = Field(default=None)
    suggested_description: Optional[str] = Field(default=None)
    suggested_requirements: Optional[List[str]] = Field(default=None)
    suggested_acceptance_criteria: Optional[List[str]] = Field(default=None)
    summary: str = Field(description="Brief review summary in Vietnamese")


# =============================================================================
# CONVERSATIONAL RESPONSE
# =============================================================================

class ConversationalOutput(BaseModel):
    """Output schema for respond_conversational (optional, can use raw text)."""
    message: str = Field(description="Natural response message in Vietnamese")


# =============================================================================
# DOMAIN ANALYSIS FEEDBACK
# =============================================================================

class DocumentFeedbackOutput(BaseModel):
    """Output schema for generate_document_feedback."""
    message: str = Field(description="Natural feedback message in Vietnamese with emoji")
