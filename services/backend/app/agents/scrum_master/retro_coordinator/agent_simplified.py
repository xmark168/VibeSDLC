"""Simplified Retro Coordinator Agent - Focus on generating project rules.

TraDS ============= Simplified workflow:
1. Get sprint data (metrics + blockers) from DB
2. Analyze with LLM to generate rules
3. Save rules to ProjectRules table
==============================
"""

import os
import json
from typing import Optional
from uuid import UUID
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import Session
from dotenv import load_dotenv

load_dotenv()

from .state import RetroState
from .schemas import ProjectRulesOutput
from .tools import get_sprint_blockers, get_sprint_metrics, update_project_rules


class RetroCoordinatorAgent:
    """Simplified Retro Coordinator Agent."""

    def __init__(self, session: Session):
        """Initialize agent with database session."""
        self.session = session
        self.graph = self._build_graph()

    def _llm(self, temperature: float = 0.7) -> ChatOpenAI:
        """Initialize LLM."""
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    def _build_graph(self) -> StateGraph:
        """Build simplified workflow."""
        workflow = StateGraph(RetroState)

        workflow.add_node("collect_data", self._collect_data_node)
        workflow.add_node("generate_agent_reports", self._generate_agent_reports_node)
        workflow.add_node("analyze_and_generate_rules", self._analyze_node)
        workflow.add_node("save_rules", self._save_rules_node)

        workflow.set_entry_point("collect_data")
        workflow.add_edge("collect_data", "generate_agent_reports")
        workflow.add_edge("generate_agent_reports", "analyze_and_generate_rules")
        workflow.add_edge("analyze_and_generate_rules", "save_rules")
        workflow.add_edge("save_rules", END)

        return workflow.compile()

    def _collect_data_node(self, state: RetroState) -> RetroState:
        """Collect sprint metrics and blockers from DB."""
        print("\n📊 Collecting sprint data from database...")

        try:
            sprint_id = UUID(state["sprint_id"])

            # Get metrics
            metrics = get_sprint_metrics(self.session, sprint_id)
            state["sprint_metrics"] = metrics
            print(f"✅ Metrics: {metrics.get('completed_tasks')}/{metrics.get('total_tasks')} tasks, {metrics.get('completed_points')}/{metrics.get('total_points')} points")

            # Get blockers
            blockers = get_sprint_blockers(self.session, sprint_id)
            state["blockers"] = blockers
            print(f"✅ Blockers: {len(blockers)} found")

        except Exception as e:
            state["error"] = f"Error collecting data: {e}"
            print(f"❌ {state['error']}")

        return state

    def _generate_agent_reports_node(self, state: RetroState) -> RetroState:
        """Generate individual agent reports from sprint data."""
        print("\n📝 Generating agent reports...")

        try:
            metrics = state.get("sprint_metrics", {})
            blockers = state.get("blockers", [])
            user_feedback = state.get("user_feedback", "")

            # Prepare data for LLM
            metrics_json = json.dumps(metrics, indent=2)
            blockers_json = json.dumps(blockers, indent=2)

            # Categorize blockers by type
            dev_blockers = [b for b in blockers if b.get("type") == "DEV_BLOCKER"]
            test_blockers = [b for b in blockers if b.get("type") == "TEST_BLOCKER"]

            # Create structured LLM
            from .schemas import AgentReportsOutput
            structured_llm = self._llm().with_structured_output(AgentReportsOutput)

            # Build prompt
            system_prompt = """Bạn là Scrum Master tạo báo cáo cho từng agent trong sprint retrospective.

Tạo báo cáo cho 3 agents (PO, Developer, Tester) với format:
✅ Đã hoàn thành:
• ...
• ...

🚧 Vấn đề gặp phải:
• ...
• ...

Dựa trên:
- Sprint metrics (tasks, story points)
- Blockers từ team
- PO feedback (nếu có)

Viết bằng tiếng Việt, ngắn gọn, cụ thể."""

            human_prompt = f"""Tạo báo cáo cho từng agent:

METRICS:
{metrics_json}

BLOCKERS TỪ DEVELOPERS ({len(dev_blockers)} blockers):
{json.dumps(dev_blockers, indent=2)}

BLOCKERS TỪ TESTERS ({len(test_blockers)} blockers):
{json.dumps(test_blockers, indent=2)}

PO FEEDBACK:
{user_feedback if user_feedback else "Không có"}

Tạo báo cáo riêng cho PO, Developer và Tester."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            result = structured_llm.invoke(messages)

            # Fallback messages for empty reports
            fallback_po = "✅ Đã hoàn thành:\n• Sprint đang trong quá trình thực hiện\n\n🚧 Vấn đề gặp phải:\n• Chưa có đủ dữ liệu để đánh giá chi tiết"
            fallback_dev = "✅ Đã hoàn thành:\n• Team đang tích cực phát triển các tính năng\n\n🚧 Vấn đề gặp phải:\n• Chưa có đủ thông tin về blockers và tiến độ"
            fallback_tester = "✅ Đã hoàn thành:\n• Đang chuẩn bị test cases và môi trường test\n\n🚧 Vấn đề gặp phải:\n• Chưa có đủ dữ liệu testing để phân tích"

            # Store reports in state with fallback
            state["agent_reports"] = {
                "po": result.po_report if result.po_report and len(result.po_report.strip()) > 20 else fallback_po,
                "dev": result.dev_report if result.dev_report and len(result.dev_report.strip()) > 20 else fallback_dev,
                "tester": result.tester_report if result.tester_report and len(result.tester_report.strip()) > 20 else fallback_tester
            }

            print("✅ Agent reports generated")
            print(f"   PO: {state['agent_reports']['po'][:50]}...")
            print(f"   Dev: {state['agent_reports']['dev'][:50]}...")
            print(f"   Tester: {state['agent_reports']['tester'][:50]}...")

        except Exception as e:
            state["error"] = f"Error generating reports: {e}"
            print(f"❌ {state['error']}")
            import traceback
            traceback.print_exc()

            # Set fallback reports on error
            state["agent_reports"] = {
                "po": "✅ Đã hoàn thành:\n• Sprint đang trong quá trình thực hiện\n\n🚧 Vấn đề gặp phải:\n• Chưa có đủ dữ liệu để đánh giá chi tiết",
                "dev": "✅ Đã hoàn thành:\n• Team đang tích cực phát triển các tính năng\n\n🚧 Vấn đề gặp phải:\n• Chưa có đủ thông tin về blockers và tiến độ",
                "tester": "✅ Đã hoàn thành:\n• Đang chuẩn bị test cases và môi trường test\n\n🚧 Vấn đề gặp phải:\n• Chưa có đủ dữ liệu testing để phân tích"
            }

        return state

    def _analyze_node(self, state: RetroState) -> RetroState:
        """Analyze sprint data and generate rules with LLM."""
        print("\n🤖 Analyzing sprint and generating rules...")

        try:
            metrics = state.get("sprint_metrics", {})
            blockers = state.get("blockers", [])
            user_feedback = state.get("user_feedback", "")

            # Prepare data for LLM
            metrics_json = json.dumps(metrics, indent=2)
            blockers_json = json.dumps(blockers, indent=2)

            # Create structured LLM
            structured_llm = self._llm().with_structured_output(ProjectRulesOutput)

            # Build prompt with PO feedback integration
            system_prompt = """Bạn là Scrum Master chuyên nghiệp phân tích sprint retrospective.

Nhiệm vụ:
1. Tạo tóm tắt sprint overview (2-3 câu) bằng tiếng Việt
2. Liệt kê những điều tốt (what went well) dạng bullet points - KẾT HỢP từ metrics, blockers VÀ feedback PO
3. Tóm tắt blockers theo loại (PO/Dev/Tester) - KẾT HỢP từ blockers DB VÀ feedback PO
4. Tạo quy tắc cải tiến cho từng role (PO/Dev/Tester) cho sprint tiếp theo

Quy tắc phải:
- Cụ thể, có thể thực hiện được
- Dựa trên blockers, metrics VÀ FEEDBACK TỪ PRODUCT OWNER
- Ưu tiên những gì PO quan tâm (nếu có feedback)
- Ngăn chặn vấn đề tương tự trong tương lai
- Viết bằng tiếng Việt
- Dạng bullet points"""

            # Build human prompt
            human_prompt_parts = ["Phân tích sprint retrospective:\n"]

            human_prompt_parts.append(f"SPRINT METRICS:\n{metrics_json}\n")
            human_prompt_parts.append(f"BLOCKERS TỪ TEAM (Dev/Tester):\n{blockers_json}\n")

            if user_feedback and user_feedback.strip():
                human_prompt_parts.append(f"FEEDBACK TỪ PRODUCT OWNER:\n{user_feedback}\n")
                human_prompt_parts.append("⚠️ QUAN TRỌNG: Kết hợp feedback PO vào 'what went well' và 'blockers summary'. Nếu PO nói về vấn đề gì, phải xuất hiện trong rules.\n")

            human_prompt_parts.append("Tạo overview, what went well (kết hợp metrics + PO feedback), blockers summary (kết hợp blockers DB + PO feedback) và rules cho PO/Dev/Tester.")

            human_prompt = "\n".join(human_prompt_parts)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            result = structured_llm.invoke(messages)

            # Update state
            state["overview_summary"] = result.overview_summary
            state["what_went_well"] = result.what_went_well
            state["blockers_summary"] = result.blockers_summary
            state["po_rules"] = result.po_rules
            state["dev_rules"] = result.dev_rules
            state["tester_rules"] = result.tester_rules

            print("✅ Rules generated successfully")

        except Exception as e:
            state["error"] = f"Error analyzing: {e}"
            print(f"❌ {state['error']}")
            import traceback
            traceback.print_exc()

        return state

    def _save_rules_node(self, state: RetroState) -> RetroState:
        """Save rules to database."""
        print("\n💾 Saving rules to database...")

        try:
            project_id = UUID(state["project_id"])
            po_rules = state.get("po_rules", "")
            dev_rules = state.get("dev_rules", "")
            tester_rules = state.get("tester_rules", "")

            success = update_project_rules(
                self.session,
                project_id,
                po_rules,
                dev_rules,
                tester_rules
            )

            if success:
                print("✅ Rules saved to database")

                # Build final summary
                metrics = state.get("sprint_metrics", {})
                agent_reports = state.get("agent_reports", {})
                print(f"\n📦 Final agent_reports being saved:")
                print(f"   Keys: {list(agent_reports.keys())}")
                print(f"   PO length: {len(agent_reports.get('po', ''))}")
                print(f"   Dev length: {len(agent_reports.get('dev', ''))}")
                print(f"   Tester length: {len(agent_reports.get('tester', ''))}")

                state["retro_summary"] = {
                    "status": "success",
                    "sprint_metrics": metrics,
                    "agent_reports": agent_reports,
                    "overview_summary": state.get("overview_summary"),
                    "what_went_well": state.get("what_went_well"),
                    "blockers_summary": state.get("blockers_summary"),
                    "blockers": state.get("blockers", []),
                    "po_rules": po_rules,
                    "dev_rules": dev_rules,
                    "tester_rules": tester_rules,
                }
            else:
                state["error"] = "Failed to save rules"

        except Exception as e:
            state["error"] = f"Error saving rules: {e}"
            print(f"❌ {state['error']}")

        return state

    def run(self, sprint_id: str, project_id: str, user_feedback: Optional[str] = None) -> dict:
        """Run retrospective analysis.

        Args:
            sprint_id: Sprint UUID
            project_id: Project UUID
            user_feedback: Optional user feedback to refine rules

        Returns:
            Retrospective summary
        """
        print("\n" + "="*80)
        print("🚀 RETRO COORDINATOR AGENT - SIMPLIFIED")
        print("="*80)

        try:
            initial_state: RetroState = {
                "sprint_id": sprint_id,
                "project_id": project_id,
                "user_feedback": user_feedback,
                "sprint_metrics": None,
                "blockers": None,
                "agent_reports": None,  # NEW
                "what_went_well": None,
                "blockers_summary": None,
                "overview_summary": None,
                "po_rules": None,
                "dev_rules": None,
                "tester_rules": None,
                "retro_summary": None,
                "error": None,
            }

            final_state = self.graph.invoke(initial_state)

            if final_state.get("error"):
                return {
                    "status": "error",
                    "error": final_state["error"]
                }

            return {
                "status": "success",
                "data": final_state.get("retro_summary")
            }

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e)
            }


def create_retro_coordinator_agent(session: Session) -> RetroCoordinatorAgent:
    """Create agent instance."""
    return RetroCoordinatorAgent(session=session)
