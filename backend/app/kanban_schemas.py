"""
Kanban Schemas - Pydantic models for request/response validation

This module contains all schemas for the Lean Kanban system:
- Tech Stacks
- Agents
- Projects (with Kanban policies)
- Epics
- Stories (with workflow and status transitions)
- Agent Assignments
- Status History
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.enums import StoryStatus, StoryType, StoryPriority, AgentType


# ==================== TechStack Schemas ====================

class TechStackBase(BaseModel):
    """Base TechStack schema"""
    name: str = Field(..., min_length=1, max_length=100, description="Technology stack name")
    data: Optional[dict] = Field(None, description="Technology specifications, versions, configs")


class TechStackCreate(TechStackBase):
    """Schema for creating a new tech stack"""
    pass


class TechStackUpdate(BaseModel):
    """Schema for updating a tech stack"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    data: Optional[dict] = None


class TechStackResponse(TechStackBase):
    """Schema for tech stack response"""
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Agent Schemas ====================

class AgentBase(BaseModel):
    """Base Agent schema"""
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    type: AgentType = Field(..., description="Agent type")
    description: Optional[str] = Field(None, description="Agent description")
    capacity: Optional[int] = Field(None, ge=1, description="Maximum number of stories agent can handle")
    is_active: bool = Field(True, description="Is agent active")


class AgentCreate(AgentBase):
    """Schema for creating a new agent"""
    project_id: int = Field(..., description="Project ID that this agent belongs to")


class AgentUpdate(BaseModel):
    """Schema for updating an agent"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[AgentType] = None
    description: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    project_id: Optional[int] = None


class AgentResponse(AgentBase):
    """Schema for agent response"""
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Project Schemas ====================

class ProjectBase(BaseModel):
    """Base Project schema"""
    code: str = Field(..., min_length=1, max_length=50, description="Project code identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    color: Optional[str] = Field(None, max_length=7, pattern="^#[0-9A-Fa-f]{6}$", description="Hex color code (e.g., #FF5733)")
    icon: Optional[str] = Field(None, max_length=50, description="Icon name or emoji")
    working_directory: Optional[str] = Field(None, max_length=500, description="Project working directory path")
    tech_stack_id: Optional[int] = Field(None, description="Technology stack ID")
    kanban_policy: Optional[dict] = Field(None, description="Kanban board configuration")


class ProjectCreate(ProjectBase):
    """Schema for creating a new project"""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7, pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    working_directory: Optional[str] = Field(None, max_length=500)
    tech_stack_id: Optional[int] = None
    kanban_policy: Optional[dict] = None


class ProjectResponse(ProjectBase):
    """Schema for project response"""
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    # Nested objects (optional - can be expanded later)
    tech_stack: Optional[TechStackResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Epic Schemas ====================

class EpicBase(BaseModel):
    """Base Epic schema"""
    title: str = Field(..., min_length=1, max_length=255, description="Epic title")
    description: Optional[str] = Field(None, description="Epic description")
    project_id: int = Field(..., description="Project ID")


class EpicCreate(EpicBase):
    """Schema for creating a new epic"""
    pass


class EpicUpdate(BaseModel):
    """Schema for updating an epic"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class EpicResponse(BaseModel):
    """Schema for epic response"""
    id: int
    title: str
    description: Optional[str]
    project_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Story Schemas ====================

class StoryBase(BaseModel):
    """Base Story schema"""
    title: str = Field(..., min_length=1, max_length=255, description="Story title")
    description: Optional[str] = Field(None, description="Story description")
    epic_id: int = Field(..., description="Epic ID")
    type: StoryType = Field(StoryType.USER_STORY, description="Story type")
    priority: StoryPriority = Field(StoryPriority.MEDIUM, description="Story priority")
    acceptance_criteria: Optional[str] = Field(None, description="Acceptance Criteria")


class StoryCreate(StoryBase):
    """Schema for creating a new story"""
    pass


class StoryUpdate(BaseModel):
    """Schema for updating a story (status changes should use separate endpoint)"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[StoryType] = None
    priority: Optional[StoryPriority] = None
    acceptance_criteria: Optional[str] = None


class StoryStatusUpdate(BaseModel):
    """Schema for updating story status"""
    status: StoryStatus = Field(..., description="New story status")


class StoryResponse(BaseModel):
    """Schema for story response"""
    id: int
    title: str
    description: Optional[str]
    epic_id: int
    status: StoryStatus
    type: StoryType
    priority: StoryPriority
    acceptance_criteria: Optional[str]
    token_used: Optional[int]
    completed_at: Optional[datetime]
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StoryListResponse(BaseModel):
    """Schema for paginated story list response"""
    items: List[StoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== StoryAgentAssignment Schemas ====================

class AssignmentBase(BaseModel):
    """Base Assignment schema"""
    story_id: int = Field(..., description="Story ID")
    agent_id: int = Field(..., description="Agent ID")
    role: Optional[str] = Field(None, max_length=50, description="Specific role for this assignment")


class AssignmentCreate(AssignmentBase):
    """Schema for creating a new assignment"""
    pass


class AssignmentResponse(BaseModel):
    """Schema for assignment response"""
    id: int
    story_id: int
    agent_id: int
    role: Optional[str]
    assigned_at: datetime
    # Nested objects
    agent: Optional[AgentResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== StoryStatusHistory Schemas ====================

class StatusHistoryCreate(BaseModel):
    """Schema for creating status history"""
    story_id: int
    old_status: Optional[StoryStatus] = None
    new_status: StoryStatus
    changed_by_id: int

class StatusHistoryResponse(BaseModel):
    """Schema for status history response"""
    id: int
    story_id: int
    old_status: Optional[StoryStatus]
    new_status: StoryStatus
    changed_by_id: int
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Extended Response Schemas with Nested Data ====================

class StoryDetailedResponse(StoryResponse):
    """Detailed story response with relationships"""
    epic: Optional[EpicResponse] = None
    agent_assignments: List[AssignmentResponse] = []
    status_history: List[StatusHistoryResponse] = []

    model_config = ConfigDict(from_attributes=True)


class EpicDetailedResponse(EpicResponse):
    """Detailed epic response with stories"""
    stories: List[StoryResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ProjectDetailedResponse(ProjectResponse):
    """Detailed project response with epics"""
    epics: List[EpicResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ==================== Internal Create Schemas ====================

class ProjectCreateInternal(BaseModel):
    """Internal schema for creating project with owner_id"""
    code: str
    name: str
    working_directory: Optional[str] = None
    owner_id: int
    tech_stack_id: Optional[int] = None
    kanban_policy: Optional[dict] = None

class StoryCreateInternal(BaseModel):
    """Internal schema for creating story with status and created_by_id"""
    title: str
    description: Optional[str] = None
    epic_id: int
    type: StoryType
    priority: StoryPriority
    acceptance_criteria: Optional[str] = None
    status: StoryStatus
    created_by_id: int
