"""
Integration test example: API ↔ Database Integration
Using the testing plan from TESTING_PLAN.md
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from uuid import uuid4

from app.main import app
from app.models import Story, Project, User
from app.core.db import engine


@pytest.fixture
def test_client():
    """Create test client with clean database state."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def db_session():
    """Create database session for testing."""
    with Session(engine) as session:
        # Clean up any test data before test
        session.exec(select(Story).where(Story.title.like('%Test%')))
        session.commit()
        yield session
        # Clean up after test
        session.exec(select(Story).where(Story.title.like('%Test%')))
        session.commit()


def test_create_story_integration(test_client: TestClient, db_session: Session):
    """
    Integration test example: API ↔ Database
    Following the test case described in TESTING_PLAN.md section 7.1
    """
    # Given: Valid project exists in database
    project_id = str(uuid4())
    project = Project(
        id=project_id,
        name="Test Project",
        description="Integration test project"
    )
    db_session.add(project)
    db_session.commit()
    
    # Test data for story creation
    story_data = {
        "title": "Integration Test Story",
        "description": "Testing API to Database integration",
        "project_id": project_id,
        "status": "todo"
    }
    
    # When: Send POST request to create story via API
    response = test_client.post(
        "/stories/", 
        json=story_data,
        headers={"Content-Type": "application/json"}
    )
    
    # Then: Verify API response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}, response: {response.text}"
    
    # Then: Verify data was stored correctly in database
    created_story = db_session.exec(
        select(Story).where(Story.title == "Integration Test Story")
    ).first()
    
    assert created_story is not None, "Story was not saved to database"
    assert created_story.description == "Testing API to Database integration"
    assert str(created_story.project_id) == project_id
    assert created_story.status.value == "todo"
    
    print(f"✓ Integration test passed: Story {created_story.id} created successfully")


def test_get_story_integration(test_client: TestClient, db_session: Session):
    """
    Integration test: API GET endpoint ↔ Database retrieval
    """
    # Given: Story exists in database
    project_id = str(uuid4())
    project = Project(
        id=project_id,
        name="Test Project",
        description="Integration test project"
    )
    db_session.add(project)
    
    story = Story(
        title="Existing Test Story",
        description="This story already exists in DB",
        project_id=project_id,
        status="todo"
    )
    db_session.add(story)
    db_session.commit()
    
    # When: Get the story via API
    response = test_client.get(f"/stories/{story.id}")
    
    # Then: Verify response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["title"] == "Existing Test Story"
    assert response_data["description"] == "This story already exists in DB"
    assert response_data["status"] == "todo"
    
    print(f"✓ Get story integration test passed: Retrieved story {response_data['id']}")


def test_update_story_integration(test_client: TestClient, db_session: Session):
    """
    Integration test: API PUT endpoint ↔ Database update
    """
    # Given: Story exists in database with initial status
    project_id = str(uuid4())
    project = Project(id=project_id, name="Test Project", description="Update test project")
    db_session.add(project)
    
    story = Story(
        title="Update Test Story",
        description="Original description",
        project_id=project_id,
        status="todo"
    )
    db_session.add(story)
    db_session.commit()
    
    # When: Update the story via API
    update_data = {
        "title": "Updated Test Story",
        "description": "Updated description",
        "status": "in_progress"
    }
    
    response = test_client.put(f"/stories/{story.id}", json=update_data)
    
    # Then: Verify API response
    assert response.status_code == 200
    
    # Then: Verify database was updated
    updated_story = db_session.get(Story, story.id)
    assert updated_story.title == "Updated Test Story"
    assert updated_story.description == "Updated description"
    assert updated_story.status.value == "in_progress"
    
    print(f"✓ Update story integration test passed: Story {story.id} updated successfully")


if __name__ == "__main__":
    # Run the tests directly if needed
    pytest.main([__file__, "-v"])