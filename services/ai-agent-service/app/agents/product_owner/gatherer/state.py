from typing import Dict, List, Literal, TypedDict
from pydantic import BaseModel, Field


class EvalResult(BaseModel):
    gaps: List[str] = Field(default_factory=list)
    score: float = 0.0
    confidence: float = 0.0
    status: Literal["working", "done", "invalid"] = "working"
    message: str = ""


class BriefState(TypedDict, total=False):
    # I/O
    last_user_input: str
    user_messages: List[str]
    ai_messages: List[str]

    # working memory
    brief: Dict
    eval: EvalResult
    iteration_count: int
    max_iterations: int
    retry_count: int
    awaiting_user: bool
    finalized: bool
    force_preview: bool
    mode: str


