from sqlmodel import Session
from app.core.db import engine
from app.models import Story
from uuid import UUID

story_ids = [
    '812c51b2-7b3e-4b5e-8905-9f8b4f7bd008',
    '36bacca4-b6d0-4df7-a2cc-8748d022a307',
]

with Session(engine) as session:
    for sid in story_ids:
        try:
            story_id = UUID(sid)
            story = session.get(Story, story_id)
            
            if story:
                print(f"Story {sid[:8]}: {story.title}")
                print(f"  Status: {story.status}")
            else:
                print(f"Story {sid[:8]}: NOT FOUND")
        except Exception as e:
            print(f"Error: {e}")
        print()
