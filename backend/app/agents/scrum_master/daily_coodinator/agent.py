"""Daily Coordinator Agent - Orchestrates daily scrum activities.

This agent coordinates daily scrum by:
1. CollectDevReports: Calling DeveloperAgent to get daily progress reports
2. CollectTesterReports: Calling TesterAgent to get daily test reports
3. AggregateReports: Combining reports from both teams
4. DetectBlockers: Identifying blockers and issues
5. ExtractLearnings: Creating rules from blockers for knowledge base (NEW)
6. UpdateTaskStatus: Updating task status based on progress
7. GenerateSummary: Creating final daily scrum summary

Architecture: LangGraph-based workflow with node-based processing.
"""

import os
import sys
import time
import json
from typing import Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

# Handle imports
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from state import DailyScrumState
    from tools import aggregate_dev_and_tester_reports, detect_blockers_from_reports
else:
    from .state import DailyScrumState
    from .tools import aggregate_dev_and_tester_reports, detect_blockers_from_reports

# Import agents
try:
    from ...developer import DeveloperAgent
    from ...tester import TesterAgent
except ImportError:
    import sys
    from pathlib import Path
    app_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(app_path))
    from developer import DeveloperAgent
    from tester import TesterAgent

# Import prompts
try:
    from templates.prompts.scrum_master.daily_coordinator import (
        COLLECT_DEV_REPORTS_HEADER,
        COLLECT_DEV_REPORTS_SUCCESS,
        COLLECT_DEV_REPORTS_ERROR,
        COLLECT_TESTER_REPORTS_HEADER,
        COLLECT_TESTER_REPORTS_SUCCESS,
        COLLECT_TESTER_REPORTS_ERROR,
        UPDATE_TASK_STATUS_HEADER,
        UPDATE_TASK_STATUS_SUCCESS,
        UPDATE_TASK_STATUS_ERROR,
        UPDATE_TASK_STATUS_FOOTER,
        GENERATE_SUMMARY_HEADER,
        GENERATE_SUMMARY_SUCCESS,
        GENERATE_SUMMARY_ERROR,
        GENERATE_SUMMARY_FOOTER,
        ERROR_MISSING_DEV_REPORTS,
        ERROR_MISSING_TESTER_REPORTS,
        ERROR_AGGREGATING_REPORTS,
        ERROR_DETECTING_BLOCKERS,
        ERROR_UPDATING_TASK_STATUS,
        ERROR_GENERATING_SUMMARY,
        ERROR_DAILY_COORDINATOR,
    )
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    app_path = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(app_path))
    from templates.prompts.scrum_master.daily_coordinator import (
        COLLECT_DEV_REPORTS_HEADER,
        COLLECT_DEV_REPORTS_SUCCESS,
        COLLECT_DEV_REPORTS_ERROR,
        COLLECT_TESTER_REPORTS_HEADER,
        COLLECT_TESTER_REPORTS_SUCCESS,
        COLLECT_TESTER_REPORTS_ERROR,
        UPDATE_TASK_STATUS_HEADER,
        UPDATE_TASK_STATUS_SUCCESS,
        UPDATE_TASK_STATUS_ERROR,
        UPDATE_TASK_STATUS_FOOTER,
        GENERATE_SUMMARY_HEADER,
        GENERATE_SUMMARY_SUCCESS,
        GENERATE_SUMMARY_ERROR,
        GENERATE_SUMMARY_FOOTER,
        ERROR_MISSING_DEV_REPORTS,
        ERROR_MISSING_TESTER_REPORTS,
        ERROR_AGGREGATING_REPORTS,
        ERROR_DETECTING_BLOCKERS,
        ERROR_UPDATING_TASK_STATUS,
        ERROR_GENERATING_SUMMARY,
        ERROR_DAILY_COORDINATOR,
    )


class DailyCoordinatorAgent:
    """Daily Coordinator Agent - Orchestrates daily scrum activities."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Initialize Daily Coordinator Agent.

        Args:
            session_id: Session ID for tracing
            user_id: User ID for tracking
        """
        self.session_id = session_id
        self.user_id = user_id

        # Initialize LangFuse handler
        try:
            # Try relative import first
            try:
                from ...utils.langfuse_utils import initialize_langfuse_handler, create_langfuse_metadata
            except ImportError:
                # Fallback for direct script execution
                import sys
                from pathlib import Path
                utils_path = Path(__file__).parent.parent.parent.parent / "utils"
                sys.path.insert(0, str(utils_path.parent))
                from utils.langfuse_utils import initialize_langfuse_handler, create_langfuse_metadata

            metadata = create_langfuse_metadata(
                agent_type="daily_coordinator",
                additional_data={"session_id": session_id, "user_id": user_id}
            )
            self.langfuse_handler = initialize_langfuse_handler(
                session_id=session_id,
                user_id=user_id,
                agent_type="daily_coordinator",
                metadata=metadata
            )
        except Exception as e:
            import logging
            logging.warning(f"Failed to initialize LangFuse handler: {e}")
            self.langfuse_handler = None

        # Initialize sub-agents (without session_id to disable Langfuse tracing)
        # This prevents 413 errors by reducing trace payload size
        self.developer_agent = DeveloperAgent(
            session_id=None,  # Disable Langfuse for sub-agent
            user_id=user_id
        )
        self.tester_agent = TesterAgent(
            session_id=None,  # Disable Langfuse for sub-agent
            user_id=user_id
        )

        # Build LangGraph workflow
        self.graph = self._build_graph()

    def _llm(self, model: str = "gpt-4o-mini", temperature: float = 0.7) -> ChatOpenAI:
        """Initialize LLM instance for analysis and insights.

        Args:
            model: Model name (default: gpt-4o-mini)
            temperature: Temperature for LLM (default: 0.7 for creative insights)

        Returns:
            ChatOpenAI instance
        """
        try:
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
                callbacks=[self.langfuse_handler] if self.langfuse_handler else []
            )
            return llm
        except Exception as e:
            import logging
            logging.warning(f"Failed to initialize LLM: {e}")
            raise

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow with nodes for daily scrum.

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(DailyScrumState)

        # Add nodes
        workflow.add_node("collect_dev_reports", self._collect_dev_reports_node)
        workflow.add_node("collect_tester_reports", self._collect_tester_reports_node)
        workflow.add_node("aggregate_reports", self._aggregate_reports_node)
        workflow.add_node("detect_blockers", self._detect_blockers_node)
        workflow.add_node("extract_learnings", self._extract_learnings_node)  # NEW
        workflow.add_node("update_task_status", self._update_task_status_node)
        workflow.add_node("generate_summary", self._generate_summary_node)

        # Set entry point
        workflow.set_entry_point("collect_dev_reports")

        # Add edges
        workflow.add_edge("collect_dev_reports", "collect_tester_reports")
        workflow.add_edge("collect_tester_reports", "aggregate_reports")
        workflow.add_edge("aggregate_reports", "detect_blockers")
        workflow.add_edge("detect_blockers", "extract_learnings")  # NEW
        workflow.add_edge("extract_learnings", "update_task_status")  # UPDATED
        workflow.add_edge("update_task_status", "generate_summary")
        workflow.add_edge("generate_summary", END)

        return workflow.compile()

    def _collect_dev_reports_node(self, state: DailyScrumState) -> DailyScrumState:
        """Collect developer reports from DeveloperAgent."""
        print(COLLECT_DEV_REPORTS_HEADER)

        try:
            # Call DeveloperAgent to get daily reports
            dev_reports = self.developer_agent.get_daily_reports()
            state["dev_reports"] = dev_reports
            print(COLLECT_DEV_REPORTS_SUCCESS.format(
                total_developers=dev_reports.get('total_developers', 0)
            ))
        except Exception as e:
            state["error"] = ERROR_MISSING_DEV_REPORTS.format(error=str(e))
            print(COLLECT_DEV_REPORTS_ERROR.format(error=state['error']))

        return state

    def _collect_tester_reports_node(self, state: DailyScrumState) -> DailyScrumState:
        """Collect tester reports from TesterAgent."""
        print(COLLECT_TESTER_REPORTS_HEADER)

        try:
            # Call TesterAgent to get daily reports
            tester_reports = self.tester_agent.get_daily_reports()
            state["tester_reports"] = tester_reports
            print(COLLECT_TESTER_REPORTS_SUCCESS.format(
                total_testers=tester_reports.get('total_testers', 0)
            ))
        except Exception as e:
            state["error"] = ERROR_MISSING_TESTER_REPORTS.format(error=str(e))
            print(COLLECT_TESTER_REPORTS_ERROR.format(error=state['error']))

        return state

    def _aggregate_reports_node(self, state: DailyScrumState) -> DailyScrumState:
        """Aggregate reports from both teams using LLM for analysis."""
        print("\n" + "="*80)
        print("📊 AGGREGATING REPORTS WITH LLM ANALYSIS")
        print("="*80)

        try:
            if not state.get("dev_reports") or not state.get("tester_reports"):
                state["error"] = "Missing dev or tester reports"
                return state

            # First, aggregate using traditional method
            aggregated = aggregate_dev_and_tester_reports(
                state["dev_reports"],
                state["tester_reports"]
            )

            # Now use LLM to analyze and provide insights
            print("\n🤖 Calling LLM to analyze aggregated reports...")
            llm = self._llm(temperature=0.7)

            # Prepare data for LLM analysis
            reports_json = json.dumps(aggregated, indent=2, default=str)

            # Create prompt for LLM analysis using simple string format
            system_prompt = """You are an expert Scrum Master analyzing daily team reports.
Analyze the aggregated reports and provide:
1. Key insights about team progress
2. Potential risks or concerns
3. Recommendations for improvement
4. Team morale assessment

Respond in JSON format with keys: insights, risks, recommendations, morale_assessment"""

            human_prompt = f"Please analyze these daily reports:\n\n{reports_json}"

            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            response = llm.invoke(messages)

            # Parse LLM response
            try:
                response_text = response.content.strip()
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()

                llm_analysis = json.loads(response_text)
                aggregated["llm_analysis"] = llm_analysis
                print("✅ LLM analysis completed")
            except Exception as parse_e:
                import logging
                logging.debug(f"Failed to parse LLM response: {parse_e}")
                aggregated["llm_analysis"] = {"error": str(parse_e)}

            state["aggregated_reports"] = aggregated
            print("="*80 + "\n")

        except Exception as e:
            state["error"] = ERROR_AGGREGATING_REPORTS.format(error=str(e))
            print(f"❌ {state['error']}")
            # Set empty aggregated_reports to prevent downstream errors
            if "aggregated_reports" not in state:
                state["aggregated_reports"] = {
                    "dev_reports": state.get("dev_reports", []),
                    "tester_reports": state.get("tester_reports", []),
                    "team_metrics": {},
                    "llm_analysis": {"error": str(e)}
                }

        return state

    def _detect_blockers_node(self, state: DailyScrumState) -> DailyScrumState:
        """Detect and analyze blockers from aggregated reports using LLM."""
        print("\n" + "="*80)
        print("🚨 DETECTING BLOCKERS WITH LLM ANALYSIS")
        print("="*80)

        try:
            if not state.get("aggregated_reports"):
                state["error"] = "Missing aggregated reports"
                return state

            # First, detect blockers using traditional method
            blocker_analysis = detect_blockers_from_reports(
                state["aggregated_reports"]
            )

            # Now use LLM to analyze blockers and suggest solutions
            print("\n🤖 Calling LLM to analyze blockers and suggest solutions...")
            llm = self._llm(temperature=0.7)

            # Prepare blocker data for LLM
            blockers_json = json.dumps(blocker_analysis, indent=2, default=str)

            # Create prompt for LLM analysis using simple string format
            system_prompt = """You are an expert Scrum Master analyzing team blockers.
Analyze the detected blockers and provide:
1. Root cause analysis for each blocker
2. Priority ranking and impact assessment
3. Recommended solutions and mitigation strategies
4. Escalation recommendations if needed

Respond in JSON format with keys: root_causes, impact_assessment, solutions, escalations"""

            human_prompt = f"Please analyze these blockers:\n\n{blockers_json}"

            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            response = llm.invoke(messages)

            # Parse LLM response
            try:
                response_text = response.content.strip()
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()

                llm_analysis = json.loads(response_text)
                blocker_analysis["llm_analysis"] = llm_analysis
                print("✅ LLM blocker analysis completed")
            except Exception as parse_e:
                import logging
                logging.debug(f"Failed to parse LLM response: {parse_e}")
                blocker_analysis["llm_analysis"] = {"error": str(parse_e)}

            state["blocker_analysis"] = blocker_analysis
            state["detected_blockers"] = blocker_analysis.get("all_blockers", [])
            print("="*80 + "\n")

        except Exception as e:
            state["error"] = ERROR_DETECTING_BLOCKERS.format(error=str(e))
            print(f"❌ {state['error']}")
            # Set empty blocker_analysis to prevent downstream errors
            if "blocker_analysis" not in state:
                state["blocker_analysis"] = {
                    "total_blockers": 0,
                    "high_priority_count": 0,
                    "medium_priority_count": 0,
                    "low_priority_count": 0,
                    "llm_analysis": {"error": str(e)}
                }
            if "detected_blockers" not in state:
                state["detected_blockers"] = []

        return state

    def _extract_learnings_node(self, state: DailyScrumState) -> DailyScrumState:
        """Extract learnings from detected blockers and create project rules.

        This node:
        1. Analyzes detected blockers using LLM
        2. Extracts actionable rules/instructions
        3. Saves rules to knowledge base (RuleService)
        4. Tags rules for future retrieval
        """
        print("\n" + "="*80)
        print("🧠 EXTRACT LEARNINGS FROM BLOCKERS")
        print("="*80)

        try:
            blocker_analysis = state.get("blocker_analysis", {})
            detected_blockers = state.get("detected_blockers", [])
            project_id = state.get("project_id", "project-001")

            if not detected_blockers:
                print("ℹ️  No blockers detected - skipping learning extraction")
                state["extracted_rules"] = []
                print("="*80 + "\n")
                return state

            print(f"\n📋 Analyzing {len(detected_blockers)} blockers to extract learnings...")

            # Prepare blocker data for LLM
            blockers_json = json.dumps(detected_blockers, indent=2, default=str)

            # LLM prompt to extract learnings
            system_prompt = """You are an expert Scrum Master extracting actionable learnings from team blockers.

For each blocker, create a preventive rule/instruction that developers or testers can follow to avoid similar issues in the future.

For each rule, provide:
1. title: Short, actionable title (e.g., "Always validate API responses before processing")
2. description: Detailed instruction on how to prevent this blocker
3. tags: Array of relevant tags for retrieval (e.g., ["api", "validation", "error-handling"])
4. category: One of: technical, process, quality, communication
5. severity: high, medium, or low (based on blocker impact)
6. rule_type: One of: blocker_prevention, best_practice, code_standard

Respond in JSON format with array of rules."""

            human_prompt = f"""Analyze these blockers and extract preventive rules:

{blockers_json}

Create rules that are:
- Specific and actionable
- Tagged appropriately for retrieval
- Focused on prevention, not just description"""

            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            # Call LLM
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

            print("🤖 Calling LLM to extract rules from blockers...")
            response = llm.invoke(messages)

            # Parse LLM response
            response_text = response.content.strip()
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            extracted_rules_data = json.loads(response_text)

            # Save rules to knowledge base using RuleService
            try:
                from ....services.rule_service import RuleService, ProjectRule
            except ImportError:
                # Fallback for direct script execution
                import sys
                from pathlib import Path
                app_path = Path(__file__).parent.parent.parent.parent
                sys.path.insert(0, str(app_path))
                from services.rule_service import RuleService, ProjectRule

            saved_rules = []
            for rule_data in extracted_rules_data:
                # Create ProjectRule instance
                rule = ProjectRule(
                    project_id=project_id,
                    rule_type=rule_data.get("rule_type", "blocker_prevention"),
                    title=rule_data.get("title"),
                    description=rule_data.get("description"),
                    tags=rule_data.get("tags", []),
                    category=rule_data.get("category", "technical"),
                    severity=rule_data.get("severity", "medium"),
                    source_blocker_id=rule_data.get("source_blocker_id"),
                    source_type="daily_blocker",
                    created_by="scrum_master"
                )

                # Save to RuleService (in-memory storage for POC)
                saved_rule = RuleService.save_rule(rule)
                saved_rules.append(saved_rule.model_dump())

                print(f"\n✅ Rule Created: {rule.title}")
                print(f"   Category: {rule.category} | Severity: {rule.severity}")
                print(f"   Tags: {', '.join(rule.tags)}")

            state["extracted_rules"] = saved_rules
            print(f"\n📊 Total Rules Extracted: {len(saved_rules)}")
            print("="*80 + "\n")

        except Exception as e:
            print(f"❌ Error extracting learnings: {e}")
            import traceback
            traceback.print_exc()
            state["extracted_rules"] = []
            print("="*80 + "\n")

        return state

    def _update_task_status_node(self, state: DailyScrumState) -> DailyScrumState:
        """Update task status based on progress reports."""
        print(UPDATE_TASK_STATUS_HEADER)

        try:
            aggregated = state.get("aggregated_reports", {})
            dev_reports = aggregated.get("dev_reports", [])
            tester_reports = aggregated.get("tester_reports", [])

            # Prepare task status updates
            task_updates = {
                "timestamp": datetime.now().isoformat(),
                "dev_tasks": {
                    "completed": sum(len(r.get("tasks_completed_yesterday", [])) for r in dev_reports),
                    "in_progress": sum(len(r.get("tasks_in_progress", [])) for r in dev_reports),
                    "planned": sum(len(r.get("tasks_planned_today", [])) for r in dev_reports),
                },
                "test_tasks": {
                    "completed": sum(len(r.get("tests_completed_yesterday", [])) for r in tester_reports),
                    "in_progress": sum(len(r.get("tests_in_progress", [])) for r in tester_reports),
                    "planned": sum(len(r.get("tests_planned_today", [])) for r in tester_reports),
                },
                "quality_metrics": {
                    "bugs_found": sum(len(r.get("bugs_found", [])) for r in tester_reports),
                    "avg_test_coverage": aggregated.get("team_metrics", {}).get("testers", {}).get("avg_test_coverage", 0),
                }
            }

            state["task_status_updates"] = task_updates

            print(UPDATE_TASK_STATUS_SUCCESS.format(
                dev_completed=task_updates['dev_tasks']['completed'],
                dev_in_progress=task_updates['dev_tasks']['in_progress'],
                dev_planned=task_updates['dev_tasks']['planned'],
                test_completed=task_updates['test_tasks']['completed'],
                test_in_progress=task_updates['test_tasks']['in_progress'],
                test_planned=task_updates['test_tasks']['planned'],
                bugs_found=task_updates['quality_metrics']['bugs_found'],
                avg_coverage=task_updates['quality_metrics']['avg_test_coverage']
            ))

        except Exception as e:
            state["error"] = ERROR_UPDATING_TASK_STATUS.format(error=str(e))
            print(UPDATE_TASK_STATUS_ERROR.format(error=state['error']))

        print(UPDATE_TASK_STATUS_FOOTER + "\n")
        return state

    def _generate_summary_node(self, state: DailyScrumState) -> DailyScrumState:
        """Generate final daily scrum summary with LLM-generated insights."""
        print(GENERATE_SUMMARY_HEADER)

        try:
            # Build base summary
            summary = {
                "date": state.get("date", datetime.now().isoformat()),
                "sprint_id": state.get("sprint_id"),
                "status": "success" if not state.get("error") else "error",
                "error": state.get("error"),
                "team_metrics": state.get("aggregated_reports", {}).get("team_metrics", {}),
                "task_updates": state.get("task_status_updates", {}),
                "blockers": {
                    "total": state.get("blocker_analysis", {}).get("total_blockers", 0),
                    "high": state.get("blocker_analysis", {}).get("high_priority_count", 0),
                    "medium": state.get("blocker_analysis", {}).get("medium_priority_count", 0),
                    "low": state.get("blocker_analysis", {}).get("low_priority_count", 0),
                    "details": state.get("detected_blockers", [])
                },
                "timestamp": datetime.now().isoformat()
            }

            # Use LLM to generate executive summary and recommendations
            print("\n🤖 Calling LLM to generate executive summary...")
            llm = self._llm(temperature=0.7)

            # Prepare data for LLM
            summary_data = json.dumps({
                "team_metrics": summary["team_metrics"],
                "task_updates": summary["task_updates"],
                "blockers": summary["blockers"],
                "llm_analysis": state.get("aggregated_reports", {}).get("llm_analysis", {}),
                "blocker_analysis": state.get("blocker_analysis", {}).get("llm_analysis", {})
            }, indent=2, default=str)

            # Create prompt for executive summary using simple string format
            system_prompt = """You are an expert Scrum Master creating a daily standup summary.
Generate a concise executive summary including:
1. Overall team status (on track, at risk, blocked)
2. Key accomplishments from today
3. Top 3 priorities for tomorrow
4. Critical blockers requiring immediate attention
5. Team morale and engagement level

Respond in JSON format with keys: status, accomplishments, priorities, critical_blockers, morale, recommendations"""

            human_prompt = f"Please generate a daily standup summary based on this data:\n\n{summary_data}"

            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            response = llm.invoke(messages)

            # Parse LLM response
            try:
                response_text = response.content.strip()
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()

                llm_summary = json.loads(response_text)
                summary["executive_summary"] = llm_summary
                print("✅ Executive summary generated")
            except Exception as parse_e:
                import logging
                logging.debug(f"Failed to parse LLM response: {parse_e}")
                summary["executive_summary"] = {"error": str(parse_e)}

            state["daily_summary"] = summary

            print(GENERATE_SUMMARY_SUCCESS.format(
                status=summary['status'],
                total_blockers=summary['blockers']['total'],
                high_priority=summary['blockers']['high']
            ))

        except Exception as e:
            state["error"] = ERROR_GENERATING_SUMMARY.format(error=str(e))
            print(GENERATE_SUMMARY_ERROR.format(error=state['error']))

        print(GENERATE_SUMMARY_FOOTER + "\n")
        return state

    def run(
        self,
        sprint_id: str,
        date: Optional[str] = None
    ) -> dict:
        """Run daily scrum coordination.

        Args:
            sprint_id: Sprint ID
            date: Date for daily scrum (optional, defaults to today)

        Returns:
            dict: Daily scrum summary with status
        """
        start_time = time.time()

        try:
            # Prepare initial state
            initial_state: DailyScrumState = {
                "sprint_id": sprint_id,
                "date": date or datetime.now().isoformat(),
                "dev_reports": None,
                "tester_reports": None,
                "aggregated_reports": None,
                "detected_blockers": None,
                "blocker_analysis": None,
                "task_status_updates": None,
                "daily_summary": None,
                "error": None
            }

            # Add LangFuse handler to config if available
            config = {}
            if self.langfuse_handler:
                config["callbacks"] = [self.langfuse_handler]

            # Run graph
            final_state = self.graph.invoke(initial_state, config=config if config else None)

            # Flush Langfuse traces immediately after graph execution
            if self.langfuse_handler:
                try:
                    self.langfuse_handler.langfuse.flush()
                except Exception as flush_e:
                    import logging
                    logging.debug(f"Failed to flush Langfuse traces: {flush_e}")

            # Check if final_state is None
            if final_state is None:
                return {
                    "status": "error",
                    "error": "Graph execution returned None"
                }

            # Return result with status
            daily_summary = final_state.get("daily_summary")
            execution_time = time.time() - start_time

            if daily_summary:
                # Log successful execution
                if self.langfuse_handler:
                    try:
                        from ...utils.langfuse_utils import log_node_execution
                        log_node_execution(
                            node_name="daily_coordinator_workflow",
                            agent_type="daily_coordinator",
                            execution_time=execution_time,
                            output_data={
                                "status": "success",
                                "total_blockers": daily_summary.get("blockers", {}).get("total", 0),
                                "high_priority_blockers": daily_summary.get("blockers", {}).get("high", 0)
                            }
                        )
                    except Exception as e:
                        import logging
                        logging.debug(f"Failed to log node execution: {e}")

                return {
                    "status": "success",
                    "daily_summary": daily_summary
                }
            else:
                # Log error
                if self.langfuse_handler:
                    try:
                        from ...utils.langfuse_utils import log_node_execution
                        log_node_execution(
                            node_name="daily_coordinator_workflow",
                            agent_type="daily_coordinator",
                            execution_time=execution_time,
                            error=final_state.get("error", "No summary generated")
                        )
                    except Exception as e:
                        import logging
                        logging.debug(f"Failed to log error: {e}")

                return {
                    "status": "error",
                    "error": final_state.get("error", "No summary generated")
                }

        except Exception as e:
            execution_time = time.time() - start_time

            # Log exception
            if self.langfuse_handler:
                try:
                    from ...utils.langfuse_utils import log_node_execution
                    log_node_execution(
                        node_name="daily_coordinator_workflow",
                        agent_type="daily_coordinator",
                        execution_time=execution_time,
                        error=str(e)
                    )
                except Exception as log_e:
                    import logging
                    logging.debug(f"Failed to log error: {log_e}")

            print(ERROR_DAILY_COORDINATOR.format(error=str(e)))
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e)
            }


def create_daily_coordinator_agent(
    session_id: str,
    user_id: str
) -> DailyCoordinatorAgent:
    """Create Daily Coordinator Agent instance.

    Args:
        session_id: Session ID for tracing
        user_id: User ID for tracking

    Returns:
        DailyCoordinatorAgent instance
    """
    return DailyCoordinatorAgent(
        session_id=session_id,
        user_id=user_id
    )


# ============================================================================
# DIRECT EXECUTION - TEST DAILY COORDINATOR AGENT
# ============================================================================

if __name__ == "__main__":
    """
    Direct execution test for Daily Coordinator Agent.

    This block allows testing the Daily Coordinator Agent directly by running:
        python agent.py

    The test creates a Daily Coordinator Agent instance and runs it with mock data
    to simulate a complete daily scrum workflow.
    """
    from datetime import datetime

    print("\n" + "="*80)
    print("🚀 DAILY COORDINATOR AGENT - DIRECT TEST")
    print("="*80)

    # ========================================================================
    # Step 1: Initialize Daily Coordinator Agent
    # ========================================================================
    print("\n📌 Step 1: Initializing Daily Coordinator Agent...")
    agent = create_daily_coordinator_agent(
        session_id="test-session-001",
        user_id="test-user-001"
    )
    print("✅ Agent initialized successfully")

    # ========================================================================
    # Step 2: Prepare test data
    # ========================================================================
    print("\n📌 Step 2: Preparing test data...")
    test_sprint_id = "SPRINT-2024-Q1-001"
    test_date = datetime.now().isoformat()

    print(f"   Sprint ID: {test_sprint_id}")
    print(f"   Date: {test_date}")
    print("✅ Test data prepared")

    # ========================================================================
    # Step 3: Run Daily Coordinator Agent
    # ========================================================================
    print("\n📌 Step 3: Running Daily Coordinator Agent workflow...")
    print("   This will execute all 6 nodes:")
    print("   1. CollectDevReports - Collect developer reports")
    print("   2. CollectTesterReports - Collect tester reports")
    print("   3. AggregateReports - Aggregate reports from both teams")
    print("   4. DetectBlockers - Detect and analyze blockers")
    print("   5. UpdateTaskStatus - Update task status")
    print("   6. GenerateSummary - Generate final daily scrum summary")
    print()

    try:
        # Run the agent with test data
        result = agent.run(
            sprint_id=test_sprint_id,
            date=test_date
        )

        # ====================================================================
        # Step 4: Display results
        # ====================================================================
        print("\n" + "="*80)
        print("📊 DAILY COORDINATOR AGENT - TEST RESULTS")
        print("="*80)

        if result.get("status") == "success":
            print("\n✅ Daily Coordinator Agent executed successfully!")

            # Display summary
            if result.get("daily_summary"):
                summary = result["daily_summary"]
                print("\n📋 Daily Scrum Summary:")
                print(f"   Status: {summary.get('status')}")
                print(f"   Sprint: {summary.get('sprint_id')}")
                print(f"   Date: {summary.get('date')}")

                # Display blockers
                blockers = summary.get("blockers", {})
                print(f"\n🚨 Blockers:")
                print(f"   Total: {blockers.get('total', 0)}")
                print(f"   High Priority: {blockers.get('high', 0)}")
                print(f"   Medium Priority: {blockers.get('medium', 0)}")
                print(f"   Low Priority: {blockers.get('low', 0)}")

                # Display task updates
                task_updates = summary.get("task_updates", {})
                if task_updates:
                    print(f"\n📝 Task Updates:")
                    dev_tasks = task_updates.get("dev_tasks", {})
                    test_tasks = task_updates.get("test_tasks", {})

                    print(f"   Dev Tasks:")
                    print(f"      Completed: {dev_tasks.get('completed', 0)}")
                    print(f"      In Progress: {dev_tasks.get('in_progress', 0)}")
                    print(f"      Planned: {dev_tasks.get('planned', 0)}")

                    print(f"   Test Tasks:")
                    print(f"      Completed: {test_tasks.get('completed', 0)}")
                    print(f"      In Progress: {test_tasks.get('in_progress', 0)}")
                    print(f"      Planned: {test_tasks.get('planned', 0)}")

                # Display team metrics
                team_metrics = summary.get("team_metrics", {})
                if team_metrics:
                    print(f"\n📈 Team Metrics:")
                    dev_metrics = team_metrics.get("developers", {})
                    test_metrics = team_metrics.get("testers", {})

                    print(f"   Developers: {dev_metrics.get('count', 0)}")
                    print(f"   Testers: {test_metrics.get('count', 0)}")
                    print(f"   Avg Test Coverage: {test_metrics.get('avg_test_coverage', 0):.1f}%")
        else:
            print("\n❌ Daily Coordinator Agent encountered an error!")
            print(f"   Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"\n❌ Error running Daily Coordinator Agent: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("✅ TEST COMPLETED")
    print("="*80 + "\n")
