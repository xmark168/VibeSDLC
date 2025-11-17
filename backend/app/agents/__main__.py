"""
Agent System Entry Point

Run with: python -m app.agents
"""

import asyncio
import logging
import sys

from app.agents.team import AgentTeam
from app.agents.implementations import (
    TeamLeaderAgent,
    BusinessAnalystAgent,
    DeveloperAgent,
    TesterAgent,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for agent system."""
    logger.info("=" * 80)
    logger.info("Starting VibeSDLC Agent Team")
    logger.info("=" * 80)

    # Create team
    team = AgentTeam()

    # Hire all agents
    logger.info("Hiring agents...")
    team.hire([
        TeamLeaderAgent(),
        BusinessAnalystAgent(),
        DeveloperAgent(),
        TesterAgent(),
    ])

    logger.info("All agents hired and ready!")
    logger.info("=" * 80)

    # Example: Start with initial message
    # Uncomment to test:
    # await team.start("Build a user authentication system", n_round=10)

    # Or run interactively
    logger.info("Team is ready. Waiting for messages...")
    logger.info("(In production, this would listen to API/Kafka/etc.)")
    logger.info("=" * 80)

    # Keep running (in production, would listen to message sources)
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nAgent system stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
