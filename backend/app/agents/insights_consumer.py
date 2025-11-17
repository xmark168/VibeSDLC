"""
Insights Agent Consumer (Team Leader)

Analyzes project metrics and provides actionable insights
"""

import logging
import uuid
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta

from sqlmodel import Session, select, func

from app.crews.events.kafka_consumer import create_consumer
from app.crews.events.kafka_producer import get_kafka_producer
from app.crews.events.event_schemas import KafkaTopics, AgentResponseEvent
from app.core.db import engine
from app.models import Story, StoryStatus

logger = logging.getLogger(__name__)


class InsightsAgentConsumer:
    """
    Team Leader agent for project insights and analytics

    Capabilities:
    - Cycle time analysis
    - Identify blocked stories
    - Workload distribution analysis
    - Bottleneck detection
    - Team performance recommendations
    """

    def __init__(self):
        self.consumer = None
        self.producer = None
        self.running = False

    async def start(self):
        """Start the insights agent consumer"""
        try:
            logger.info("Starting Insights Agent (Team Leader) Consumer...")

            # Get Kafka producer
            self.producer = await get_kafka_producer()

            # Create consumer
            self.consumer = await create_consumer(
                consumer_id="insights_agent_leader",
                topics=[KafkaTopics.AGENT_TASKS_LEADER],
                group_id="leader_agents_group",
                auto_offset_reset="latest"
            )

            # Register task handler
            self.consumer.register_handler("agent.task", self.handle_task)

            self.running = True
            logger.info("Insights Agent Consumer started successfully")

            # Start consuming
            await self.consumer.consume()

        except Exception as e:
            logger.error(f"Error starting Insights Agent Consumer: {e}")
            raise

    async def stop(self):
        """Stop the consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
        logger.info("Insights Agent Consumer stopped")

    async def handle_task(self, event_data: Dict[str, Any]):
        """
        Handle incoming insights/analytics tasks

        Event structure:
        {
            "task_id": UUID,
            "agent_type": "leader",
            "project_id": UUID,
            "user_message_id": UUID,
            "task_description": str,
            "context": dict
        }
        """
        try:
            task_id = UUID(event_data["task_id"])
            project_id = UUID(event_data["project_id"])
            user_message_id = UUID(event_data["user_message_id"])
            task_description = event_data["task_description"]

            logger.info(f"Processing insights task {task_id}: {task_description[:50]}...")

            # Generate insights
            response_content, structured_data = await self.generate_insights(
                project_id,
                task_description
            )

            # Publish response event
            response_id = uuid.uuid4()
            response_event = AgentResponseEvent(
                response_id=response_id,
                task_id=task_id,
                agent_type="leader",
                project_id=project_id,
                content=response_content,
                structured_data=structured_data,
                metadata={
                    "user_message_id": str(user_message_id),
                    "insights_type": "project_analytics",
                },
                timestamp=datetime.utcnow()
            )

            await self.producer.publish_event(
                topic=KafkaTopics.AGENT_RESPONSES,
                event=response_event.model_dump(),
                key=str(project_id)
            )

            logger.info(f"Insights task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Error handling insights task: {e}")

    async def generate_insights(
        self,
        project_id: UUID,
        task_description: str
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate project insights based on data analysis

        Returns: (response_content, structured_data)
        """
        try:
            with Session(engine) as session:
                # Fetch project stories
                statement = select(Story).where(Story.project_id == project_id)
                stories = session.exec(statement).all()

                if not stories:
                    return "No stories found in this project yet. Create some stories to see insights!", {}

                # Calculate metrics
                insights_data = {
                    "total_stories": len(stories),
                    "status_distribution": self.calculate_status_distribution(stories),
                    "blocked_stories": self.find_blocked_stories(stories),
                    "cycle_time_analysis": self.analyze_cycle_time(stories),
                    "workload_distribution": self.analyze_workload(stories),
                    "recommendations": self.generate_recommendations(stories),
                }

                # Format response
                response_content = self.format_insights_response(insights_data)

                return response_content, insights_data

        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return f"Error analyzing project metrics: {str(e)}", {}

    def calculate_status_distribution(self, stories: List[Story]) -> Dict[str, int]:
        """Calculate distribution of stories across statuses"""
        distribution = {}
        for story in stories:
            status = story.status.value if hasattr(story.status, 'value') else str(story.status)
            distribution[status] = distribution.get(status, 0) + 1
        return distribution

    def find_blocked_stories(self, stories: List[Story]) -> List[Dict[str, Any]]:
        """Find stories that are blocked"""
        blocked = []
        for story in stories:
            # Check if story has blockers
            if hasattr(story, 'blockers') and story.blockers:
                blocked.append({
                    "id": str(story.id),
                    "title": story.title,
                    "status": story.status.value if hasattr(story.status, 'value') else str(story.status),
                    "blocker_count": len(story.blockers),
                })
        return blocked

    def analyze_cycle_time(self, stories: List[Story]) -> Dict[str, Any]:
        """Analyze cycle time for completed stories"""
        completed_stories = [
            s for s in stories
            if hasattr(s, 'completed_at') and s.completed_at
        ]

        if not completed_stories:
            return {
                "average_days": 0,
                "min_days": 0,
                "max_days": 0,
                "count": 0,
            }

        cycle_times = []
        for story in completed_stories:
            if story.created_at and story.completed_at:
                delta = story.completed_at - story.created_at
                cycle_times.append(delta.total_seconds() / 86400)  # Convert to days

        if not cycle_times:
            return {"average_days": 0, "min_days": 0, "max_days": 0, "count": 0}

        return {
            "average_days": round(sum(cycle_times) / len(cycle_times), 1),
            "min_days": round(min(cycle_times), 1),
            "max_days": round(max(cycle_times), 1),
            "count": len(cycle_times),
        }

    def analyze_workload(self, stories: List[Story]) -> Dict[str, Any]:
        """Analyze workload distribution by assignee"""
        workload = {}

        for story in stories:
            if story.assignee_id:
                assignee_id = str(story.assignee_id)
                if assignee_id not in workload:
                    workload[assignee_id] = {
                        "total": 0,
                        "by_status": {},
                    }

                workload[assignee_id]["total"] += 1

                status = story.status.value if hasattr(story.status, 'value') else str(story.status)
                workload[assignee_id]["by_status"][status] = \
                    workload[assignee_id]["by_status"].get(status, 0) + 1

        return workload

    def generate_recommendations(self, stories: List[Story]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Check for blocked stories
        blocked_count = sum(1 for s in stories if hasattr(s, 'blockers') and s.blockers)
        if blocked_count > 0:
            recommendations.append(
                f"⚠️ {blocked_count} stories are blocked. Review blockers and unblock high-priority items."
            )

        # Check WIP
        in_progress = sum(
            1 for s in stories
            if s.status == StoryStatus.InProgress
        )
        if in_progress > 5:
            recommendations.append(
                f"📊 High WIP ({in_progress} stories in progress). Consider focusing on completing existing work."
            )

        # Check for stories without assignees
        unassigned = sum(1 for s in stories if not s.assignee_id)
        if unassigned > 3:
            recommendations.append(
                f"👥 {unassigned} stories are unassigned. Assign stories to team members for better tracking."
            )

        # Check for old stories
        old_stories = [
            s for s in stories
            if s.created_at and (datetime.utcnow() - s.created_at).days > 30
            and s.status != StoryStatus.Done
        ]
        if old_stories:
            recommendations.append(
                f"⏰ {len(old_stories)} stories are older than 30 days. Review and prioritize or close them."
            )

        if not recommendations:
            recommendations.append("✅ Project health looks good! Keep up the great work.")

        return recommendations

    def format_insights_response(self, insights_data: Dict[str, Any]) -> str:
        """Format insights data into readable text"""
        lines = ["# Project Insights\n"]

        # Summary
        lines.append(f"## Summary")
        lines.append(f"Total Stories: **{insights_data['total_stories']}**\n")

        # Status distribution
        lines.append("## Status Distribution")
        for status, count in insights_data["status_distribution"].items():
            lines.append(f"- {status}: {count}")
        lines.append("")

        # Blocked stories
        if insights_data["blocked_stories"]:
            lines.append("## ⚠️ Blocked Stories")
            for story in insights_data["blocked_stories"]:
                lines.append(f"- **{story['title']}** ({story['blocker_count']} blockers)")
            lines.append("")

        # Cycle time
        cycle_time = insights_data["cycle_time_analysis"]
        if cycle_time["count"] > 0:
            lines.append("## ⏱️ Cycle Time Analysis")
            lines.append(f"- Average: {cycle_time['average_days']} days")
            lines.append(f"- Min: {cycle_time['min_days']} days")
            lines.append(f"- Max: {cycle_time['max_days']} days")
            lines.append(f"- Completed stories: {cycle_time['count']}")
            lines.append("")

        # Recommendations
        lines.append("## 💡 Recommendations")
        for rec in insights_data["recommendations"]:
            lines.append(f"- {rec}")

        return "\n".join(lines)


# Global instance
insights_agent_consumer = InsightsAgentConsumer()
