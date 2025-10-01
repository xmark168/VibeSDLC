from typing import TypedDict, Annotated, Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.tools import Tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import operator
import json
import os

# --- Langfuse: tracing/observability ---
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

# ===== Langfuse callback (đọc key/host từ .env) =====
langfuse = Langfuse()
lf_handler = CallbackHandler(
    langfuse=langfuse,
    user_id=os.getenv("LF_USER_ID", "it@ckhub.vn"),
    session_id=os.getenv("LF_SESSION_ID", "gatherer-session"),
    tags=["gatherer", "react-agent"]
)

# ===== Cấu hình OpenAI-compatible =====
# Dùng model từ env (nếu provider của bạn yêu cầu tên khác 'gpt-4o')
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # đã được map từ API_KEY ở main.py
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # ví dụ: https://v98store.com/v1

# ============ State schema ============
class GathererState(TypedDict):
    input_data: Dict[str, Any]
    memory: Annotated[List[Dict[str, str]], operator.add]
    uncertainties: List[str]
    brief: Optional[str]
    status: str
    next_question: Optional[str]
    tool_results: Dict[str, Any]
    gaps: List[str]
    completeness_score: float

# ============ Prompts ============
EVALUATE_PROMPT = """
Bạn là một chuyên gia đánh giá tính hoàn chỉnh của thông tin sản phẩm.
Dựa trên template sau và memory chat, đánh giá completeness score từ 0-1.
Template: {template}
Memory: {memory}
Output JSON: {{"status": "hoàn tất/chưa hoàn tất/hỏi thêm", "completeness_score": number (0-1), "gaps": ["list of missing fields"]}}
"""

GENERATE_PROMPT = """
Tạo product brief dựa trên template và memory.
Template: {template}
Memory: {memory}
Output: JSON theo template.
"""

REFLECTION_PROMPT = """
Phản ánh và validate brief.
Brief: {brief}
Memory: {memory}
Output JSON: {{"validated_brief": updated brief JSON, "issues": ["list of issues"]}}
"""

NATURAL_QUESTION_PROMPT = """
Chuyển uncertainties thành câu hỏi tự nhiên.
Uncertainties: {uncertainties}
Output: Câu hỏi tự nhiên để hỏi user.
"""

# ============ Template brief ============
PRODUCT_BRIEF_TEMPLATE = {
    "ten_san_pham": {"required": True, "value": ""},
    "tong_quan": {"required": True, "value": ""},
    "muc_tieu": {"required": True, "value": ""},
    "doi_tuong_muc_tieu": {"required": True, "value": ""},
    "tinh_nang_chinh": {"required": True, "value": []},
    "tinh_nang_mo_rong": {"required": False, "value": []},
}

# ===== Helpers =====
def _safe_json_loads(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise

def _chat_llm(temp: float):
    """
    Khởi tạo ChatOpenAI trỏ thẳng tới OpenAI-compatible endpoint của bạn.
    Truyền api_key & base_url tường minh để không phụ thuộc env trong runtime.
    """
    return ChatOpenAI(
        model=MODEL_NAME,
        temperature=temp,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        callbacks=[lf_handler],
    )

# ===== Custom tools =====
def evaluate_completeness(state: GathererState) -> Dict[str, Any]:
    llm = _chat_llm(0.3)
    prompt = ChatPromptTemplate.from_messages([("system", EVALUATE_PROMPT)])
    chain = prompt | llm
    memory_str = json.dumps(state.get("memory", []), ensure_ascii=False)
    resp = chain.invoke(
        {
            "template": json.dumps(PRODUCT_BRIEF_TEMPLATE, ensure_ascii=False),
            "memory": memory_str,
        },
        config={"callbacks": [lf_handler]},
    )
    return _safe_json_loads(resp.content)

def naturalize_question(state: GathererState) -> str:
    llm = _chat_llm(0.5)
    prompt = ChatPromptTemplate.from_messages([("system", NATURAL_QUESTION_PROMPT)])
    chain = prompt | llm
    resp = chain.invoke(
        {"uncertainties": state.get("gaps", [])},
        config={"callbacks": [lf_handler]},
    )
    return resp.content.strip()

def generate_brief(state: GathererState) -> Dict[str, Any]:
    llm = _chat_llm(0.3)
    prompt = ChatPromptTemplate.from_messages([("system", GENERATE_PROMPT)])
    chain = prompt | llm
    memory_str = json.dumps(state.get("memory", []), ensure_ascii=False)
    resp = chain.invoke(
        {
            "template": json.dumps(PRODUCT_BRIEF_TEMPLATE, ensure_ascii=False),
            "memory": memory_str,
        },
        config={"callbacks": [lf_handler]},
    )
    return _safe_json_loads(resp.content)

def reflect_validate(state: GathererState) -> Dict[str, Any]:
    llm = _chat_llm(0.2)
    prompt = ChatPromptTemplate.from_messages([("system", REFLECTION_PROMPT)])
    chain = prompt | llm
    memory_str = json.dumps(state.get("memory", []), ensure_ascii=False)
    resp = chain.invoke(
        {
            "brief": state.get("brief", ""),
            "memory": memory_str,
        },
        config={"callbacks": [lf_handler]},
    )
    return _safe_json_loads(resp.content)

# ===== Tools list =====
tools = [
    DuckDuckGoSearchRun(name="web_search"),
    Tool(name="evaluate_completeness", func=evaluate_completeness,
         description="Đánh giá tính hoàn chỉnh của thông tin dựa trên memory."),
    Tool(name="naturalize_question", func=naturalize_question,
         description="Chuyển gaps thành câu hỏi tự nhiên."),
    Tool(name="generate_brief", func=generate_brief,
         description="Tạo product brief từ memory."),
    Tool(name="reflect_validate", func=reflect_validate,
         description="Phản ánh và validate brief."),
]

# ===== System prompt =====
SYSTEM_PROMPT = """
Bạn là Gatherer Agent, phỏng vấn user để thu thập thông tin sản phẩm và tạo brief.
Sử dụng tools để đánh giá, hỏi thêm, search nếu cần, và generate brief khi hoàn chỉnh (>0.8).
Bắt đầu bằng chào hỏi empathic.
Giữ memory cập nhật.
Kết thúc khi brief validated.
"""

# ===== LLM + Memory + Agent =====
llm = _chat_llm(0.4)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True,
    handle_parsing_errors=True,
    callbacks=[lf_handler],
)

# ===== Public API =====
def run_gatherer(user_input: str):
    # State khởi tạo (nếu sau này bạn muốn chuyền state vào tools)
    state = GathererState(
        input_data={},
        memory=[],
        uncertainties=[],
        brief=None,
        status="chưa hoàn tất",
        next_question=None,
        tool_results={},
        gaps=[],
        completeness_score=0.0
    )
    response = agent_executor.invoke({"input": user_input}, config={"callbacks": [lf_handler]})
    return response["output"]
