
"""Router for StoryEvent Router."""

import logging
from typing import Any, Dict
from uuid import UUID

from sqlmodel import Session, select

from app.kafka.event_schemas import AgentTaskType, BaseKafkaEvent
from app.kafka.producer import KafkaProducer
from app.models import Story
from app.core.db import engine
from app.agents.routers.base import BaseEventRouter

logger = logging.getLogger(__name__)

class StoryEventRouter(BaseEventRouter):
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        event_type = event_dict.get("event_type", "")
        return event_type in (
            "story.status.changed", 
            "story.cancel", 
            "story.pause", 
            "story.resume",
            "story.created",
            "story.review_action",
            "story.review_requested",
        )
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        event_type = event_dict.get("event_type", "")
        story_id = event_dict.get("story_id")
        project_id = event_dict.get("project_id")
        if event_type == "story.created":
            self.logger.info(f"New story created: {story_id} (auto-verify disabled)")
            return

        if event_type == "story.review_action":
            self.logger.info(f"Story review action: {event_dict.get('action')} for {story_id}")
            await self._handle_review_action(event_dict, project_id)
            return
        
        if event_type == "story.review_requested":
            self.logger.info(f"Story review requested: {story_id} in project {project_id}")
            await self._verify_new_story(event_dict, project_id)
            return
        
        if event_type == "story.cancel":
            self.logger.info(f"Story cancel requested: {story_id}")
            await self._cancel_story_task(event_dict, project_id)
            return
        
        if event_type == "story.pause":
            self.logger.info(f"Story pause requested: {story_id}")
            await self._pause_story_task(event_dict, project_id)
            return
        
        if event_type == "story.resume":
            self.logger.info(f"Story resume requested: {story_id}")
            await self._resume_story_task(event_dict, project_id)
            return

        payload = event_dict.get("payload", {})
        new_status = event_dict.get("new_status") or payload.get("to_status")
        old_status = event_dict.get("old_status") or payload.get("from_status")

        self.logger.info(
            f"Story {story_id} moved from {old_status} to {new_status} in project {project_id}"
        )

        if new_status == "InProgress":
            await self._route_to_developer(event_dict, project_id)
        elif new_status == "Review":
            await self._route_to_tester(event_dict, project_id)

    async def _route_to_developer(self, event_dict: Dict[str, Any], project_id: UUID) -> None:
        with Session(engine) as session:
            from app.services import AgentService
            agent_service = AgentService(session)
            developer = agent_service.get_by_project_and_role(
                project_id=project_id,
                role_type="developer"
            )

            if developer:
                story_title = event_dict.get('story_title', 'Unknown Story')
                content = f"Story '{story_title}' has been moved to In Progress. Please start development."

                await self.publish_task(
                    agent_id=developer.id,
                    task_type=AgentTaskType.IMPLEMENT_STORY,
                    source_event=event_dict,
                    routing_reason="story_status_changed_to_in_progress",
                    priority="high",
                    additional_context={
                        "story_id": event_dict.get("story_id"),
                        "content": content,
                        "execution_mode": "background",
                    }
                )

                self.logger.info(
                    f"Routed story status change to Developer: {developer.name} ({developer.id})"
                )
            else:
                self.logger.warning(
                    f"No Developer found in project {project_id} for story status change"
                )

    async def _route_to_tester(self, event_dict: Dict[str, Any], project_id: UUID) -> None:
        with Session(engine) as session:
            from app.services import AgentService
            from app.models import Story
            agent_service = AgentService(session)

            tester = agent_service.get_by_project_and_role(
                project_id=project_id,
                role_type="tester"
            )

            if tester:
                story_id = event_dict.get("story_id")
                
                story = session.get(Story, UUID(story_id))
                if not story:
                    self.logger.error(f"Story {story_id} not found")
                    return
                
                await self.publish_task(
                    agent_id=tester.id,
                    task_type=AgentTaskType.WRITE_TESTS,
                    source_event=event_dict,
                    routing_reason="story_status_changed_to_review",
                    priority="high",
                    additional_context={
                        "trigger_type": "status_review",
                        "story_ids": [str(story_id)],
                        "auto_generated": True,
                        "content": f"Auto-generate integration tests for story '{story.title}'",
                        "execution_mode": "background",
                        "worktree_path": story.worktree_path,
                        "branch_name": story.branch_name,
                    }
                )

                self.logger.info(
                    f"Routed to Tester with workspace: {story.worktree_path} "
                    f"({tester.name})"
                )
            else:
                self.logger.warning(
                    f"No Tester found in project {project_id} for story review testing"
                )

    async def _cancel_story_task(self, event_dict: Dict[str, Any], project_id: str | UUID) -> None:
        story_id = event_dict.get("story_id")
        self.logger.info(f"Story cancel event received for: {story_id}")
        from app.models import Story
        from app.services.agent_pool_service import AgentPoolService
        
        with Session(engine) as session:
            story = session.get(Story, UUID(story_id) if isinstance(story_id, str) else story_id)
            if story and story.assigned_agent_id:
                pool = AgentPoolService.find_pool_for_agent(story.assigned_agent_id)
                if pool:
                    pool.signal_agent(story.assigned_agent_id, story_id, "cancel")
                    self.logger.info(f"[cancel] Signal sent to agent {story.assigned_agent_id}")
                else:
                    self.logger.warning(f"[cancel] Agent {story.assigned_agent_id} not found in any pool")
            else:
                self.logger.warning(f"[cancel] No assigned_agent_id for story {story_id}")

    async def _pause_story_task(self, event_dict: Dict[str, Any], project_id: str | UUID) -> None:
        story_id = event_dict.get("story_id")
        self.logger.info(f"Story pause event received for: {story_id}")
        from app.models import Story
        from app.services.agent_pool_service import AgentPoolService
        
        with Session(engine) as session:
            story = session.get(Story, UUID(story_id) if isinstance(story_id, str) else story_id)
            if story and story.assigned_agent_id:
                pool = AgentPoolService.find_pool_for_agent(story.assigned_agent_id)
                if pool:
                    pool.signal_agent(story.assigned_agent_id, story_id, "pause")
                    self.logger.info(f"[pause] Signal sent to agent {story.assigned_agent_id}")
                else:
                    self.logger.warning(f"[pause] Agent {story.assigned_agent_id} not found in any pool")
            else:
                self.logger.warning(f"[pause] No assigned_agent_id for story {story_id}")

    async def _resume_story_task(self, event_dict: Dict[str, Any], project_id: str | UUID) -> None:
        story_id = event_dict.get("story_id")
        if isinstance(project_id, str):
            project_id = UUID(project_id)
        with Session(engine) as session:
            from app.services import AgentService
            agent_service = AgentService(session)
            
            developer = agent_service.get_by_project_and_role(
                project_id=project_id,
                role_type="developer"
            )
            
            if developer:
                await self.publish_task(
                    agent_id=developer.id,
                    task_type=AgentTaskType.IMPLEMENT_STORY,
                    source_event=event_dict,
                    routing_reason="story_resume",
                    priority="high",
                    additional_context={
                        "story_id": story_id,
                        "content": f"Resume paused story",
                        "resume": True,
                        "execution_mode": "background",
                    }
                )
                self.logger.info(f"Resumed story task: {story_id}")
            else:
                self.logger.warning(f"No Developer agent found to resume story {story_id}")

    async def _verify_new_story(self, event_dict: Dict[str, Any], project_id: str | UUID) -> None:
        from app.models import Story, ArtifactType
        from app.services import AgentService
        from app.services.artifact_service import ArtifactService
        from app.agents.business_analyst.src.nodes import verify_story_simple
        from app.kafka.event_schemas import AgentEvent
        story_id = event_dict.get("story_id")
        user_id = event_dict.get("user_id")

        if isinstance(project_id, str):
            project_id = UUID(project_id)

        ba_agent = None
        agent_name = "Business Analyst"
        agent_id = None

        try:
            with Session(engine) as session:
                new_story = session.get(Story, story_id)
                if not new_story:
                    self.logger.error(f"Story {story_id} not found for verification")
                    return

                artifact_service = ArtifactService(session)
                prd_artifact = artifact_service.get_latest_version(
                    project_id=project_id,
                    artifact_type=ArtifactType.PRD
                )
                full_prd = prd_artifact.content if prd_artifact else None

                from sqlmodel import select
                existing_stories = session.exec(
                    select(Story).where(
                        Story.project_id == project_id,
                        Story.id != story_id
                    )
                ).all()

                agent_service = AgentService(session)
                ba_model = agent_service.get_by_project_and_role(
                    project_id=project_id,
                    role_type="business_analyst"
                )

                if ba_model:
                    agent_name = ba_model.human_name or ba_model.name
                    agent_id = str(ba_model.id)
                    from app.agents.business_analyst import BusinessAnalyst
                    ba_agent = BusinessAnalyst(
                        agent_model=ba_model,
                        user_id=UUID(user_id) if user_id else None
                    )

            execution_id = str(uuid4())
            
            start_event = AgentEvent(
                event_type="agent.thinking",
                agent_name=agent_name,
                agent_id=agent_id or "ba-auto-verify",
                project_id=str(project_id),
                execution_id=execution_id,
                content="Processing request...",
                execution_context={
                    "mode": "background",
                    "task_type": "story_verify",
                    "display_mode": "chat",
                }
            )
            await self.producer.publish(topic=KafkaTopics.AGENT_EVENTS, event=start_event)

            state = {
                "new_story": new_story,
                "project_id": project_id,
                "full_prd": full_prd,
                "existing_stories": existing_stories,
                "execution_id": execution_id,  # Pass to nodes for response event
            }

            self.logger.info(
                f"Verifying story: {new_story.title} "
                f"(PRD: {'yes' if full_prd else 'no'}, existing: {len(existing_stories)})"
            )

            await verify_story_simple(state, agent=ba_agent)
            
            finish_event = AgentEvent(
                event_type="agent.completed",
                agent_name=agent_name,
                agent_id=agent_id or "ba-auto-verify",
                project_id=str(project_id),
                execution_id=execution_id,
                content="Story verification complete",
                execution_context={
                    "mode": "background",
                    "task_type": "story_verify",
                    "display_mode": "chat",
                }
            )
            await self.producer.publish(topic=KafkaTopics.AGENT_EVENTS, event=finish_event)

            self.logger.info(f"Story verification complete for {story_id}")

        except Exception as e:
            self.logger.error(f"Error verifying story {story_id}: {e}", exc_info=True)

    async def _handle_review_action(self, event_dict: Dict[str, Any], project_id: str | UUID) -> None:
        from app.agents.business_analyst.src.nodes import send_review_action_response
        from app.services import AgentService
        from app.kafka.event_schemas import AgentEvent
        story_id = event_dict.get("story_id")
        story_title = event_dict.get("story_title")
        action = event_dict.get("action")
        user_id = event_dict.get("user_id")

        if isinstance(project_id, str):
            project_id = UUID(project_id)

        ba_agent = None
        agent_name = "Business Analyst"
        agent_id = None

        try:
            with Session(engine) as session:
                agent_service = AgentService(session)
                ba_model = agent_service.get_by_project_and_role(
                    project_id=project_id,
                    role_type="business_analyst"
                )

                if ba_model:
                    agent_name = ba_model.human_name or ba_model.name
                    agent_id = str(ba_model.id)
                    
                    from app.agents.business_analyst import BusinessAnalyst
                    ba_agent = BusinessAnalyst(
                        agent_model=ba_model,
                        project_id=project_id,
                        user_id=UUID(user_id) if user_id else None
                    )

            await send_review_action_response(
                story_id=story_id,
                story_title=story_title,
                action=action,
                project_id=project_id,
                agent=ba_agent
            )

            self.logger.info(f"Review action response sent for story {story_id}, action: {action}")

        except Exception as e:
            self.logger.error(f"Error handling review action for {story_id}: {e}", exc_info=True)
