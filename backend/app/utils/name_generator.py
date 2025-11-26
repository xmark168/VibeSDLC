"""Human-like name generator for agents."""


def get_display_name(human_name: str, role_type: str) -> str:
    """Get display name with role suffix.

    Args:
        human_name: Agent's human name (from persona template)
        role_type: Agent role type

    Returns:
        Display name like "Sarah (Business Analyst)"
    """
    role_display = {
        "team_leader": "Team Leader",
        "business_analyst": "Business Analyst",
        "developer": "Developer",
        "tester": "Tester",
    }
    role_label = role_display.get(role_type, role_type.replace("_", " ").title())
    return f"{human_name} ({role_label})"
