"""
Direct test for Developer V2 story processing.
Tests _load_story_from_db and _handle_story_processing without Kafka.

Run: uv run python test_dev_story_direct.py
"""

import asyncio
import logging
from uuid import uuid4, UUID

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ID = UUID("e6f013c7-abfc-4db7-990c-9f63b2fc71e5")


async def create_test_story():
    """Create a test story in DB."""
    from sqlmodel import Session
    from app.core.db import engine
    from app.models import Story, StoryStatus
    
    story_id = uuid4()
    
    with Session(engine) as session:
        story = Story(
            id=story_id,
            project_id=PROJECT_ID,
            story_code="TEST-001",
            title="[Direct Test] Homepage Featured Books",
            description="""
The homepage serves as the primary entry point for all visitors.

### Requirements
- Display hero section with 3-5 featured books rotating every 5 seconds
- Show 'Bestsellers' section with top 10 books based on sales data
- Display 'New Arrivals' section with latest 8 books
- Present main book categories with cover images
- Implement lazy loading for images
            """.strip(),
            status=StoryStatus.TODO,
            priority=1,
            acceptance_criteria=[
                "Hero section displays featured books",
                "Bestsellers section shows top 10 books",
                "New Arrivals shows latest 8 books",
                "Category tiles are clickable",
                "Images use lazy loading",
            ],
        )
        session.add(story)
        session.commit()
        session.refresh(story)
        
        logger.info(f"Created story: {story.id}")
        return story


async def test_load_story_from_db(story_id: UUID):
    """Test _load_story_from_db method directly."""
    from sqlmodel import Session
    from app.core.db import engine
    from app.models import Agent
    from app.agents.developer_v2 import DeveloperV2
    
    # Get developer agent from DB
    with Session(engine) as session:
        agent = session.query(Agent).filter(
            Agent.project_id == PROJECT_ID,
            Agent.role_type == "developer"
        ).first()
        
        if not agent:
            logger.error("No developer agent found!")
            return None
        
        logger.info(f"Found developer: {agent.human_name} ({agent.id})")
    
    # Create DeveloperV2 instance
    dev = DeveloperV2(agent)
    
    # Test _load_story_from_db
    logger.info(f"\n{'='*60}")
    logger.info("Testing _load_story_from_db")
    logger.info(f"{'='*60}")
    
    story_data = await dev._load_story_from_db(str(story_id))
    
    logger.info(f"\nLoaded story data:")
    logger.info(f"  story_id: {story_data['story_id']}")
    logger.info(f"  title: {story_data['title']}")
    logger.info(f"  content length: {len(story_data['content'])} chars")
    logger.info(f"  acceptance_criteria: {len(story_data['acceptance_criteria'])} items")
    
    if story_data['acceptance_criteria']:
        logger.info(f"\nAcceptance Criteria:")
        for i, ac in enumerate(story_data['acceptance_criteria'], 1):
            logger.info(f"  {i}. {ac[:60]}...")
    
    return story_data


async def test_handle_story_processing(story_id: UUID):
    """Test full _handle_story_processing with mocked TaskContext."""
    from sqlmodel import Session
    from app.core.db import engine
    from app.models import Agent
    from app.agents.developer_v2 import DeveloperV2
    from app.agents.core.base_agent import TaskContext
    from app.kafka.event_schemas import AgentTaskType
    
    # Get developer agent
    with Session(engine) as session:
        agent = session.query(Agent).filter(
            Agent.project_id == PROJECT_ID,
            Agent.role_type == "developer"
        ).first()
        
        if not agent:
            logger.error("No developer agent found!")
            return
    
    # Create DeveloperV2 instance
    dev = DeveloperV2(agent)
    
    # Create TaskContext simulating router dispatch
    task = TaskContext(
        task_id=uuid4(),
        task_type=AgentTaskType.IMPLEMENT_STORY,
        priority="high",
        routing_reason="story_status_changed_to_in_progress",
        project_id=PROJECT_ID,
        content="Story moved to In Progress",
        context={
            "event_type": "story.status.changed",
            "story_id": str(story_id),
            "old_status": "Todo",
            "new_status": "InProgress",
        }
    )
    
    logger.info(f"\n{'='*60}")
    logger.info("Testing _handle_story_processing")
    logger.info(f"{'='*60}")
    logger.info(f"TaskContext.context = {task.context}")
    
    # This will load story from DB and process it
    # Note: Will fail if LangGraph isn't fully set up, but shows the flow
    try:
        result = await dev._handle_story_processing(task)
        logger.info(f"\nResult: success={result.success}")
        if result.error_message:
            logger.error(f"Error: {result.error_message}")
    except Exception as e:
        logger.error(f"Processing error (expected if graph not ready): {e}")


async def main():
    print("\n" + "="*60)
    print("DIRECT TEST: Developer V2 Story Processing")
    print("="*60 + "\n")
    
    # Create test story
    story = await create_test_story()
    
    # Test 1: Load story from DB
    story_data = await test_load_story_from_db(story.id)
    
    if story_data:
        print("\n" + "-"*60)
        print("TEST PASSED: Story loaded successfully from DB")
        print(f"  - Title: {story_data['title'][:50]}...")
        print(f"  - Description: {len(story_data['content'])} chars")
        print(f"  - Acceptance Criteria: {len(story_data['acceptance_criteria'])} items")
        print("-"*60)
    
    # Test 2: Full story processing (optional - requires full setup)
    # Uncomment to test full flow:
    # await test_handle_story_processing(story.id)
    
    # Cleanup
    from sqlmodel import Session
    from app.core.db import engine
    from app.models import Story
    
    with Session(engine) as session:
        session.delete(session.get(Story, story.id))
        session.commit()
        logger.info(f"\nCleaned up test story: {story.id}")


if __name__ == "__main__":
    asyncio.run(main())
