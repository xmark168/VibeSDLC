"""Agent Orchestrator Service.

Central service that manages all agent crews and their lifecycle.
This orchestrator:
1. Initializes all crew modules (Team Leader, BA, Developer, Tester)
2. Starts/stops Kafka consumers for each crew
3. Manages crew lifecycle
4. Integrates with FastAPI app startup/shutdown
"""

import asyncio
import logging
from typing import Dict, List, Optional

from app.agents.roles.team_leader import TeamLeaderCrew, TeamLeaderConsumer
from app.agents.roles.business_analyst import BusinessAnalystCrew, BusinessAnalystConsumer
from app.agents.roles.developer import DeveloperCrew, DeveloperConsumer
from app.agents.roles.tester import TesterCrew, TesterConsumer

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Central orchestrator for all agent crews.

    Manages:
    - Team Leader Crew (orchestrates task delegation)
    - Business Analyst Crew (requirements and PRD)
    - Developer Crew (code implementation)
    - Tester Crew (QA and testing)

    Flow:
    1. User message → Team Leader analyzes → Delegates to specialist
    2. Specialist crew receives routing event → Executes task → Publishes response
    3. WebSocket bridge forwards response to UI
    """

    def __init__(self):
        """Initialize the orchestrator with all crews."""
        self._running = False
        self._consumers: Dict[str, any] = {}
        self._tasks: List[asyncio.Task] = []

        # Initialize crews
        self.team_leader = TeamLeaderCrew()
        self.business_analyst = BusinessAnalystCrew()
        self.developer = DeveloperCrew()
        self.tester = TesterCrew()

        # Initialize consumers
        self._consumers = {
            "team_leader": TeamLeaderConsumer(group_id="team-leader-consumer"),
            "business_analyst": BusinessAnalystConsumer(group_id="business-analyst-consumer"),
            "developer": DeveloperConsumer(group_id="developer-consumer"),
            "tester": TesterConsumer(group_id="tester-consumer"),
        }

        logger.info("Agent Orchestrator initialized with 4 crews")

    async def start(self) -> None:
        """Start all crew consumers.

        This starts Kafka consumers that listen for events:
        - Team Leader: listens for UserMessageEvent
        - Specialists: listen for AgentRoutingEvent
        """
        if self._running:
            logger.warning("Agent Orchestrator already running")
            return

        logger.info("Starting Agent Orchestrator...")

        try:
            # Start all consumers in parallel
            start_tasks = [
                self._start_consumer("team_leader"),
                self._start_consumer("business_analyst"),
                self._start_consumer("developer"),
                self._start_consumer("tester"),
            ]

            await asyncio.gather(*start_tasks, return_exceptions=True)

            self._running = True
            logger.info("Agent Orchestrator started successfully - all crews listening for events")

        except Exception as e:
            logger.error(f"Failed to start Agent Orchestrator: {e}", exc_info=True)
            raise

    async def _start_consumer(self, crew_name: str) -> None:
        """Start a specific crew consumer.

        Args:
            crew_name: Name of the crew to start
        """
        try:
            consumer = self._consumers.get(crew_name)
            if consumer:
                # Start consumer in background task
                task = asyncio.create_task(consumer.start())
                self._tasks.append(task)
                logger.info(f"{crew_name} consumer started")
            else:
                logger.warning(f"Consumer not found for crew: {crew_name}")
        except Exception as e:
            logger.error(f"Failed to start {crew_name} consumer: {e}", exc_info=True)

    async def stop(self) -> None:
        """Stop all crew consumers."""
        if not self._running:
            return

        logger.info("Stopping Agent Orchestrator...")

        try:
            # Stop all consumers
            stop_tasks = [
                consumer.stop()
                for consumer in self._consumers.values()
            ]

            await asyncio.gather(*stop_tasks, return_exceptions=True)

            # Cancel background tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete
            await asyncio.gather(*self._tasks, return_exceptions=True)

            self._tasks.clear()
            self._running = False

            logger.info("Agent Orchestrator stopped")

        except Exception as e:
            logger.error(f"Error stopping Agent Orchestrator: {e}", exc_info=True)

    @property
    def is_running(self) -> bool:
        """Check if orchestrator is running."""
        return self._running

    def get_crew_status(self) -> Dict[str, Dict[str, any]]:
        """Get status of all crews.

        Returns:
            Dictionary with crew names and their status
        """
        return {
            "team_leader": {
                "crew": self.team_leader.crew_name,
                "consumer_running": self._consumers["team_leader"].is_running,
            },
            "business_analyst": {
                "crew": self.business_analyst.crew_name,
                "consumer_running": self._consumers["business_analyst"].is_running,
            },
            "developer": {
                "crew": self.developer.crew_name,
                "consumer_running": self._consumers["developer"].is_running,
            },
            "tester": {
                "crew": self.tester.crew_name,
                "consumer_running": self._consumers["tester"].is_running,
            },
            "orchestrator_running": self._running,
        }


# Global orchestrator instance
_orchestrator_instance: Optional[AgentOrchestrator] = None


async def get_orchestrator() -> AgentOrchestrator:
    """Get the global orchestrator instance.

    Returns:
        Initialized AgentOrchestrator singleton
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    return _orchestrator_instance


async def start_orchestrator() -> None:
    """Start the global orchestrator instance."""
    orchestrator = await get_orchestrator()
    await orchestrator.start()


async def stop_orchestrator() -> None:
    """Stop the global orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance:
        await _orchestrator_instance.stop()
        _orchestrator_instance = None
