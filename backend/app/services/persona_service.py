"""Persona Service - Manages agent persona templates."""

import random
from uuid import UUID
from typing import Optional
from sqlmodel import Session, select

from app.models import AgentPersonaTemplate


class PersonaService:
    """Service for managing persona templates"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_random_persona_for_role(
        self, 
        role_type: str,
        exclude_ids: Optional[list[UUID]] = None
    ) -> Optional[AgentPersonaTemplate]:
        """Get random active persona for role type.
        
        Args:
            role_type: Agent role type
            exclude_ids: Personas already used in project (for diversity)
            
        Returns:
            Random persona or None if no personas available
        """
        query = (
            select(AgentPersonaTemplate)
            .where(AgentPersonaTemplate.role_type == role_type)
            .where(AgentPersonaTemplate.is_active == True)
        )
        
        if exclude_ids:
            query = query.where(AgentPersonaTemplate.id.notin_(exclude_ids))
        
        personas = self.session.exec(query).all()
        
        if not personas:
            return None
        
        return random.choice(personas)
    
    def get_all_by_role(self, role_type: str) -> list[AgentPersonaTemplate]:
        """Get all active personas for role.
        
        Args:
            role_type: Agent role type
            
        Returns:
            List of personas ordered by display_order
        """
        return self.session.exec(
            select(AgentPersonaTemplate)
            .where(AgentPersonaTemplate.role_type == role_type)
            .where(AgentPersonaTemplate.is_active == True)
            .order_by(AgentPersonaTemplate.display_order)
        ).all()
    
    def get_by_name_and_role(
        self, 
        name: str, 
        role_type: str
    ) -> Optional[AgentPersonaTemplate]:
        """Get specific persona by name and role.
        
        Args:
            name: Persona name
            role_type: Agent role type
            
        Returns:
            Persona or None if not found
        """
        return self.session.exec(
            select(AgentPersonaTemplate)
            .where(AgentPersonaTemplate.name == name)
            .where(AgentPersonaTemplate.role_type == role_type)
        ).first()
    
    def get_by_id(self, persona_id: UUID) -> Optional[AgentPersonaTemplate]:
        """Get persona by ID.
        
        Args:
            persona_id: Persona template UUID
            
        Returns:
            Persona or None if not found
        """
        return self.session.get(AgentPersonaTemplate, persona_id)
    
    def get_all_active(self) -> list[AgentPersonaTemplate]:
        """Get all active personas across all roles.
        
        Returns:
            List of all active personas
        """
        return self.session.exec(
            select(AgentPersonaTemplate)
            .where(AgentPersonaTemplate.is_active == True)
            .order_by(AgentPersonaTemplate.role_type, AgentPersonaTemplate.display_order)
        ).all()
    
    def create(self, persona_data: dict) -> AgentPersonaTemplate:
        """Create new persona template.
        
        Args:
            persona_data: Dictionary with persona attributes
            
        Returns:
            Created persona template
        """
        persona = AgentPersonaTemplate(**persona_data)
        self.session.add(persona)
        self.session.commit()
        self.session.refresh(persona)
        return persona
    
    def update(self, persona_id: UUID, updates: dict) -> Optional[AgentPersonaTemplate]:
        """Update persona template.
        
        Args:
            persona_id: Persona UUID
            updates: Dictionary of fields to update
            
        Returns:
            Updated persona or None if not found
        """
        persona = self.session.get(AgentPersonaTemplate, persona_id)
        if not persona:
            return None
        
        for key, value in updates.items():
            if hasattr(persona, key):
                setattr(persona, key, value)
        
        self.session.add(persona)
        self.session.commit()
        self.session.refresh(persona)
        return persona
    
    def deactivate(self, persona_id: UUID) -> bool:
        """Deactivate persona template (soft delete).
        
        Args:
            persona_id: Persona UUID
            
        Returns:
            True if deactivated, False if not found
        """
        persona = self.session.get(AgentPersonaTemplate, persona_id)
        if not persona:
            return False
        
        persona.is_active = False
        self.session.add(persona)
        self.session.commit()
        return True
