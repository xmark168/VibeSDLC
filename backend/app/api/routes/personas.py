"""Persona Template Management API Routes"""

import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query
from sqlmodel import select, func

from app.api.deps import SessionDep, get_current_user
from app.models import AgentPersonaTemplate, Agent, User
from app.schemas.persona import (
    PersonaCreate,
    PersonaUpdate,
    PersonaResponse,
    PersonaWithUsageStats,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("", response_model=list[PersonaResponse])
def list_personas(
    session: SessionDep,
    current_user: User = None,
    role_type: Optional[str] = Query(None, description="Filter by role type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all persona templates with optional filters"""
    query = select(AgentPersonaTemplate)
    
    if role_type:
        query = query.where(AgentPersonaTemplate.role_type == role_type)
    
    if is_active is not None:
        query = query.where(AgentPersonaTemplate.is_active == is_active)
    
    query = query.order_by(
        AgentPersonaTemplate.role_type,
        AgentPersonaTemplate.display_order,
        AgentPersonaTemplate.name
    ).offset(skip).limit(limit)
    
    personas = session.exec(query).all()
    return personas


@router.get("/by-role/{role_type}", response_model=list[PersonaResponse])
def list_personas_by_role(
    session: SessionDep,
    role_type: str,
    current_user: User = None,
    is_active: bool = Query(True, description="Filter by active status"),
):
    """Get all personas for a specific role type"""
    query = (
        select(AgentPersonaTemplate)
        .where(AgentPersonaTemplate.role_type == role_type)
        .where(AgentPersonaTemplate.is_active == is_active)
        .order_by(AgentPersonaTemplate.display_order, AgentPersonaTemplate.name)
    )
    
    personas = session.exec(query).all()
    return personas


@router.get("/with-stats", response_model=list[PersonaWithUsageStats])
def list_personas_with_stats(
    session: SessionDep,
    current_user: User = None,
    role_type: Optional[str] = Query(None),
):
    """List personas with usage statistics"""
    query = select(AgentPersonaTemplate)
    
    if role_type:
        query = query.where(AgentPersonaTemplate.role_type == role_type)
    
    query = query.order_by(
        AgentPersonaTemplate.role_type,
        AgentPersonaTemplate.display_order
    )
    
    personas = session.exec(query).all()
    
    # Calculate usage stats for each persona
    result = []
    for persona in personas:
        # Count active agents using this persona
        active_count = session.exec(
            select(func.count(Agent.id))
            .where(Agent.persona_template_id == persona.id)
            .where(Agent.status != "terminated")
        ).one()
        
        # Count total agents ever created with this persona
        total_count = session.exec(
            select(func.count(Agent.id))
            .where(Agent.persona_template_id == persona.id)
        ).one()
        
        result.append(
            PersonaWithUsageStats(
                **persona.model_dump(),
                active_agents_count=active_count,
                total_agents_created=total_count,
            )
        )
    
    return result


@router.get("/{persona_id}", response_model=PersonaResponse)
def get_persona(
    session: SessionDep,
    persona_id: UUID,
    current_user: User = None,
):
    """Get a specific persona template by ID"""
    persona = session.get(AgentPersonaTemplate, persona_id)
    
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona template with ID {persona_id} not found"
        )
    
    return persona


@router.post("", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
def create_persona(
    session: SessionDep,
    persona_data: PersonaCreate,
    current_user: User = None,
):
    """Create a new persona template"""
    # Check for duplicate name + role_type combination
    existing = session.exec(
        select(AgentPersonaTemplate)
        .where(AgentPersonaTemplate.name == persona_data.name)
        .where(AgentPersonaTemplate.role_type == persona_data.role_type)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Persona '{persona_data.name}' already exists for role type '{persona_data.role_type}'"
        )
    
    persona = AgentPersonaTemplate(**persona_data.model_dump())
    session.add(persona)
    session.commit()
    session.refresh(persona)
    
    logger.info(
        f"Created persona template: {persona.name} ({persona.role_type}) by {current_user.email if current_user else 'system'}"
    )
    
    return persona


@router.put("/{persona_id}", response_model=PersonaResponse)
def update_persona(
    session: SessionDep,
    persona_id: UUID,
    persona_update: PersonaUpdate,
    current_user: User = None,
):
    """Update a persona template"""
    persona = session.get(AgentPersonaTemplate, persona_id)
    
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona template with ID {persona_id} not found"
        )
    
    # Check for duplicate name + role if name or role is being changed
    if persona_update.name or persona_update.role_type:
        new_name = persona_update.name or persona.name
        new_role = persona_update.role_type or persona.role_type
        
        if new_name != persona.name or new_role != persona.role_type:
            existing = session.exec(
                select(AgentPersonaTemplate)
                .where(AgentPersonaTemplate.name == new_name)
                .where(AgentPersonaTemplate.role_type == new_role)
                .where(AgentPersonaTemplate.id != persona_id)
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Persona '{new_name}' already exists for role type '{new_role}'"
                )
    
    # Update fields
    update_data = persona_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(persona, key, value)
    
    session.add(persona)
    session.commit()
    session.refresh(persona)
    
    logger.info(
        f"Updated persona template: {persona.name} ({persona.id}) by {current_user.email if current_user else 'system'}"
    )
    
    return persona


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(
    session: SessionDep,
    persona_id: UUID,
    current_user: User = None,
    hard_delete: bool = Query(False, description="Permanently delete instead of deactivate"),
):
    """Delete or deactivate a persona template"""
    persona = session.get(AgentPersonaTemplate, persona_id)
    
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona template with ID {persona_id} not found"
        )
    
    # Check if persona is in use
    active_agents_count = session.exec(
        select(func.count(Agent.id))
        .where(Agent.persona_template_id == persona_id)
        .where(Agent.status != "terminated")
    ).one()
    
    if active_agents_count > 0 and hard_delete:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete persona: {active_agents_count} active agents are using it. Deactivate instead."
        )
    
    if hard_delete:
        session.delete(persona)
        logger.info(f"Hard deleted persona template: {persona.name} ({persona.id})")
    else:
        persona.is_active = False
        session.add(persona)
        logger.info(f"Deactivated persona template: {persona.name} ({persona.id})")
    
    session.commit()
    return None


@router.post("/{persona_id}/activate", response_model=PersonaResponse)
def activate_persona(
    session: SessionDep,
    persona_id: UUID,
    current_user: User = None,
):
    """Reactivate a deactivated persona template"""
    persona = session.get(AgentPersonaTemplate, persona_id)
    
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona template with ID {persona_id} not found"
        )
    
    persona.is_active = True
    session.add(persona)
    session.commit()
    session.refresh(persona)
    
    logger.info(f"Activated persona template: {persona.name} ({persona.id})")
    
    return persona
