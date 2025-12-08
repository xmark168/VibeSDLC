"""TechStack model for managing technology stacks."""

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import BaseModel


class TechStack(BaseModel, table=True):
    """TechStack model for storing technology stack configurations."""
    __tablename__ = "tech_stacks"
    
    code: str = Field(unique=True, max_length=50, index=True)
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=500)
    image: str | None = Field(default=None, max_length=500)
    
    # Flexible stack config: {"runtime": "bun", "framework": "nextjs", ...}
    stack_config: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    is_active: bool = Field(default=True)
    display_order: int = Field(default=0)
