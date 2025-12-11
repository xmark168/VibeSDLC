"""Script to add a story via API."""
import requests
import json

# Configuration
API_BASE = "http://localhost:8000/api/v1"
# Replace with your actual token
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN_HERE"

# Story data
story_data = {
    "project_id": "YOUR_PROJECT_ID_HERE",  # Replace with actual project UUID
    "story_code": "EPIC-001-US-001",
    "title": "As a visitor, I want to see featured books and promotions on the homepage so that I can quickly discover interesting books and special offers",
    "description": """Create an engaging homepage that displays featured books, current promotions, and bestsellers in an attractive layout. The homepage should serve as the main entry point for users to discover books and navigate to different sections of the bookstore.""",
    "requirements": [
        "Display a hero banner section with rotating promotional content and featured books",
        "Show a curated list of featured books with cover images, titles, authors, and prices",
        "Display current promotions and special offers in a dedicated section",
        "Include a bestsellers section showing top-selling books",
        "Implement responsive design that works on desktop, tablet, and mobile devices",
        "Add quick navigation links to main categories and sections",
        "Display book ratings and review counts for featured books",
        "Implement lazy loading for images to optimize page performance"
    ],
    "acceptance_criteria": [
        "Given I am a visitor, When I land on the homepage, Then I should see a hero banner with at least one featured promotion",
        "Given I am on the homepage, When the page loads, Then I should see at least 8-12 featured books with cover images, titles, authors, and prices",
        "Given I am viewing the homepage, When I scroll down, Then I should see sections for promotions, featured books, and bestsellers clearly separated",
        "Given I am on a mobile device, When I access the homepage, Then all content should be responsive and properly formatted for my screen size",
        "Given I am on the homepage, When I click on a featured book, Then I should be navigated to the book detail page",
        "Given the homepage has loaded, When I check the page load time, Then it should load within 3 seconds on a standard connection"
    ],
    "story_type": "UserStory",
    "priority": 1,
    "story_point": 8,
    "tags": ["homepage", "featured", "promotions", "frontend"],
    "labels": ["ui", "performance"]
}


def create_story():
    """Create story via API."""
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_BASE}/stories/",
        headers=headers,
        json=story_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Story created successfully!")
        print(f"  ID: {result['id']}")
        print(f"  Code: {result.get('story_code', 'N/A')}")
        print(f"  Title: {result['title'][:50]}...")
        return result
    else:
        print(f"✗ Failed to create story: {response.status_code}")
        print(f"  Error: {response.text}")
        return None


if __name__ == "__main__":
    import sys
    
    # Check if token and project_id are set
    if ACCESS_TOKEN == "YOUR_ACCESS_TOKEN_HERE":
        print("Please set ACCESS_TOKEN in the script")
        print("You can get it from localStorage after logging in:")
        print("  localStorage.getItem('access_token')")
        sys.exit(1)
    
    if story_data["project_id"] == "YOUR_PROJECT_ID_HERE":
        print("Please set project_id in the script")
        print("You can get it from the URL: /workspace/{project_id}")
        sys.exit(1)
    
    create_story()
