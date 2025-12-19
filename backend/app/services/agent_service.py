"""Agent Service"""

from uuid import UUID
from typing import Optional

from sqlmodel import Session, select, update

from app.models import Agent, AgentStatus, AgentPersonaTemplate
from app.utils.name_generator import get_display_name


class AgentService:
    def __init__(self, session: Session):
        self.session = session

    def update_status(
        self, 
        agent_id: UUID, 
        status: AgentStatus,
        commit: bool = True
    ) -> Optional[Agent]:
        agent = self.session.get(Agent, agent_id)
        if agent:
            agent.status = status
            self.session.add(agent)
            if commit:
                self.session.commit()
                self.session.refresh(agent)
        return agent

    def bulk_update_status(
        self, 
        from_statuses: list[AgentStatus], 
        to_status: AgentStatus
    ) -> int:
        stmt = (
            update(Agent)
            .where(Agent.status.in_(from_statuses))
            .values(status=to_status)
        )
        result = self.session.exec(stmt)
        self.session.commit()
        return result.rowcount

    def get_by_id(self, agent_id: UUID) -> Optional[Agent]:
        return self.session.get(Agent, agent_id)

    def get_by_project_and_role(
        self, 
        project_id: UUID, 
        role_type: str
    ) -> Optional[Agent]:
        statement = (
            select(Agent)
            .where(Agent.project_id == project_id)
            .where(Agent.role_type == role_type)
        )
        return self.session.exec(statement).first()

    def get_by_project_and_name(
        self, 
        project_id: UUID, 
        name: str,
        case_sensitive: bool = False
    ) -> Optional[Agent]:
        statement = select(Agent).where(Agent.project_id == project_id)
        if case_sensitive:
            statement = statement.where(Agent.name == name)
        else:
            statement = statement.where(Agent.name.ilike(f"%{name}%"))
        return self.session.exec(statement).first()

    def get_all_by_project(self, project_id: UUID) -> list[Agent]:
        statement = select(Agent).where(Agent.project_id == project_id)
        return self.session.exec(statement).all()

    def get_all_by_role(self, role_type: str) -> list[Agent]:
        statement = select(Agent).where(Agent.role_type == role_type)
        return self.session.exec(statement).all()

    def get_by_statuses(
        self, 
        statuses: list[AgentStatus],
        role_type: Optional[str] = None
    ) -> list[Agent]:
        statement = select(Agent).where(Agent.status.in_(statuses))
        if role_type:
            statement = statement.where(Agent.role_type == role_type)
        return self.session.exec(statement).all()

    def get_by_project_and_names(
        self,
        project_id: UUID,
        names: list[str]
    ) -> list[Agent]:
        statement = (
            select(Agent)
            .where(Agent.project_id == project_id)
            .where(Agent.human_name.in_(names))
        )
        return self.session.exec(statement).all()

    def create(
        self,
        project_id: UUID,
        human_name: str,
        role_type: str,
        name: Optional[str] = None,
        agent_type: Optional[str] = None,
        status: AgentStatus = AgentStatus.idle,
        **kwargs
    ) -> Agent:
        agent = Agent(
            project_id=project_id,
            human_name=human_name,
            name=name or role_type,
            role_type=role_type,
            agent_type=agent_type or role_type,
            status=status,
            **kwargs
        )
        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)
        return agent

    def create_from_template(
        self,
        project_id: UUID,
        persona_template: AgentPersonaTemplate,
        status: AgentStatus = AgentStatus.idle,
    ) -> Agent:
        display_name = get_display_name(
            persona_template.name, 
            persona_template.role_type
        )
        
        agent = Agent(
            project_id=project_id,
            persona_template_id=persona_template.id,
            
            human_name=persona_template.name,
            name=display_name,
            role_type=persona_template.role_type,
            agent_type=persona_template.role_type,
            
            personality_traits=persona_template.personality_traits.copy() if persona_template.personality_traits else [],
            communication_style=persona_template.communication_style,
            persona_metadata=persona_template.persona_metadata.copy() if persona_template.persona_metadata else {},
            
            status=status,
        )
        
        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)
        
        return agent

    def delete(self, agent_id: UUID) -> bool:
        agent = self.session.get(Agent, agent_id)
        if agent:
            self.session.delete(agent)
            self.session.commit()
            return True
        return False

    def count_by_status(self, role_type: Optional[str] = None) -> dict[str, int]:
        agents = self.get_all_by_role(role_type) if role_type else self.session.exec(select(Agent)).all()
        
        counts = {
            "idle": 0,
            "busy": 0,
            "error": 0,
            "stopped": 0,
            "starting": 0,
            "stopping": 0,
            "terminated": 0,
        }
        
        for agent in agents:
            if agent.status == AgentStatus.idle:
                counts["idle"] += 1
            elif agent.status in [AgentStatus.busy, AgentStatus.starting]:
                counts["busy"] += 1
            elif agent.status == AgentStatus.error:
                counts["error"] += 1
            elif agent.status == AgentStatus.stopped:
                counts["stopped"] += 1
            elif agent.status == AgentStatus.stopping:
                counts["stopping"] += 1
            elif agent.status == AgentStatus.terminated:
                counts["terminated"] += 1
        
        return counts
