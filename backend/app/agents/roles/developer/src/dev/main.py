#!/usr/bin/env python
import re
import sys
import warnings

from dev.crew import Dev

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information


def extract_user_stories(epic_text):
    """
    Extract user stories from the epic text by parsing the structure.
    Returns a list of tuples containing (story_number, user_story_text)
    """
    # Regular expression pattern to match user stories
    # Pattern matches: 'N.M.' followed by user story text and its acceptance criteria
    pattern = r'(\d+\.\d+)\.\s*(.*?)(?=\n\s*\d+\.\d+\.|\n\s*###|$)'

    matches = re.findall(pattern, epic_text, re.DOTALL)

    user_stories = []
    for match in matches:
        story_number = match[0]
        story_content = match[1].strip()

        # Extract just the user story part before the Description and Acceptance Criteria
        story_parts = re.split(r'\*\*Description:\*\*|\*\*Acceptance Criteria:\*\*', story_content, 1)
        story_text = story_parts[0].strip()

        user_stories.append((story_number, story_text))

    return user_stories


def run():
    """
    Run the crew with a list of user stories for a single project.
    """
    # --- Configuration for the single project ---
    # NOTE: The project_id should be a valid Python identifier (e.g., 'my_project')
    project_id = "demo"
    # The path to the project's codebase
    project_path = r'D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\dev\demo'

    # List of user stories to be implemented in this run
    user_stories = [
        '''
        As a learner, I want to log into my account 
        so that I can access personalized learning content and track my progress.

        *Description:* 
        Users can log into the platform using their registered email and password 
        (or third-party login options if available). The system validates credentials 
        and grants access to the dashboard upon successful authentication.

        *Acceptance Criteria:*
        - Given I am on the Login Page, When I enter a valid email and password and click “Login”, Then I am successfully logged into my account and redirected to my Dashboard.
        - Given I enter an incorrect email or password, When I click “Login”, Then I see an appropriate error message telling me the credentials are invalid.
        - Given I have forgotten my password, When I click the “Forgot Password” link, Then I am redirected to the password recovery flow.
        - Given the platform supports third-party login (e.g., Google Login), When I click the social login button, Then I can authenticate using my social account and be redirected to my Dashboard.
        - Given I am already logged in, When I revisit the Login Page, Then I should be redirected to my Dashboard automatically (unless I log out).
        '''
    ]


    # --- End Configuration ---

    print(f"## Initializing Project: {project_id} ##")
    print("=" * 70)

    # Consolidate all user stories into a single string for the planning agent
    user_stories_list = "\n---\n".join(user_stories)

    # Prepare the inputs for the crew
    inputs = {
        'user_stories_list': user_stories_list,
        'working_dir': project_path
    }

    print(f"\n## Processing {len(user_stories)} user stories for project '{project_id}'... ##")
    print("=" * 70)

    # Create a single crew instance for the project and kick it off once.
    # The __init__ method of Dev will handle project registration and indexing.
    dev_crew = Dev(project_id=project_id, root_dir=project_path).crew()
    dev_crew.kickoff(inputs=inputs)

    print("\n\n## All projects and user stories have been processed. ##")
    print("=" * 70)


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        Dev().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "task_description": """
        Write a function to check if a number is prime.
        Test with numbers: 17, 20, 97
        """,
        "input_data": "test_numbers = [17, 20, 97]",
    }
    try:
        Dev().crew().test(
            n_iterations=int(sys.argv[1]),
            openai_model_name=sys.argv[2],
            inputs=inputs
        )
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json

    if len(sys.argv) < 2:
        raise Exception(
            "No trigger payload provided. Please provide JSON payload as argument."
        )

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": "",
        "current_year": "",
    }

    try:
        result = Dev().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")


if __name__ == "__main__":
    run()
