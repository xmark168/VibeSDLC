"""
Team Leader Agent Consumer

Combines Router Agent, Insights Agent, and Team Leader Agent functionality into one intelligent orchestrator.
Uses CrewAI for ALL analysis and decision-making - no keyword fallback routing.

Responsibilities:
1. Analyze user messages using CrewAI to determine intent (delegation, insights, or hybrid)
2. Provide project insights and analytics by querying database
3. Delegate tasks to specialist agents (BA, Dev, Tester) with parallel support
4. Publish responses and routing decisions to appropriate Kafka topics
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta

from crewai import Task, Crew
from sqlmodel import Session, select, func

from app.core.config import settings
from app.core.db import engine
from app.models import Story, Blocker, StoryStatus, BlockerType
from app.crews.agents.team_leader import get_unified_team_leader_agent
from app.crews.events.kafka_consumer import create_consumer
from app.crews.events.kafka_producer import get_kafka_producer
from app.crews.events.event_schemas import (
    KafkaTopics,
    AgentTaskEvent,
    AgentResponseEvent,
    AgentRoutingEvent,
)

logger = logging.getLogger(__name__)


class TeamLeaderAgent:
    """
    Team Leader Agent - combines routing, insights, and delegation

    Single point of intelligence that:
    - Uses CrewAI to analyze ALL user messages (no keyword fallback)
    - Provides project insights and metrics from database
    - Delegates tasks to specialist agents with parallel support
    - Publishes comprehensive responses and routing decisions
    """

    def __init__(self):
        self.consumer = None
        self.producer = None
        self.agent = None
        self.running = False

    async def start(self):
        """Start the unified team leader agent consumer"""
        try:
            logger.info("=" * 80)
            logger.info("Starting Unified Team Leader Agent...")
            logger.info("=" * 80)

            # Get Unified Team Leader CrewAI agent
            self.agent = get_unified_unified_team_leader_agent()
            logger.info("✓ CrewAI agent initialized")

            # Get Kafka producer
            self.producer = await get_kafka_producer()
            logger.info("✓ Kafka producer initialized")

            # Create consumer for user messages
            self.consumer = await create_consumer(
                consumer_id="unified_unified_team_leader_agent",
                topics=[KafkaTopics.USER_MESSAGES],
                group_id="unified_team_leader_group",
                auto_offset_reset="latest"
            )
            logger.info("✓ Kafka consumer created")

            # Register message handler
            self.consumer.register_handler("user.message", self.handle_user_message)

            self.running = True
            logger.info("=" * 80)
            logger.info("✓ Unified Team Leader Agent started successfully")
            logger.info("  - Consuming from: USER_MESSAGES")
            logger.info("  - Publishing to: AGENT_TASKS_*, AGENT_RESPONSES, AGENT_ROUTING")
            logger.info("  - Capabilities: Routing, Insights, Delegation")
            logger.info("=" * 80)

            # Start consuming
            await self.consumer.consume()

        except Exception as e:
            logger.error(f"Error starting Unified Team Leader Agent: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop the unified team leader agent"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
        logger.info("Unified Team Leader Agent stopped")

    async def handle_user_message(self, event_data: Dict[str, Any]):
        """
        Handle incoming user messages with intelligent CrewAI analysis

        Event structure:
        {
            "message_id": UUID,
            "project_id": UUID,
            "user_id": UUID,
            "content": str,
            "metadata": dict (optional)
        }
        """
        try:
            message_id = UUID(event_data["message_id"])
            project_id = UUID(event_data["project_id"])
            user_id = UUID(event_data["user_id"])
            content = event_data["content"]
            metadata = event_data.get("metadata", {})

            logger.info("=" * 80)
            logger.info(f"🧠 Unified Team Leader analyzing message {message_id}")
            logger.info(f"   Project: {project_id}")
            logger.info(f"   User: {user_id}")
            logger.info(f"   Content: {content[:100]}...")
            logger.info("=" * 80)

            # Use CrewAI to analyze the message and determine action plan
            analysis = await self.analyze_user_message(content, str(project_id))

            logger.info(f"📊 Analysis complete:")
            logger.info(f"   Request Type: {analysis['request_type']}")
            logger.info(f"   Primary Action: {analysis['primary_action']}")
            logger.info(f"   Confidence: {analysis['confidence']}")
            logger.info("-" * 80)

            # Execute based on analysis
            if analysis['request_type'] == 'insights':
                # Insights-only request
                await self.handle_insights_request(
                    analysis, message_id, project_id, user_id, content
                )
            elif analysis['request_type'] == 'delegation':
                # Delegation-only request
                await self.handle_delegation_request(
                    analysis, message_id, project_id, user_id, content
                )
            elif analysis['request_type'] == 'hybrid':
                # Both insights and delegation
                await self.handle_hybrid_request(
                    analysis, message_id, project_id, user_id, content
                )
            else:
                # Unexpected type - log warning and default to delegation
                logger.warning(f"Unexpected request type: {analysis['request_type']}, defaulting to delegation")
                await self.handle_delegation_request(
                    analysis, message_id, project_id, user_id, content
                )

            logger.info("=" * 80)
            logger.info(f"✅ Message {message_id} processed successfully")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Error handling user message: {e}", exc_info=True)

    async def analyze_user_message(self, content: str, project_id: str) -> Dict[str, Any]:
        """
        Use CrewAI to deeply analyze user message and determine action plan

        Returns:
            Dict with:
            - request_type: 'insights' | 'delegation' | 'hybrid'
            - primary_action: str description
            - confidence: float (0.0-1.0)
            - delegation_plan: Optional[Dict] if delegation needed
            - insights_queries: Optional[List[str]] if insights needed
        """
        try:
            # Create analysis task for Unified Team Leader
            task = Task(
                description=f"""
                Analyze the following user message and determine the appropriate action plan.

                User Message: "{content}"
                Project ID: {project_id}

                You must determine:
                1. REQUEST TYPE: Is this asking for:
                   - 'insights': Project metrics, analytics, status, reports, data analysis
                   - 'delegation': Task to be done by a specialist (BA, Dev, Tester)
                   - 'hybrid': Both insights AND delegation needed

                2. If DELEGATION is needed, identify which specialist agent(s):
                   - BA (Business Analyst): Create/refine user stories, requirements, acceptance criteria
                   - Dev (Developer): Implement features, fix bugs, write code, refactoring
                   - Tester (QA): Create test cases, test plans, run tests, QA
                   - Multiple agents can be assigned for parallel work

                3. If INSIGHTS are needed, identify what metrics/data:
                   - Story status distribution (TODO, IN_PROGRESS, REVIEW, DONE counts)
                   - Blocked stories and blockers
                   - Cycle time analysis
                   - Workload distribution
                   - Recommendations

                Provide your analysis in this EXACT format:
                REQUEST_TYPE: [insights|delegation|hybrid]
                PRIMARY_ACTION: [one-line description]
                CONFIDENCE: [0.0-1.0]
                DELEGATION_NEEDED: [yes|no]
                PRIMARY_AGENT: [ba|dev|tester|none]
                ADDITIONAL_AGENTS: [comma-separated list or none]
                INSIGHTS_NEEDED: [yes|no]
                INSIGHTS_QUERIES: [comma-separated list of metrics needed, or none]
                RATIONALE: [brief explanation]
                """,
                expected_output="Structured analysis with request type, delegation plan, and insights queries",
                agent=self.agent,
            )

            # Execute task using Crew (in thread pool to avoid blocking)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._execute_crew_task,
                task
            )

            # Parse the result into structured analysis
            analysis = self._parse_analysis_result(str(result))

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing message: {e}", exc_info=True)
            # Fallback to safe default
            return {
                "request_type": "delegation",
                "primary_action": "Route to specialist agent",
                "confidence": 0.3,
                "delegation_plan": {
                    "primary_agent": "ba",
                    "additional_agents": [],
                    "rationale": f"Error during analysis: {str(e)}"
                },
                "insights_queries": []
            }

    def _execute_crew_task(self, task: Task) -> str:
        """Execute CrewAI task synchronously (runs in thread pool)"""
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=False
        )
        result = crew.kickoff()
        return str(result)

    def _parse_analysis_result(self, result: str) -> Dict[str, Any]:
        """
        Parse CrewAI analysis result into structured data

        Extracts request type, delegation plan, and insights queries from the analysis
        """
        result_lower = result.lower()

        # Default values
        request_type = "delegation"
        primary_action = "Process user request"
        confidence = 0.5
        delegation_plan = None
        insights_queries = []

        try:
            # Extract REQUEST_TYPE
            if "request_type:" in result_lower:
                if "insights" in result_lower.split("request_type:")[1].split("\n")[0]:
                    if "hybrid" in result_lower.split("request_type:")[1].split("\n")[0]:
                        request_type = "hybrid"
                    else:
                        request_type = "insights"
                elif "delegation" in result_lower.split("request_type:")[1].split("\n")[0]:
                    request_type = "delegation"

            # Extract PRIMARY_ACTION
            if "primary_action:" in result_lower:
                action_start = result.lower().find("primary_action:") + 15
                action_end = result.find("\n", action_start)
                if action_end == -1:
                    action_end = action_start + 200
                primary_action = result[action_start:action_end].strip()

            # Extract CONFIDENCE
            if "confidence:" in result_lower:
                conf_text = result_lower.split("confidence:")[1].split("\n")[0].strip()
                # Extract float from text (handles formats like "0.8" or "0.8/1.0")
                import re
                conf_match = re.search(r'(\d+\.?\d*)', conf_text)
                if conf_match:
                    confidence = float(conf_match.group(1))
                    if confidence > 1.0:
                        confidence = confidence / 100.0  # Handle percentage format

            # Extract DELEGATION_NEEDED and agents
            delegation_needed = "delegation_needed: yes" in result_lower
            if delegation_needed or request_type in ("delegation", "hybrid"):
                primary_agent = "ba"  # default
                additional_agents = []
                rationale = ""

                # Extract PRIMARY_AGENT
                if "primary_agent:" in result_lower:
                    agent_text = result_lower.split("primary_agent:")[1].split("\n")[0]
                    if "ba" in agent_text or "business analyst" in agent_text:
                        primary_agent = "ba"
                    elif "dev" in agent_text or "developer" in agent_text:
                        primary_agent = "dev"
                    elif "tester" in agent_text or "qa" in agent_text:
                        primary_agent = "tester"

                # Extract ADDITIONAL_AGENTS
                if "additional_agents:" in result_lower:
                    additional_text = result_lower.split("additional_agents:")[1].split("\n")[0]
                    if "ba" in additional_text and primary_agent != "ba":
                        additional_agents.append("ba")
                    if ("dev" in additional_text or "developer" in additional_text) and primary_agent != "dev":
                        additional_agents.append("dev")
                    if ("tester" in additional_text or "qa" in additional_text) and primary_agent != "tester":
                        additional_agents.append("tester")

                # Extract RATIONALE
                if "rationale:" in result_lower:
                    rat_start = result.lower().find("rationale:") + 10
                    rat_end = result.find("\n", rat_start)
                    if rat_end == -1:
                        rat_end = rat_start + 300
                    rationale = result[rat_start:rat_end].strip()

                delegation_plan = {
                    "primary_agent": primary_agent,
                    "additional_agents": additional_agents,
                    "rationale": rationale
                }

            # Extract INSIGHTS_QUERIES
            insights_needed = "insights_needed: yes" in result_lower
            if insights_needed or request_type in ("insights", "hybrid"):
                if "insights_queries:" in result_lower:
                    queries_text = result_lower.split("insights_queries:")[1].split("\n")[0]
                    # Parse comma-separated queries
                    if "none" not in queries_text and queries_text.strip():
                        raw_queries = queries_text.split(",")
                        insights_queries = [q.strip() for q in raw_queries if q.strip()]

        except Exception as e:
            logger.error(f"Error parsing analysis result: {e}", exc_info=True)

        return {
            "request_type": request_type,
            "primary_action": primary_action,
            "confidence": confidence,
            "delegation_plan": delegation_plan,
            "insights_queries": insights_queries,
            "full_analysis": result
        }

    async def handle_insights_request(
        self,
        analysis: Dict[str, Any],
        message_id: UUID,
        project_id: UUID,
        user_id: UUID,
        original_content: str
    ):
        """Handle insights-only requests - query database and provide analytics"""
        logger.info("📊 Handling INSIGHTS request")

        # Query database for project metrics
        insights_data = await self.generate_project_insights(project_id)

        # Format insights into human-readable response
        insights_response = self.format_insights_response(insights_data, analysis)

        # Publish insights response to AGENT_RESPONSES topic
        response_event = AgentResponseEvent(
            response_id=uuid.uuid4(),
            task_id=message_id,  # Use message_id as task_id for insights
            agent_type="unified_team_leader",
            project_id=project_id,
            content=insights_response,
            structured_data=insights_data,
            timestamp=datetime.utcnow()
        )

        await self.producer.publish_event(
            topic=KafkaTopics.AGENT_RESPONSES,
            event=response_event.model_dump(),
            key=str(project_id)
        )

        logger.info("✓ Insights response published to AGENT_RESPONSES")

        # Also publish routing event
        routing_event = AgentRoutingEvent(
            routing_id=uuid.uuid4(),
            message_id=message_id,
            project_id=project_id,
            assigned_agent="unified_team_leader",
            routing_reason="Insights request - handled directly by Team Leader",
            confidence=analysis['confidence'],
            timestamp=datetime.utcnow()
        )

        await self.producer.publish_event(
            topic=KafkaTopics.AGENT_ROUTING,
            event=routing_event.model_dump(),
            key=str(project_id)
        )

        logger.info("✓ Routing event published to AGENT_ROUTING")

    async def handle_delegation_request(
        self,
        analysis: Dict[str, Any],
        message_id: UUID,
        project_id: UUID,
        user_id: UUID,
        original_content: str
    ):
        """Handle delegation-only requests - route to specialist agent(s)"""
        logger.info("🎯 Handling DELEGATION request")

        delegation_plan = analysis.get('delegation_plan', {})
        primary_agent = delegation_plan.get('primary_agent', 'ba')
        additional_agents = delegation_plan.get('additional_agents', [])
        rationale = delegation_plan.get('rationale', '')

        # Log delegation strategy
        if additional_agents:
            logger.info(
                f"   PARALLEL DELEGATION: Primary={primary_agent}, "
                f"Additional={additional_agents} ({len(additional_agents) + 1} agents)"
            )
        else:
            logger.info(f"   SINGLE DELEGATION: Agent={primary_agent}")

        # Delegate to primary agent
        await self._delegate_to_agent(
            agent_type=primary_agent,
            message_id=message_id,
            project_id=project_id,
            user_id=user_id,
            task_description=original_content,
            context={
                "user_id": str(user_id),
                "delegated_by": "unified_team_leader",
                "intent": analysis['primary_action'],
                "rationale": rationale,
                "is_primary": True,
                "confidence": analysis['confidence']
            }
        )

        # Delegate to additional agents if specified (parallel delegation)
        for agent_type in additional_agents:
            await self._delegate_to_agent(
                agent_type=agent_type,
                message_id=message_id,
                project_id=project_id,
                user_id=user_id,
                task_description=original_content,
                context={
                    "user_id": str(user_id),
                    "delegated_by": "unified_team_leader",
                    "intent": analysis['primary_action'],
                    "rationale": rationale,
                    "is_primary": False,
                    "primary_agent": primary_agent,
                    "confidence": analysis['confidence']
                }
            )

        # Publish routing event
        all_agents = [primary_agent] + additional_agents
        routing_event = AgentRoutingEvent(
            routing_id=uuid.uuid4(),
            message_id=message_id,
            project_id=project_id,
            assigned_agent=primary_agent,
            routing_reason=f"Delegated to {', '.join(all_agents)} - {rationale}",
            confidence=analysis['confidence'],
            metadata={"all_agents": all_agents},
            timestamp=datetime.utcnow()
        )

        await self.producer.publish_event(
            topic=KafkaTopics.AGENT_ROUTING,
            event=routing_event.model_dump(),
            key=str(project_id)
        )

        logger.info("✓ Delegation and routing events published")

    async def handle_hybrid_request(
        self,
        analysis: Dict[str, Any],
        message_id: UUID,
        project_id: UUID,
        user_id: UUID,
        original_content: str
    ):
        """Handle hybrid requests - both insights AND delegation"""
        logger.info("🔀 Handling HYBRID request (Insights + Delegation)")

        # Generate insights first
        insights_data = await self.generate_project_insights(project_id)
        insights_response = self.format_insights_response(insights_data, analysis)

        # Publish insights response
        response_event = AgentResponseEvent(
            response_id=uuid.uuid4(),
            task_id=message_id,
            agent_type="unified_team_leader",
            project_id=project_id,
            content=insights_response,
            structured_data=insights_data,
            timestamp=datetime.utcnow()
        )

        await self.producer.publish_event(
            topic=KafkaTopics.AGENT_RESPONSES,
            event=response_event.model_dump(),
            key=str(project_id)
        )

        logger.info("✓ Insights response published")

        # Then handle delegation
        await self.handle_delegation_request(
            analysis, message_id, project_id, user_id, original_content
        )

        logger.info("✓ Hybrid request completed (insights + delegation)")

    async def _delegate_to_agent(
        self,
        agent_type: str,
        message_id: UUID,
        project_id: UUID,
        user_id: UUID,
        task_description: str,
        context: Dict[str, Any]
    ):
        """Delegate a task to a specific specialist agent"""
        try:
            task_id = uuid.uuid4()
            agent_task = AgentTaskEvent(
                task_id=task_id,
                agent_type=agent_type,
                project_id=project_id,
                user_message_id=message_id,
                task_description=task_description,
                context=context,
                timestamp=datetime.utcnow()
            )

            # Get appropriate topic for agent
            target_topic = self._get_agent_topic(agent_type)

            # Publish task event
            await self.producer.publish_event(
                topic=target_topic,
                event=agent_task.model_dump(),
                key=str(project_id)
            )

            logger.info(
                f"   ✓ Task {task_id} delegated to {agent_type} agent "
                f"(primary: {context.get('is_primary', False)})"
            )

        except Exception as e:
            logger.error(f"Error delegating to {agent_type} agent: {e}", exc_info=True)

    def _get_agent_topic(self, agent_type: str) -> str:
        """Get Kafka topic for specified agent type"""
        topic_map = {
            "ba": KafkaTopics.AGENT_TASKS_BA,
            "dev": KafkaTopics.AGENT_TASKS_DEV,
            "tester": KafkaTopics.AGENT_TASKS_TESTER,
        }
        return topic_map.get(agent_type, KafkaTopics.AGENT_TASKS_BA)

    # ============================================================================
    # INSIGHTS ENGINE - Database queries and metrics
    # ============================================================================

    async def generate_project_insights(self, project_id: UUID) -> Dict[str, Any]:
        """
        Generate comprehensive project insights by querying database

        Returns:
            Dict containing metrics and analytics
        """
        try:
            # Run database queries in thread pool
            loop = asyncio.get_event_loop()
            insights = await loop.run_in_executor(
                None,
                self._query_project_insights,
                project_id
            )
            return insights

        except Exception as e:
            logger.error(f"Error generating project insights: {e}", exc_info=True)
            return {
                "error": str(e),
                "project_id": str(project_id)
            }

    def _query_project_insights(self, project_id: UUID) -> Dict[str, Any]:
        """
        Query database for project insights (runs synchronously in thread pool)

        Metrics calculated:
        - Story status distribution
        - Blocked stories
        - Cycle time analysis
        - Workload distribution
        - Recommendations
        """
        with Session(engine) as session:
            # Fetch all stories for project
            statement = select(Story).where(Story.project_id == project_id)
            stories = session.exec(statement).all()

            if not stories:
                return {
                    "project_id": str(project_id),
                    "story_count": 0,
                    "message": "No stories found for this project"
                }

            # Calculate metrics
            status_distribution = self._calculate_status_distribution(stories)
            blocked_stories = self._find_blocked_stories(stories)
            cycle_time_analysis = self._analyze_cycle_time(stories)
            workload_analysis = self._analyze_workload(stories)
            recommendations = self._generate_recommendations(stories, blocked_stories)

            return {
                "project_id": str(project_id),
                "story_count": len(stories),
                "status_distribution": status_distribution,
                "blocked_stories": blocked_stories,
                "cycle_time": cycle_time_analysis,
                "workload": workload_analysis,
                "recommendations": recommendations,
                "generated_at": datetime.utcnow().isoformat()
            }

    def _calculate_status_distribution(self, stories: List[Story]) -> Dict[str, int]:
        """Calculate story count by status"""
        distribution = {
            "TODO": 0,
            "IN_PROGRESS": 0,
            "REVIEW": 0,
            "DONE": 0
        }

        for story in stories:
            status_name = story.status.name if hasattr(story.status, 'name') else str(story.status)
            if status_name in distribution:
                distribution[status_name] += 1

        return distribution

    def _find_blocked_stories(self, stories: List[Story]) -> List[Dict[str, Any]]:
        """Find stories with active blockers"""
        blocked = []

        for story in stories:
            if story.blockers:
                blocked.append({
                    "story_id": str(story.id),
                    "title": getattr(story, 'title', f"Story {story.id}"),
                    "status": story.status.name if hasattr(story.status, 'name') else str(story.status),
                    "blocker_count": len(story.blockers),
                    "blockers": [
                        {
                            "type": blocker.blocker_type.name if hasattr(blocker.blocker_type, 'name') else str(blocker.blocker_type),
                            "description": blocker.description
                        }
                        for blocker in story.blockers
                    ]
                })

        return blocked

    def _analyze_cycle_time(self, stories: List[Story]) -> Dict[str, Any]:
        """Analyze cycle time for completed stories"""
        completed_stories = [s for s in stories if s.status == StoryStatus.DONE and s.completed_at]

        if not completed_stories:
            return {
                "completed_count": 0,
                "average_days": None,
                "message": "No completed stories with completion dates"
            }

        cycle_times = []
        for story in completed_stories:
            if story.created_at and story.completed_at:
                delta = story.completed_at - story.created_at
                cycle_times.append(delta.total_seconds() / 86400)  # Convert to days

        if not cycle_times:
            return {
                "completed_count": len(completed_stories),
                "average_days": None,
                "message": "No valid cycle time data"
            }

        average_cycle_time = sum(cycle_times) / len(cycle_times)
        min_cycle_time = min(cycle_times)
        max_cycle_time = max(cycle_times)

        return {
            "completed_count": len(completed_stories),
            "average_days": round(average_cycle_time, 2),
            "min_days": round(min_cycle_time, 2),
            "max_days": round(max_cycle_time, 2)
        }

    def _analyze_workload(self, stories: List[Story]) -> Dict[str, Any]:
        """Analyze workload distribution across team members"""
        assignee_workload = {}

        for story in stories:
            if story.assignee_id:
                assignee_id = str(story.assignee_id)
                if assignee_id not in assignee_workload:
                    assignee_workload[assignee_id] = {
                        "total": 0,
                        "in_progress": 0,
                        "review": 0,
                        "done": 0
                    }

                assignee_workload[assignee_id]["total"] += 1

                if story.status == StoryStatus.IN_PROGRESS:
                    assignee_workload[assignee_id]["in_progress"] += 1
                elif story.status == StoryStatus.REVIEW:
                    assignee_workload[assignee_id]["review"] += 1
                elif story.status == StoryStatus.DONE:
                    assignee_workload[assignee_id]["done"] += 1

        unassigned_count = len([s for s in stories if not s.assignee_id])

        return {
            "assignee_workload": assignee_workload,
            "unassigned_stories": unassigned_count,
            "team_member_count": len(assignee_workload)
        }

    def _generate_recommendations(
        self,
        stories: List[Story],
        blocked_stories: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable recommendations based on project data"""
        recommendations = []

        # Check for high blocker count
        if len(blocked_stories) > 3:
            recommendations.append(
                f"⚠️ High number of blocked stories ({len(blocked_stories)}). "
                "Consider a team sync to unblock these items."
            )

        # Check for unstarted stories
        todo_count = len([s for s in stories if s.status == StoryStatus.TODO])
        if todo_count > 10:
            recommendations.append(
                f"📋 Large backlog of TODO stories ({todo_count}). "
                "Consider prioritizing and assigning these stories."
            )

        # Check for stories in review
        review_count = len([s for s in stories if s.status == StoryStatus.REVIEW])
        if review_count > 5:
            recommendations.append(
                f"👀 Many stories in review ({review_count}). "
                "Consider allocating more review capacity."
            )

        # Check for unassigned stories
        unassigned_count = len([s for s in stories if not s.assignee_id])
        if unassigned_count > 5:
            recommendations.append(
                f"👤 High number of unassigned stories ({unassigned_count}). "
                "Consider assigning these to team members."
            )

        if not recommendations:
            recommendations.append("✅ Project health looks good! Keep up the good work.")

        return recommendations

    def format_insights_response(
        self,
        insights_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> str:
        """Format insights data into human-readable response"""
        if "error" in insights_data:
            return f"❌ Error generating insights: {insights_data['error']}"

        if insights_data.get("story_count", 0) == 0:
            return "📊 No stories found for this project yet."

        # Build formatted response
        lines = ["📊 **Project Insights Report**", ""]

        # Status distribution
        lines.append("**Story Status Distribution:**")
        status_dist = insights_data.get("status_distribution", {})
        for status, count in status_dist.items():
            lines.append(f"  - {status}: {count}")
        lines.append("")

        # Blocked stories
        blocked = insights_data.get("blocked_stories", [])
        if blocked:
            lines.append(f"**Blocked Stories:** {len(blocked)} stories blocked")
            for story in blocked[:3]:  # Show first 3
                lines.append(f"  - {story.get('title', 'Untitled')} ({story.get('blocker_count')} blockers)")
            if len(blocked) > 3:
                lines.append(f"  - ... and {len(blocked) - 3} more")
            lines.append("")

        # Cycle time
        cycle_time = insights_data.get("cycle_time", {})
        if cycle_time.get("average_days"):
            lines.append("**Cycle Time Analysis:**")
            lines.append(f"  - Average: {cycle_time['average_days']} days")
            lines.append(f"  - Min: {cycle_time['min_days']} days")
            lines.append(f"  - Max: {cycle_time['max_days']} days")
            lines.append("")

        # Workload
        workload = insights_data.get("workload", {})
        if workload.get("assignee_workload"):
            lines.append("**Workload Distribution:**")
            lines.append(f"  - Team members: {workload.get('team_member_count', 0)}")
            lines.append(f"  - Unassigned stories: {workload.get('unassigned_stories', 0)}")
            lines.append("")

        # Recommendations
        recommendations = insights_data.get("recommendations", [])
        if recommendations:
            lines.append("**Recommendations:**")
            for rec in recommendations:
                lines.append(f"  {rec}")
            lines.append("")

        return "\n".join(lines)


# Global unified team leader agent instance
team_leader_consumer = UnifiedTeamLeaderAgent()
