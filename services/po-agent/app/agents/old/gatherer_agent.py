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
import uuid
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

# ===== Langfuse callback =====
Langfuse()
lf_handler = CallbackHandler()

def _lf_metadata():
    """Metadata Langfuse cho mỗi run."""
    return {
        "langfuse_user_id": 'đồng đội ngu như bò',
        "langfuse_session_id":'gatherer-agent-demo' + uuid.uuid4(),
        "langfuse_tags": ["gatherer", "react-agent"],
    }

# ===== Cấu hình OpenAI-compatible =====
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4.1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

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
    """Khởi tạo ChatOpenAI trỏ tới OpenAI-compatible endpoint."""
    return ChatOpenAI(
        model=MODEL_NAME,
        temperature=temp,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        callbacks=[lf_handler],
    )

# ReAct tools cần nhận string input và trả về string output
def evaluate_completeness(input_str: str) -> str:
    """Đánh giá tính hoàn chỉnh của thông tin dựa trên memory."""
    # Lấy memory từ agent_executor's memory (sẽ được truyền qua context)
    llm = _chat_llm(0.3)
    prompt = ChatPromptTemplate.from_messages([("system", EVALUATE_PROMPT)])
    chain = prompt | llm
    
    # Tạm thời dùng empty memory, sau này có thể lấy từ context
    memory_str = "[]"  
    
    try:
        resp = chain.invoke(
            {
                "template": json.dumps(PRODUCT_BRIEF_TEMPLATE, ensure_ascii=False),
                "memory": memory_str,
            },
            config={"callbacks": [lf_handler], "metadata": _lf_metadata()},
        )
        return resp.content
    except Exception as e:
        return f"Lỗi khi đánh giá: {str(e)}"

def naturalize_question(input_str: str) -> str:
    """Chuyển gaps thành câu hỏi tự nhiên."""
    llm = _chat_llm(0.5)
    prompt = ChatPromptTemplate.from_messages([("system", NATURAL_QUESTION_PROMPT)])
    chain = prompt | llm

    try:
        resp = chain.invoke(
            {"uncertainties": input_str},
            config={"callbacks": [lf_handler], "metadata": _lf_metadata()},
        )
        return resp.content.strip()
    except Exception as e:
        return f"Lỗi khi tạo câu hỏi: {str(e)}"

def generate_brief(input_str: str) -> str:
    """Tạo product brief từ memory."""
    llm = _chat_llm(0.3)
    prompt = ChatPromptTemplate.from_messages([("system", GENERATE_PROMPT)])
    chain = prompt | llm
    
    # Tạm thời dùng empty memory
    memory_str = "[]"
    
    try:
        resp = chain.invoke(
            {
                "template": json.dumps(PRODUCT_BRIEF_TEMPLATE, ensure_ascii=False),
                "memory": memory_str,
            },
            config={"callbacks": [lf_handler], "metadata": _lf_metadata()},
        )
        return resp.content
    except Exception as e:
        return f"Lỗi khi tạo brief: {str(e)}"

def reflect_validate(input_str: str) -> str:
    """Phản ánh và validate brief."""
    llm = _chat_llm(0.2)
    prompt = ChatPromptTemplate.from_messages([("system", REFLECTION_PROMPT)])
    chain = prompt | llm
    
    # Parse input_str như brief JSON nếu có thể
    brief_str = input_str
    memory_str = "[]"
    
    try:
        resp = chain.invoke(
            {
                "brief": brief_str,
                "memory": memory_str,
            },
            config={"callbacks": [lf_handler], "metadata": _lf_metadata()},
        )
        return resp.content
    except Exception as e:
        return f"Lỗi khi validate: {str(e)}"

# ===== Tools list =====
tools = [
    DuckDuckGoSearchRun(name="web_search"),
    Tool(
        name="evaluate_completeness", 
        func=evaluate_completeness,
        description="Đánh giá tính hoàn chỉnh của thông tin dựa trên memory. Input: mô tả về thông tin cần đánh giá"
    ),
    Tool(
        name="naturalize_question", 
        func=naturalize_question,
        description="Chuyển gaps thành câu hỏi tự nhiên. Input: danh sách các gaps hoặc uncertainties"
    ),
    Tool(
        name="generate_brief", 
        func=generate_brief,
        description="Tạo product brief từ memory. Input: yêu cầu tạo brief"
    ),
    Tool(
        name="reflect_validate", 
        func=reflect_validate,
        description="Phản ánh và validate brief. Input: brief JSON cần validate"
    ),
]

# ===== FIXED: Correct ReAct prompt format =====
# ReAct agent cần format string đặc biệt cho agent_scratchpad
from langchain_core.prompts import PromptTemplate

REACT_PROMPT_TEMPLATE = """Bạn là Gatherer Agent chuyên phỏng vấn để thu thập yêu cầu và tạo product brief.
Mục tiêu: (1) hỏi tối thiểu, (2) điền đủ brief theo template đã biết, (3) chỉ gọi tool khi cần, (4) khi đủ thông tin thì kết thúc bằng Final Answer.

QUY TẮC BẮT BUỘC (PHẢI TUÂN THỦ 100%):
1) Mọi lượt trả lời PHẢI bắt đầu bằng dòng:
   Thought: <mô tả ngắn gọn bạn sẽ làm gì tiếp theo>

2) Nếu dùng tool, bạn PHẢI in đúng 4 dòng theo thứ tự y như sau (không thêm/bớt dòng, không thêm prefix khác):
   Thought: <vì sao cần dùng tool>
   Action: <tên_tool_chính_xác_trong_danh_sách>
   Action Input: <một CHUỖI duy nhất; nếu là JSON thì phải là JSON string hợp lệ trên MỘT DÒNG>
   Observation: <nội dung kết quả tool (tóm tắt ngắn, một dòng)>

   - Không được in thêm chữ nào khác ngoài 4 dòng trên cho mỗi lần gọi tool.
   - Nếu cần gọi nhiều tool, lặp lại đúng block 4 dòng cho từng tool theo thứ tự.
   
2.2) Nếu KHÔNG dùng tool mà muốn hỏi người dùng, bạn PHẢI kết thúc lượt đó bằng:
Thought: Tôi đã có đủ thông tin để trả lời
Final Answer: <đặt tối đa 3 câu hỏi ngắn gọn ở đây, mỗi câu trên 1 dòng, không thêm chữ nào khác>

3) Nếu đã đủ để trả lời user, bạn PHẢI kết thúc bằng đúng 2 dòng:
   Thought: Tôi đã có đủ thông tin để trả lời
   Final Answer: <câu trả lời cuối cùng cho người dùng>

4) KHÔNG được in lời chào, giải thích dài dòng, hay bất kỳ văn bản nào Ở NGOÀI các block quy định (Thought/Action/Action Input/Observation/Final Answer).

5) Khi gọi tool:
   - Tên tool phải khớp chính xác với một trong {tool_names}.
   - Action Input phải là CHUỖI. Nếu cần truyền JSON, hãy nhúng JSON vào chuỗi một dòng (escape dấu xuống dòng).
   - Chỉ truyền nội dung đủ dùng (đã loại trùng lặp, đã rút gọn).
   - Không truyền “memory_str = []” giả; luôn dùng ngữ cảnh từ {chat_history} + {input} đã được bạn tổng hợp.

6) Chiến lược hỏi thêm:
   - Mỗi lượt hỏi tối đa 3 câu HAY NHẤT (ngắn gọn, rõ ràng).
   - Không lặp lại câu đã hỏi trước đó (hãy kiểm tra {chat_history}).
   - Nếu có thể tự giả định hợp lý (và đánh dấu là “giả định — cần xác nhận”), hãy làm vậy để giảm số câu hỏi.
   - Chỉ hỏi tiếp khi thực sự cần để tiến tới Final Answer.

7) Tối giản vòng lặp:
   - Ưu tiên tóm tắt ngắn gọn Observation, rồi ra quyết định.
   - Khi đủ thông tin cho bản brief mức “>= 0.8” (gần đầy đủ), hãy Final Answer thay vì hỏi thêm.

8) Output phải hoàn toàn bằng tiếng Việt.

--------------------------------
THÔNG TIN TOOL KHẢ DỤNG
{tools}

Tên các công cụ hợp lệ: {tool_names}
--------------------------------

BỐI CẢNH HỘI THOẠI TRƯỚC ĐÓ:
{chat_history}

YÊU CẦU MỚI NHẤT TỪ USER:
{input}

NHẬT KÝ LÀM VIỆC (để bạn ghi lại chuỗi Thought/Action/Observation):
{agent_scratchpad}"""


# ===== LLM + Memory + Agent =====
llm = _chat_llm(0.4)

# Sử dụng PromptTemplate thay vì ChatPromptTemplate cho ReAct
prompt = PromptTemplate.from_template(REACT_PROMPT_TEMPLATE)

# Create agent với prompt đã sửa
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt,
)

# Memory với format phù hợp
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=False,  # ReAct cần string, không phải messages
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True,
    handle_parsing_errors="Thought: Tôi cần định dạng lại theo yêu cầu.\n",
    callbacks=[lf_handler],
    max_iterations=15,  # Giới hạn số lần lặp để tránh loop vô hạn
    early_stopping_method="force",  # Dừng sau khi đạt max_iterations
    max_execution_time=20.0
)

# ===== Public API =====
def run_gatherer(user_input: str):
    """Chạy Gatherer Agent với input từ user."""
    try:
        response = agent_executor.invoke(
            {"input": user_input},
            config={"callbacks": [lf_handler], "metadata": _lf_metadata()},
        )
        return response["output"]
    except Exception as e:
        print(f"Error in agent execution: {e}")
        # Nếu lỗi parsing format ReAct, trả về response đơn giản
        if "Could not parse LLM output" in str(e):
            return "Xin lỗi, tôi không hiểu yêu cầu. Bạn có thể nói rõ hơn về sản phẩm bạn muốn phát triển không?"
        return f"Xin lỗi, có lỗi xảy ra: {str(e)}"