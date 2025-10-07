from typing import Dict, List, Literal, TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage,AIMessage


# class EvalResult(BaseModel):
#     gaps: List[str] = Field(default_factory=list)
#     score: float = 0.0
#     confidence: float = 0.0
#     status: Literal["working", "done", "invalid"] = "working"
#     message: str = ""


# class BriefState(TypedDict, total=False):
#     # I/O
#     last_user_input: str
#     user_messages: List[str]
#     ai_messages: List[str]

#     # working memory
#     brief: Dict
#     eval: EvalResult
#     iteration_count: int
#     max_iterations: int
#     retry_count: int
#     awaiting_user: bool
#     finalized: bool
#     force_preview: bool
#     mode: str

class EvaluateOutput(BaseModel):
    gaps: list[str] = Field(description="Danh sách các thông tin còn thiếu")
    score: float = Field(description="Điểm đánh giá độ đầy đủ", ge=0.0, le=1.0)
    status: str = Field(description="Trạng thái: incomplete hoặc done")
    confidence: float = Field(description="Độ tin cậy đánh giá", ge=0.0, le=1.0)


class State(BaseModel):
    """Trạng thái cho quy trình làm việc của gatherer agent."""

    messages: list[BaseMessage] = Field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 5
    retry_count: int = 0
    gaps: list[str] = Field(default_factory=list)
    score: float = 0.0
    phase: str = "initial"
    confidence: float = 0.0
    brief: dict
    incomplete_flag: bool = False
    questions: str = ""
    user_choice: Literal["approve", "edit", "regenerate", ""] = ""
    edit_changes: str = ""