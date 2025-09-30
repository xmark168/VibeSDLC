"""
Gatherer Agent

Tính năng:
- Phỏng vấn người dùng để thu thập requirements
- Lập kế hoạch từ câu hỏi nghiên cứu
- Web search và extract nội dung (tavily)
- Tổng hợp insight và requirements
- Giao tiếp với các sub-agents khác trong PO

"""

from __future__ import annotations
from typing import List, Dict, Any, Set, Optional
from typing_extensions import TypedDict, Literal
from dataclasses import dataclass
import os, json, time
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

# LLM
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
import httpx

# Tavily tools
from langchain_tavily import TavilySearch, TavilyExtract

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# === Data Models ===

class UserRequirement(BaseModel):
    """Mô hình cho một requirement từ user"""
    id: str
    title: str
    description: str
    priority: Literal["high", "medium", "low"] = "medium"
    category: str  # e.g., "functional", "non-functional", "ui/ux"
    source: str  # "interview", "research", "assumption"
    confidence: float = 0.5  # 0-1, độ tin cậy của requirement
    created_at: datetime = Field(default_factory=datetime.now)


class ResearchQuery(BaseModel):
    """Câu hỏi nghiên cứu"""
    query: str
    purpose: str
    priority: int = 1


class GathererState(TypedDict):
    """State của Gatherer Agent"""
    user_input: str
    conversation_history: List[Dict[str, Any]]
    requirements: List[UserRequirement]
    research_queries: List[ResearchQuery]
    research_results: List[Dict[str, Any]]
    insights: List[str]
    next_questions: List[str]
    status: Literal["gathering", "researching", "analyzing", "complete"]
    error: Optional[str]


# === Gatherer Agent Class ===

class GathererAgent:
    """
    Gatherer Agent - Thu thập requirements từ user và research
    """

    def __init__(self, llm_model: str = "gpt-4o-mini", api_base_url: str = "https://v98store.com/v1"):
        # Configure ChatOpenAI to use third-party API service
        self.llm = ChatOpenAI(
            model=llm_model,
            temperature=0.7,
            base_url=api_base_url,
            api_key=os.getenv("OPENAI_API_KEY")  # Your v98store API key
        )
        self.tavily_search = TavilySearch()
        self.tavily_extract = TavilyExtract()
        self.api_base_url = api_base_url

    async def check_api_balance(self) -> Dict[str, Any]:
        """Check API key balance from v98store"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return {"error": "API key not found in environment variables"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://v98store.com/check-balance?key={api_key}",
                    timeout=10.0
                )

                if response.status_code == 200:
                    return {"status": "success", "data": response.json()}
                else:
                    return {"error": f"API check failed with status {response.status_code}"}

        except Exception as e:
            return {"error": f"Failed to check API balance: {str(e)}"}

        # Prompts
        self.interview_prompt = ChatPromptTemplate.from_messages([
            ("system", """Bạn là một Product Owner chuyên nghiệp, nhiệm vụ là phỏng vấn user để thu thập requirements cho dự án website.

Nguyên tắc phỏng vấn:
1. Đặt câu hỏi mở, khuyến khích user chia sẻ chi tiết
2. Đào sâu vào business logic và user experience
3. Xác định rõ functional và non-functional requirements
4. Ưu tiên các tính năng theo business value
5. Tránh leading questions, để user tự mô tả vision

Hãy phân tích input của user và:
- Trích xuất requirements rõ ràng
- Đặt 2-3 câu hỏi follow-up thông minh
- Đề xuất research queries nếu cần

Trả về JSON format:
{{
    "requirements": [
        {{
            "title": "...",
            "description": "...",
            "category": "functional|non-functional|ui/ux",
            "priority": "high|medium|low",
            "confidence": 0.8
        }}
    ],
    "next_questions": ["...", "..."],
    "research_queries": [
        {{
            "query": "...",
            "purpose": "...",
            "priority": 1
        }}
    ]
}}"""),
            ("human", "{user_input}")
        ])

        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """Bạn là chuyên gia phân tích requirements. Hãy tổng hợp và phân tích:

1. Tất cả requirements đã thu thập
2. Kết quả research từ web
3. Insights và patterns

Đưa ra:
- Tóm tắt requirements theo priority
- Gaps cần thu thập thêm
- Recommendations cho development team

Format JSON:
{{
    "summary": "...",
    "priority_requirements": ["...", "..."],
    "gaps": ["...", "..."],
    "recommendations": ["...", "..."],
    "insights": ["...", "..."]
}}"""),
            ("human", "Requirements: {requirements}\nResearch: {research_results}")
        ])

    def create_workflow(self) -> StateGraph:
        """Tạo LangGraph workflow cho Gatherer"""
        workflow = StateGraph(GathererState)

        # Add nodes
        workflow.add_node("interview", self.interview_user)
        workflow.add_node("research", self.research_topics)
        workflow.add_node("analyze", self.analyze_requirements)

        # Add edges
        workflow.add_edge(START, "interview")
        workflow.add_conditional_edges(
            "interview",
            self.should_research,
            {
                "research": "research",
                "analyze": "analyze"
            }
        )
        workflow.add_edge("research", "analyze")
        workflow.add_edge("analyze", END)

        return workflow.compile()

    async def interview_user(self, state: GathererState) -> GathererState:
        """Phỏng vấn user để thu thập requirements"""
        try:
            # Check API balance before making calls
            balance_check = await self.check_api_balance()
            if "error" in balance_check:
                state["error"] = f"API service error: {balance_check['error']}"
                state["status"] = "complete"
                return state

            # Gọi LLM để phân tích input
            response = await self.llm.ainvoke(
                self.interview_prompt.format_messages(
                    user_input=state["user_input"]
                )
            )

            # Parse JSON response
            import json
            result = json.loads(response.content)

            # Cập nhật state
            new_requirements = [
                UserRequirement(
                    id=f"req_{len(state['requirements'])}_{int(time.time())}",
                    title=req["title"],
                    description=req["description"],
                    category=req["category"],
                    priority=req["priority"],
                    confidence=req["confidence"],
                    source="interview"
                )
                for req in result.get("requirements", [])
            ]

            state["requirements"].extend(new_requirements)
            state["next_questions"] = result.get("next_questions", [])
            state["research_queries"].extend([
                ResearchQuery(**query) for query in result.get("research_queries", [])
            ])
            state["status"] = "researching" if state["research_queries"] else "analyzing"

        except Exception as e:
            state["error"] = f"Interview error: {str(e)}"
            state["status"] = "complete"

        return state

    async def research_topics(self, state: GathererState) -> GathererState:
        """Research các topics liên quan đến requirements"""
        try:
            research_results = []

            for query in state["research_queries"]:
                # Search với Tavily
                search_results = await self.tavily_search.ainvoke(query.query)

                # Extract content từ top results
                if search_results and len(search_results) > 0:
                    top_urls = [result.get("url") for result in search_results[:3] if result.get("url")]
                    if top_urls:
                        extracted_content = await self.tavily_extract.ainvoke(top_urls)

                        research_results.append({
                            "query": query.query,
                            "purpose": query.purpose,
                            "search_results": search_results,
                            "extracted_content": extracted_content,
                            "timestamp": datetime.now().isoformat()
                        })

            state["research_results"] = research_results
            state["status"] = "analyzing"

        except Exception as e:
            state["error"] = f"Research error: {str(e)}"
            state["status"] = "analyzing"  # Continue to analysis even if research fails

        return state

    async def analyze_requirements(self, state: GathererState) -> GathererState:
        """Phân tích và tổng hợp tất cả requirements"""
        try:
            # Check API balance before making calls
            balance_check = await self.check_api_balance()
            if "error" in balance_check:
                state["error"] = f"API service error during analysis: {balance_check['error']}"
                state["status"] = "complete"
                return state

            # Prepare data for analysis
            requirements_summary = [
                {
                    "title": req.title,
                    "description": req.description,
                    "category": req.category,
                    "priority": req.priority,
                    "confidence": req.confidence,
                    "source": req.source
                }
                for req in state["requirements"]
            ]

            research_summary = [
                {
                    "query": res["query"],
                    "purpose": res["purpose"],
                    "key_findings": res.get("extracted_content", {}).get("summary", "No summary available")
                }
                for res in state["research_results"]
            ]

            # Gọi LLM để phân tích
            response = await self.llm.ainvoke(
                self.analysis_prompt.format_messages(
                    requirements=json.dumps(requirements_summary, indent=2),
                    research_results=json.dumps(research_summary, indent=2)
                )
            )

            # Parse kết quả
            import json
            analysis = json.loads(response.content)

            state["insights"] = analysis.get("insights", [])
            state["status"] = "complete"

            # Add analysis results to conversation history
            state["conversation_history"].append({
                "type": "analysis",
                "summary": analysis.get("summary", ""),
                "priority_requirements": analysis.get("priority_requirements", []),
                "gaps": analysis.get("gaps", []),
                "recommendations": analysis.get("recommendations", []),
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            state["error"] = f"Analysis error: {str(e)}"
            state["status"] = "complete"

        return state

    def should_research(self, state: GathererState) -> str:
        """Quyết định có cần research hay không"""
        if state["research_queries"] and len(state["research_queries"]) > 0:
            return "research"
        return "analyze"

    async def run(self, user_input: str) -> Dict[str, Any]:
        """Main method để chạy Gatherer agent"""
        # Initialize state
        initial_state: GathererState = {
            "user_input": user_input,
            "conversation_history": [],
            "requirements": [],
            "research_queries": [],
            "research_results": [],
            "insights": [],
            "next_questions": [],
            "status": "gathering",
            "error": None
        }

        # Create and run workflow
        workflow = self.create_workflow()
        final_state = await workflow.ainvoke(initial_state)

        # Format output
        return {
            "status": final_state["status"],
            "requirements": [req.model_dump() for req in final_state["requirements"]],
            "next_questions": final_state["next_questions"],
            "insights": final_state["insights"],
            "conversation_history": final_state["conversation_history"],
            "error": final_state.get("error")
        }


# === Tools cho Gatherer Agent ===

class GathererTools:
    """Collection of tools for Gatherer Agent"""

    def __init__(self, gatherer: GathererAgent):
        self.gatherer = gatherer

    async def interview_user(self, user_input: str) -> Dict[str, Any]:
        """Tool để phỏng vấn user"""
        return await self.gatherer.run(user_input)

    async def get_requirements_summary(self, requirements: List[UserRequirement]) -> str:
        """Tool để tóm tắt requirements"""
        summary = "## Requirements Summary\n\n"

        # Group by priority
        high_priority = [req for req in requirements if req.priority == "high"]
        medium_priority = [req for req in requirements if req.priority == "medium"]
        low_priority = [req for req in requirements if req.priority == "low"]

        for priority, reqs in [("High", high_priority), ("Medium", medium_priority), ("Low", low_priority)]:
            if reqs:
                summary += f"### {priority} Priority\n"
                for req in reqs:
                    summary += f"- **{req.title}**: {req.description}\n"
                summary += "\n"

        return summary

    async def export_requirements(self, requirements: List[UserRequirement], format: str = "json") -> str:
        """Export requirements to different formats"""
        if format == "json":
            return json.dumps([req.model_dump() for req in requirements], indent=2)
        elif format == "markdown":
            return await self.get_requirements_summary(requirements)
        else:
            raise ValueError(f"Unsupported format: {format}")


# === Factory function ===

def create_gatherer_agent(
    llm_model: str = "gpt-4o-mini",
    api_base_url: str = "https://v98store.com/v1"
) -> GathererAgent:
    """Factory function để tạo Gatherer Agent với third-party API support"""
    return GathererAgent(llm_model=llm_model, api_base_url=api_base_url)
