"""TechStack Schemas"""

from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class TechStackBase(BaseModel):
    """Base tech stack schema"""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    image: Optional[str] = Field(None, max_length=500)
    stack_config: dict = Field(default_factory=dict)
    display_order: int = Field(default=0, ge=0)

    @field_validator('stack_config', mode='before')
    @classmethod
    def ensure_stack_config_dict(cls, v):
        if v is None:
            return {}
        return v


class TechStackCreate(TechStackBase):
    """Schema for creating a new tech stack"""
    pass


class TechStackUpdate(BaseModel):
    """Schema for updating a tech stack"""
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    image: Optional[str] = Field(None, max_length=500)
    stack_config: Optional[dict] = None
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class TechStackResponse(TechStackBase):
    """Schema for tech stack response"""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TechStacksResponse(BaseModel):
    """Schema for list of tech stacks"""
    data: list[TechStackResponse]
    count: int


# File/Folder schemas for skill management
class FileNode(BaseModel):
    """Schema for file/folder node in tree"""
    name: str
    type: str  # "file" or "folder"
    path: str
    children: Optional[list["FileNode"]] = None


class FileContent(BaseModel):
    """Schema for file content"""
    path: str
    content: str


class CreateFileRequest(BaseModel):
    """Schema for creating a file"""
    path: str
    content: str = ""


class UpdateFileRequest(BaseModel):
    """Schema for updating a file"""
    path: str
    content: str


class CreateFolderRequest(BaseModel):
    """Schema for creating a folder"""
    path: str
