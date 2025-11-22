"""Human-like name generator for agents."""

import random
from typing import Optional

# Names by role type - natural first names
ROLE_NAMES = {
    "team_leader": [
        "James", "William", "David", "Robert", "Richard",
        "Charles", "Thomas", "Daniel", "Matthew", "Anthony",
        "Victoria", "Elizabeth", "Catherine", "Margaret", "Patricia",
    ],
    "business_analyst": [
        "Sarah", "Emma", "Olivia", "Sophia", "Isabella",
        "Emily", "Grace", "Charlotte", "Amelia", "Hannah",
        "Nathan", "Ethan", "Lucas", "Mason", "Logan",
    ],
    "developer": [
        "Mike", "Alex", "Jordan", "Sam", "Chris",
        "Taylor", "Morgan", "Casey", "Jamie", "Riley",
        "Max", "Leo", "Jake", "Ryan", "Kyle",
    ],
    "tester": [
        "Luna", "Nova", "Iris", "Jade", "Ruby",
        "Violet", "Hazel", "Ivy", "Willow", "Aurora",
        "Felix", "Oscar", "Miles", "Hugo", "Finn",
    ],
}

# Fallback names for any role
DEFAULT_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Edward",
    "Fiona", "George", "Hannah", "Isaac", "Julia",
    "Kevin", "Laura", "Michael", "Nina", "Oliver",
]


def generate_agent_name(
    role_type: str,
    existing_names: Optional[list[str]] = None,
) -> str:
    """Generate a unique human-like name for an agent.

    Args:
        role_type: Agent role type (team_leader, business_analyst, developer, tester)
        existing_names: List of names already in use (to avoid duplicates)

    Returns:
        A unique human first name
    """
    existing_names = existing_names or []

    # Get role-specific names or fallback to default
    name_pool = ROLE_NAMES.get(role_type, DEFAULT_NAMES)

    # Filter out already used names
    available_names = [name for name in name_pool if name not in existing_names]

    # If all names are used, add a number suffix
    if not available_names:
        base_name = random.choice(name_pool)
        suffix = 2
        new_name = f"{base_name} {suffix}"
        while new_name in existing_names:
            suffix += 1
            new_name = f"{base_name} {suffix}"
        return new_name

    return random.choice(available_names)


def get_display_name(human_name: str, role_type: str) -> str:
    """Get display name with role suffix.

    Args:
        human_name: Agent's human name
        role_type: Agent role type

    Returns:
        Display name like "Mike (Developer)"
    """
    role_display = {
        "team_leader": "Team Leader",
        "business_analyst": "Business Analyst",
        "developer": "Developer",
        "tester": "Tester",
    }
    role_label = role_display.get(role_type, role_type.replace("_", " ").title())
    return f"{human_name} ({role_label})"
