"""Persona Template Schemas"""

from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class PersonaBase(BaseModel):
    """Base persona template schema"""
    name: str = Field(..., min_length=1, max_length=100)
    role_type: str = Field(..., min_length=1, max_length=50)
    personality_traits: list[str] = Field(default_factory=list)
    communication_style: str = Field(..., min_length=1, max_length=500)
    persona_metadata: dict = Field(default_factory=dict)
    display_order: int = Field(default=0, ge=0)

    @field_validator('personality_traits', mode='before')
    @classmethod
    def ensure_personality_traits_list(cls, v):
        if v is None:
            return []
        return v

    @field_validator('persona_metadata', mode='before')
    @classmethod
    def ensure_persona_metadata_dict(cls, v):
        if v is None:
            return {}
        return v

    @field_validator('display_order', mode='before')
    @classmethod
    def ensure_display_order_int(cls, v):
        if v is None:
            return 0
        return v


class PersonaCreate(PersonaBase):
    """Schema for creating a new persona template"""
    pass


class PersonaUpdate(BaseModel):
    """Schema for updating a persona template"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role_type: Optional[str] = Field(None, min_length=1, max_length=50)
    personality_traits: Optional[list[str]] = None
    communication_style: Optional[str] = Field(None, min_length=1, max_length=500)
    persona_metadata: Optional[dict] = None
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class PersonaResponse(PersonaBase):
    """Schema for persona template response"""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PersonaWithUsageStats(PersonaResponse):
    """Persona with usage statistics"""
    active_agents_count: int = 0
    total_agents_created: int = 0
