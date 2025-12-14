"""Developer V2 exceptions."""
from app.models.base import StoryAgentState


class StoryStoppedException(Exception):
    """Raised when story processing should stop."""
    def __init__(self, story_id: str, state: StoryAgentState, message: str = ""):
        self.story_id = story_id
        self.state = state
        self.message = message or f"Story {story_id} stopped: {state.value}"
        super().__init__(self.message)
