
from deepagents.types import SubAgent
from ....templates.prompts.developer.planner import INITIALIZE_PROMPT

plan_generator_subagent: SubAgent = {
    "name": "planGenerator",
    "description": (
        "Expert software architect that generates detailed implementation plans. "
        "Use this after gathering sufficient context about the codebase. "
        "It will analyze all gathered information and create a step-by-step plan."
    ),
    "prompt": INITIALIZE_PROMPT,
    "tools": []
}

# Export subagents
__all__ = ["plan_generator_subagent"]
