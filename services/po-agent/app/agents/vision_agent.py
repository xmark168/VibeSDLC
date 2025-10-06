from typing import TypedDict, Annotated, Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
import operator
import json
import os

# --- Langfuse (tùy chọn) ---
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

# Bật Langfuse nếu có cấu hình hợp lệ; hoặc comment 2 dòng dưới nếu đang bị 500
Langfuse()
lf_handler = CallbackHandler()

# ===== Common config =====
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4.1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

def _lf_metadata():
    return {
        "langfuse_user_id": os.getenv("LF_USER_ID", "it@ckhub.vn"),
        "langfuse_session_id": os.getenv("LF_SESSION_ID", "vision-agent-session"),
        "langfuse_tags": ["vision", "prd", "react-agent"],
    }

def _chat_llm(temp: float):
    return ChatOpenAI(
        model=MODEL_NAME,
        temperature=temp,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        callbacks=[lf_handler],
    )

# ===== Prompts =====
VISION_PROMPT = """
Bạn là chuyên gia Product Strategy. Hãy tạo **Product Vision** ngắn gọn, cô đọng, dựa trên MEMORY.
MEMORY: {memory}

YÊU CẦU:
- Viết tiếng Việt, súc tích, thực tế (không sáo rỗng).
- Trả về **DUY NHẤT** một JSON hợp lệ với các khóa:
{{
  "elevator_pitch": "...",
  "target_users": ["..."],
  "user_pains": ["..."],
  "value_proposition": ["..."],
  "guiding_principles": ["..."],
  "north_star_metric": "...",
  "success_metrics": ["..."],
  "out_of_scope": ["..."],
  "risks_assumptions": ["..."]
}}
Không thêm bất kỳ chữ nào ngoài JSON.
"""

PRD_PROMPT = """
Bạn là PM. Tạo **PRD** dựa trên MEMORY & VISION_JSON (nếu có).
MEMORY: {memory}
VISION_JSON: {vision_json}

Trả **DUY NHẤT** một JSON hợp lệ theo schema:
{{
  "overview": "",
  "goals": ["..."],
  "non_goals": ["..."],
  "personas": [
    {{"name": "...","summary": "...","primary_needs": ["..."]}}
  ],
  "user_stories": ["As a <user>, I want <need>, so that <value>"],
  "functional_requirements": ["..."],
  "non_functional_requirements": ["..."],
  "acceptance_criteria": ["..."],
  "scope_milestones": [
    {{"milestone": "MVP","items": ["..."]}},
    {{"milestone": "v1","items": ["..."]}}
  ],
  "metrics": ["..."],
  "risks": ["..."],
  "open_questions": ["..."]
}}
- Ưu tiên bám sát VISION_JSON; nếu thiếu thì suy luận hợp lý và đánh dấu "(giả định — cần xác nhận)" trong chuỗi.
- Ngắn gọn, rõ, khả thi. Không thêm chữ ngoài JSON.
"""

EVALUATE_PRD_PROMPT = """
Bạn là reviewer PRD. Đánh giá mức độ hoàn chỉnh (0-1) và liệt kê gaps còn thiếu/điểm mơ hồ.
INPUT: {prd_json}

Trả **DUY NHẤT** JSON:
{{
  "status": "hoàn tất/chưa hoàn tất/hỏi thêm",
  "completeness_score": 0.0,
  "gaps": ["..."]
}}
"""

REFINE_PRD_PROMPT = """
Bạn là PM. Cập nhật PRD dựa trên FEEDBACK & CURRENT_PRD.
CURRENT_PRD: {prd_json}
FEEDBACK: {feedback}

Trả **DUY NHẤT** JSON PRD đã cập nhật (cùng schema PRD ở trên). Không thêm chữ khác.
"""

QUESTIONS_PROMPT = """
Chuyển GAPS thành tối đa 3 câu hỏi ngắn gọn, không trùng lặp, tiếng Việt.
GAPS: {gaps}
Trả **DUY NHẤT** JSON: {{"questions": ["câu 1", "câu 2", "câu 3"]}}
"""

# ===== Tools (string in/out) =====
def _json_only(resp):
    text = resp.content.strip()
    # cắt lấy JSON
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text

def generate_product_vision(input_str: str) -> str:
    llm = _chat_llm(0.2)
    prompt = ChatPromptTemplate.from_messages([("system", VISION_PROMPT)])
    chain = prompt | llm
    resp = chain.invoke(
        {"memory": input_str.strip() or "{}"},
        config={"callbacks":[lf_handler], "metadata": _lf_metadata()},
    )
    return _json_only(resp)

def generate_prd(input_str: str) -> str:
    """
    input_str nên là JSON 1 dòng: {"memory":"...","vision_json":"..."}.
    """
    try:
        data = json.loads(input_str)
    except Exception:
        data = {"memory": input_str, "vision_json": ""}

    llm = _chat_llm(0.2)
    prompt = ChatPromptTemplate.from_messages([("system", PRD_PROMPT)])
    chain = prompt | llm
    resp = chain.invoke(
        {
            "memory": data.get("memory",""),
            "vision_json": data.get("vision_json",""),
        },
        config={"callbacks":[lf_handler], "metadata": _lf_metadata()},
    )
    return _json_only(resp)

def evaluate_prd(input_str: str) -> str:
    llm = _chat_llm(0.1)
    prompt = ChatPromptTemplate.from_messages([("system", EVALUATE_PRD_PROMPT)])
    chain = prompt | llm
    resp = chain.invoke(
        {"prd_json": input_str.strip()},
        config={"callbacks":[lf_handler], "metadata": _lf_metadata()},
    )
    return _json_only(resp)

def refine_prd(input_str: str) -> str:
    """
    input_str nên là JSON 1 dòng: {"prd_json":"...","feedback":"..."}.
    """
    try:
        data = json.loads(input_str)
    except Exception:
        # fallback: coi toàn bộ là feedback text
        data = {"prd_json": "{}", "feedback": input_str}

    llm = _chat_llm(0.2)
    prompt = ChatPromptTemplate.from_messages([("system", REFINE_PRD_PROMPT)])
    chain = prompt | llm
    resp = chain.invoke(
        {"prd_json": data.get("prd_json","{}"), "feedback": data.get("feedback","")},
        config={"callbacks":[lf_handler], "metadata": _lf_metadata()},
    )
    return _json_only(resp)

def naturalize_questions(input_str: str) -> str:
    llm = _chat_llm(0.2)
    prompt = ChatPromptTemplate.from_messages([("system", QUESTIONS_PROMPT)])
    chain = prompt | llm
    resp = chain.invoke(
        {"gaps": input_str.strip()},
        config={"callbacks":[lf_handler], "metadata": _lf_metadata()},
    )
    return _json_only(resp)

tools = [
    Tool(
        name="generate_product_vision",
        func=generate_product_vision,
        description="Tạo Product Vision JSON từ bối cảnh/memory (string). Input: chuỗi tóm tắt bối cảnh 1 dòng."
    ),
    Tool(
        name="generate_prd",
        func=generate_prd,
        description='Tạo PRD JSON từ memory + vision_json. Input: JSON 1 dòng {"memory":"...","vision_json":"..."}'
    ),
    Tool(
        name="evaluate_prd",
        func=evaluate_prd,
        description="Đánh giá độ hoàn chỉnh PRD. Input: PRD JSON 1 dòng."
    ),
    Tool(
        name="refine_prd",
        func=refine_prd,
        description='Cập nhật PRD theo phản hồi. Input: JSON 1 dòng {"prd_json":"...","feedback":"..."}'
    ),
    Tool(
        name="naturalize_questions",
        func=naturalize_questions,
        description="Chuyển danh sách gaps thành tối đa 3 câu hỏi. Input: chuỗi hoặc JSON gaps."
    ),
]

# ===== Strict ReAct Prompt =====
REACT_PROMPT_TEMPLATE = """Bạn là Vision Agent. Nhiệm vụ: tạo Product Vision và PRD chất lượng, hỏi tối thiểu.

QUY TẮC BẮT BUỘC:
1) Mọi lượt phải bắt đầu bằng:
Thought: <bạn sẽ làm gì tiếp theo>

2) Nếu dùng tool, in CHÍNH XÁC 4 dòng:
Thought: <lý do dùng tool>
Action: <tên_tool trong {tool_names}>
Action Input: <MỘT CHUỖI duy nhất; nếu JSON thì là JSON một dòng>
Observation: <tóm tắt kết quả 1 dòng>

2.3) Sau bất kỳ lần gọi tool nào, NẾU Observation cho ra:
- Vision JSON hợp lệ → NGAY LẬP TỨC kết thúc bằng:
  Thought: Tôi đã có đủ thông tin để trả lời
  Final Answer: <in NGUYÊN Vision JSON, không thêm gì khác>

- PRD JSON hợp lệ → NGAY LẬP TỨC kết thúc bằng:
  Thought: Tôi đã có đủ thông tin để trả lời
  Final Answer: <in NGUYÊN PRD JSON, không thêm gì khác>

- Questions JSON (các câu hỏi cần hỏi user) → NGAY LẬP TỨC kết thúc bằng:
  Thought: Tôi đã có đủ thông tin để trả lời
  Final Answer: <in tối đa 3 câu hỏi, mỗi câu 1 dòng, không thêm chữ khác>

3) Nếu KHÔNG dùng tool mà muốn hỏi user, PHẢI kết thúc bằng:
Thought: Tôi đã có đủ thông tin để trả lời
Final Answer: <tối đa 3 câu hỏi ngắn, mỗi câu 1 dòng>

4) Khi đã đủ, kết thúc bằng:
Thought: Tôi đã có đủ thông tin để trả lời
Final Answer: <Vision/PRD hoặc bước tiếp theo, dạng rõ ràng>

5) Không in thêm chữ nào ngoài các block Thought/Action/Action Input/Observation/Final Answer.
6) Mỗi lượt hỏi tối đa 3 câu, không trùng lặp (kiểm tra {chat_history}).
7) Nếu có thể, tự giả định hợp lý (đánh dấu “(giả định — cần xác nhận)”).

TOOLS:
{tools}

Tên công cụ: {tool_names}
--------------------------------
HỘI THOẠI TRƯỚC:
{chat_history}

YÊU CẦU MỚI:
{input}

NHẬT KÝ:
{agent_scratchpad}"""

# ===== LLM + Agent =====
llm = _chat_llm(0.3)
prompt = PromptTemplate.from_template(REACT_PROMPT_TEMPLATE)

agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt,
)

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=False,
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True,
    handle_parsing_errors="Thought: Tôi cần định dạng lại theo quy tắc và sẽ thử lại.\n",
    max_iterations=15,
    early_stopping_method="force",
    callbacks=[lf_handler],
    max_execution_time=60.0,
)

# ===== Public API =====
def run_vision(user_input: str):
    try:
        response = agent_executor.invoke(
            {"input": user_input},
            config={"callbacks":[lf_handler], "metadata": _lf_metadata()},
        )
        return response["output"]
    except Exception as e:
        if "Could not parse LLM output" in str(e):
            return "Xin lỗi, đầu ra chưa đúng định dạng. Hãy nhập lại ngắn gọn mục tiêu/đối tượng để tôi tạo Vision/PRD."
        return f"Xin lỗi, có lỗi xảy ra: {str(e)}"
