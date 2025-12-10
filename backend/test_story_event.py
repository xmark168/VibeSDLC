"""
Test script to verify Story Todo -> InProgress Kafka flow.

This script:
1. Creates a test story in the database
2. Publishes a story.status.changed event to Kafka
3. The StoryEventRouter should route it to Developer agent

Run: uv run python test_story_event.py
"""

import asyncio
import logging
from uuid import uuid4, UUID

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Will be loaded from DB
PROJECT_ID = None
USER_ID = None


def load_project_and_user():
    """Load first available project and user from DB."""
    global PROJECT_ID, USER_ID
    from sqlmodel import Session, select
    from app.core.db import engine
    from app.models import Project, User
    
    with Session(engine) as session:
        project = session.exec(select(Project).limit(1)).first()
        if not project:
            raise ValueError("No project found! Create a project first.")
        PROJECT_ID = project.id
        
        user = session.exec(select(User).limit(1)).first()
        if user:
            USER_ID = user.id
        else:
            USER_ID = UUID("00000000-0000-0000-0000-000000000000")
        
        print(f"Using project: {project.name} ({PROJECT_ID})")


async def create_test_story():
    """Create a test story in the database."""
    from sqlmodel import Session
    from app.core.db import engine
    from app.models import Story, StoryStatus
    
    story_id = uuid4()
    
    with Session(engine) as session:
        story = Story(
            id=story_id,
            project_id=PROJECT_ID,
            story_code=f"TEST-{uuid4().hex[:6].upper()}",
            title="As a first-time visitor, I want to see featured books and categories on the homepage",
            description="""
The homepage serves as the primary entry point for all visitors, showcasing the bookstore's offerings through curated collections and categories. This story establishes the foundation for user engagement by presenting featured books, bestsellers, and category navigation that helps visitors understand what the store offers and guides them toward their interests.

### Requirements
- Display hero section with 3-5 featured books rotating every 5 seconds
- Show 'Bestsellers' section with top 10 books based on sales data
- Display 'New Arrivals' section with latest 8 books added to catalog
- Present main book categories (Fiction, Non-Fiction, Children, Academic, etc.) with representative cover images
- Include promotional banner area for special offers or campaigns
- Show 'Recommended for You' section with 6 books (random for non-logged users, personalized for logged users)
- Ensure all book cards display: cover image, title, author, price, and rating
- Implement lazy loading for images to optimize page load time under 2 seconds
            """.strip(),
            status=StoryStatus.TODO,
            priority=1,
            acceptance_criteria=[
                "Given I am a visitor on the homepage, When the page loads, Then I see hero section with featured books, bestsellers section, new arrivals section, and category navigation within 2 seconds",
                "Given I am viewing the homepage, When I see a book card, Then it displays cover image, title, author name, current price, and average rating (if available)",
                "Given I am on the homepage, When I click on a book card, Then I am navigated to that book's detail page",
                "Given I am on the homepage, When I click on a category tile, Then I am navigated to the category page showing all books in that category",
                "Given the homepage has loaded, When I wait 5 seconds, Then the hero section automatically transitions to the next featured book",
                "Given I am a non-logged user, When I view 'Recommended for You' section, Then I see 6 randomly selected popular books from various categories"
            ],
        )
        session.add(story)
        session.commit()
        session.refresh(story)
        
        logger.info(f"Created story: {story.id} - {story.title}")
        return story


async def publish_status_changed_event(story_id: UUID):
    """Publish story.status.changed event to Kafka."""
    from app.kafka import get_kafka_producer, KafkaTopics, StoryEvent
    
    event = StoryEvent(
        event_type="story.status.changed",
        project_id=str(PROJECT_ID),
        user_id=str(USER_ID),
        story_id=story_id,
        old_status="Todo",
        new_status="InProgress",
        changed_by=str(USER_ID),
        transition_reason="Test: Moving to InProgress",
    )
    
    producer = await get_kafka_producer()
    success = await producer.publish(
        topic=KafkaTopics.STORY_EVENTS,
        event=event
    )
    
    if success:
        logger.info(f"Published story.status.changed event for story {story_id}")
    else:
        logger.error("Failed to publish event!")
    
    # Flush to ensure delivery
    await producer.flush()
    
    return success


async def main():
    print("\n" + "="*60)
    print("TEST: Story Todo -> InProgress Kafka Flow")
    print("="*60 + "\n")
    
    # Load project from DB
    load_project_and_user()
    
    # Step 1: Create story
    print("[1/2] Creating test story...")
    story = await create_test_story()
    print(f"      Story ID: {story.id}")
    print(f"      Title: {story.title}")
    
    # Step 2: Publish event
    print("\n[2/2] Publishing story.status.changed event...")
    await publish_status_changed_event(story.id)
    
    print("\n" + "="*60)
    print("EVENT PUBLISHED!")
    print("="*60)
    print("""
Check the logs for:
1. [STORY_EVENT_ROUTER] - Should receive the event
2. [Developer] - Should receive IMPLEMENT_STORY task
3. [Developer] Loading story from DB: <story_id>
4. [setup_workspace] Creating worktree at: <path>_<story_id>

If agents are not running, start them with:
  uv run python -m app.main
""")


if __name__ == "__main__":
    asyncio.run(main())
