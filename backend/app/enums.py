"""
Enums for VibeSDLC application
"""
import enum


class StoryStatus(str, enum.Enum):
    """Story status enum"""
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    TESTING = "TESTING"
    DONE = "DONE"
    BLOCKED = "BLOCKED"
    ARCHIVED = "ARCHIVED"


class StoryType(str, enum.Enum):
    """Story type enum"""
    USER_STORY = "USER_STORY"
    ENABLER_STORY = "ENABLER_STORY"


class StoryPriority(str, enum.Enum):
    """Story priority enum"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AgentType(str, enum.Enum):
    """Agent type enum"""
    FLOW_MANAGER = "FLOW_MANAGER"
    BUSINESS_ANALYST = "BUSINESS_ANALYST"
    DEVELOPER = "DEVELOPER"
    TESTER = "TESTER"
