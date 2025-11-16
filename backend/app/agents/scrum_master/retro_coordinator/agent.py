"""Retro Coordinator Agent - Orchestrates sprint retrospective activities.

This agent coordinates sprint retrospective by:
1. CollectPOFeedback: Calling ProductOwnerAgent to get PO feedback
2. CollectDevFeedback: Calling DeveloperAgent to get developer feedback
3. CollectTesterFeedback: Calling TesterAgent to get tester feedback
4. CategorizeIssues: Categorizing feedback into issues
5. GenerateImprovementIdeas: Generating improvement ideas
6. DefineActionItems: Creating action items for next sprint
7. GenerateSummaryReport: Creating final retrospective report

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
    from state import RetroState
    from tools import (
        aggregate_all_feedback,
        categorize_feedback
    )
else:
    from .state import RetroState
    from .tools import (
        aggregate_all_feedback,
        categorize_feedback
    )

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
    from templates.prompts.scrum_master.retro_coordinator import (
        COLLECT_PO_FEEDBACK_HEADER,
        COLLECT_PO_FEEDBACK_SUCCESS,
        COLLECT_PO_FEEDBACK_ERROR,
        COLLECT_DEV_FEEDBACK_HEADER,
        COLLECT_DEV_FEEDBACK_SUCCESS,
        COLLECT_DEV_FEEDBACK_ERROR,
        COLLECT_TESTER_FEEDBACK_HEADER,
        COLLECT_TESTER_FEEDBACK_SUCCESS,
        COLLECT_TESTER_FEEDBACK_ERROR,
        CATEGORIZE_ISSUES_HEADER,
        CATEGORIZE_ISSUES_SUCCESS,
        CATEGORIZE_ISSUES_ERROR,
        GENERATE_IDEAS_HEADER,
        GENERATE_IDEAS_SUCCESS,
        GENERATE_IDEAS_ERROR,
        DEFINE_ACTIONS_HEADER,
        DEFINE_ACTIONS_SUCCESS,
        DEFINE_ACTIONS_ERROR,
        GENERATE_REPORT_HEADER,
        GENERATE_REPORT_SUCCESS,
        GENERATE_REPORT_ERROR,
        ERROR_MISSING_PO_FEEDBACK,
        ERROR_MISSING_DEV_FEEDBACK,
        ERROR_MISSING_TESTER_FEEDBACK,
        ERROR_CATEGORIZING_ISSUES,
        ERROR_GENERATING_IDEAS,
        ERROR_DEFINING_ACTIONS,
        ERROR_GENERATING_REPORT,
        ERROR_RETRO_COORDINATOR,
    )
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    app_path = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(app_path))
    from templates.prompts.scrum_master.retro_coordinator import (
        COLLECT_PO_FEEDBACK_HEADER,
        COLLECT_PO_FEEDBACK_SUCCESS,
        COLLECT_PO_FEEDBACK_ERROR,
        COLLECT_DEV_FEEDBACK_HEADER,
        COLLECT_DEV_FEEDBACK_SUCCESS,
        COLLECT_DEV_FEEDBACK_ERROR,
        COLLECT_TESTER_FEEDBACK_HEADER,
        COLLECT_TESTER_FEEDBACK_SUCCESS,
        COLLECT_TESTER_FEEDBACK_ERROR,
        CATEGORIZE_ISSUES_HEADER,
        CATEGORIZE_ISSUES_SUCCESS,
        CATEGORIZE_ISSUES_ERROR,
        GENERATE_IDEAS_HEADER,
        GENERATE_IDEAS_SUCCESS,
        GENERATE_IDEAS_ERROR,
        DEFINE_ACTIONS_HEADER,
        DEFINE_ACTIONS_SUCCESS,
        DEFINE_ACTIONS_ERROR,
        GENERATE_REPORT_HEADER,
        GENERATE_REPORT_SUCCESS,
        GENERATE_REPORT_ERROR,
        ERROR_MISSING_PO_FEEDBACK,
        ERROR_MISSING_DEV_FEEDBACK,
        ERROR_MISSING_TESTER_FEEDBACK,
        ERROR_CATEGORIZING_ISSUES,
        ERROR_GENERATING_IDEAS,
        ERROR_DEFINING_ACTIONS,
        ERROR_GENERATING_REPORT,
        ERROR_RETRO_COORDINATOR,
    )


class RetroCoordinatorAgent:
    """Retro Coordinator Agent - Orchestrates sprint retrospective activities."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Initialize Retro Coordinator Agent.

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
                agent_type="retro_coordinator",
                additional_data={"session_id": session_id, "user_id": user_id}
            )
            self.langfuse_handler = initialize_langfuse_handler(
                session_id=session_id,
                user_id=user_id,
                agent_type="retro_coordinator",
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
        """Initialize LLM instance for retrospective analysis.

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
        """Build LangGraph workflow with nodes for retrospective.

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(RetroState)

        # Add nodes
        workflow.add_node("collect_po_feedback", self._collect_po_feedback_node)
        workflow.add_node("collect_dev_feedback", self._collect_dev_feedback_node)
        workflow.add_node("collect_tester_feedback", self._collect_tester_feedback_node)
        workflow.add_node("categorize_issues", self._categorize_issues_node)
        workflow.add_node("generate_ideas", self._generate_ideas_node)
        workflow.add_node("define_actions", self._define_actions_node)
        workflow.add_node("extract_learnings", self._extract_learnings_node)
        workflow.add_node("generate_report", self._generate_report_node)

        # Set entry point
        workflow.set_entry_point("collect_po_feedback")

        # Add edges
        workflow.add_edge("collect_po_feedback", "collect_dev_feedback")
        workflow.add_edge("collect_dev_feedback", "collect_tester_feedback")
        workflow.add_edge("collect_tester_feedback", "categorize_issues")
        workflow.add_edge("categorize_issues", "generate_ideas")
        workflow.add_edge("generate_ideas", "define_actions")
        workflow.add_edge("define_actions", "extract_learnings")
        workflow.add_edge("extract_learnings", "generate_report")
        workflow.add_edge("generate_report", END)

        return workflow.compile()

    def _collect_po_feedback_node(self, state: RetroState) -> RetroState:
        """Collect feedback from Product Owner."""
        print(COLLECT_PO_FEEDBACK_HEADER)

        try:
            # Mock PO feedback - in real scenario, call ProductOwnerAgent
            # Note: Using generic "Product Owner Team" instead of hardcoded names
            po_feedback = {
                "po_name": "Product Owner Team",
                "feedback": [
                    {
                        "category": "what_went_well",
                        "content": "Team delivered all planned features on time",
                        "priority": "high",
                        "impact": "positive"
                    },
                    {
                        "category": "what_went_wrong",
                        "content": "Communication with stakeholders could be better",
                        "priority": "medium",
                        "impact": "negative"
                    },
                    {
                        "category": "improvement",
                        "content": "Need more frequent demos to stakeholders",
                        "priority": "medium",
                        "impact": None
                    }
                ]
            }
            state["po_feedback"] = po_feedback
            print(COLLECT_PO_FEEDBACK_SUCCESS.format(
                total_items=len(po_feedback.get("feedback", []))
            ))
        except Exception as e:
            state["error"] = ERROR_MISSING_PO_FEEDBACK.format(error=str(e))
            print(COLLECT_PO_FEEDBACK_ERROR.format(error=state['error']))

        return state

    def _collect_dev_feedback_node(self, state: RetroState) -> RetroState:
        """Collect feedback from developers."""
        print(COLLECT_DEV_FEEDBACK_HEADER)

        try:
            # Get developer retrospective feedback using dedicated method
            sprint_id = state.get("sprint_id", "N/A")
            dev_feedback = self.developer_agent.get_retrospective_feedback(sprint_id=sprint_id)

            state["dev_feedback"] = dev_feedback
            print(COLLECT_DEV_FEEDBACK_SUCCESS.format(
                total_developers=dev_feedback.get("total_developers", 0),
                total_items=dev_feedback.get("total_feedback_items", 0)
            ))
        except Exception as e:
            state["error"] = ERROR_MISSING_DEV_FEEDBACK.format(error=str(e))
            print(COLLECT_DEV_FEEDBACK_ERROR.format(error=state['error']))

        return state

    def _collect_tester_feedback_node(self, state: RetroState) -> RetroState:
        """Collect feedback from testers."""
        print(COLLECT_TESTER_FEEDBACK_HEADER)

        try:
            # Get tester retrospective feedback using dedicated method
            sprint_id = state.get("sprint_id", "N/A")
            tester_feedback = self.tester_agent.get_retrospective_feedback(sprint_id=sprint_id)

            state["tester_feedback"] = tester_feedback
            print(COLLECT_TESTER_FEEDBACK_SUCCESS.format(
                total_testers=tester_feedback.get("total_testers", 0),
                total_items=tester_feedback.get("total_feedback_items", 0)
            ))
        except Exception as e:
            state["error"] = ERROR_MISSING_TESTER_FEEDBACK.format(error=str(e))
            print(COLLECT_TESTER_FEEDBACK_ERROR.format(error=state['error']))

        return state

    def _categorize_issues_node(self, state: RetroState) -> RetroState:
        """Categorize feedback into issues using LLM."""
        print(CATEGORIZE_ISSUES_HEADER)

        try:
            # Aggregate all feedback
            all_feedback = aggregate_all_feedback(
                state.get("po_feedback"),
                state.get("dev_feedback"),
                state.get("tester_feedback")
            )
            state["all_feedback"] = all_feedback

            # Categorize into issues using traditional method
            issues = categorize_feedback(all_feedback)

            # Use LLM to enhance categorization and add deeper analysis
            print("\n🤖 Calling LLM to enhance issue categorization...")
            llm = self._llm(temperature=0.7)

            # Prepare feedback for LLM
            feedback_json = json.dumps(all_feedback, indent=2, default=str)

            # Create prompt for LLM categorization using simple string format
            system_prompt = """You are an expert Scrum Master analyzing retrospective feedback.
Analyze the feedback and provide:
1. Enhanced issue categorization with root causes
2. Patterns and themes across feedback
3. Impact assessment for each issue
4. Relationships between issues

Respond in JSON format with keys: enhanced_issues, patterns, impact_analysis, relationships"""

            human_prompt = f"Please analyze and categorize this feedback:\n\n{feedback_json}"

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
                # Enhance issues with LLM analysis
                for issue in issues:
                    issue["llm_analysis"] = llm_analysis
                print("✅ LLM issue categorization completed")
            except Exception as parse_e:
                import logging
                logging.debug(f"Failed to parse LLM response: {parse_e}")

            state["categorized_issues"] = issues

            # Count by severity
            high_severity = len([i for i in issues if i.get("severity") == "high"])
            medium_severity = len([i for i in issues if i.get("severity") == "medium"])
            low_severity = len([i for i in issues if i.get("severity") == "low"])

            print(CATEGORIZE_ISSUES_SUCCESS.format(
                total_issues=len(issues),
                high_severity=high_severity,
                medium_severity=medium_severity,
                low_severity=low_severity
            ))
        except Exception as e:
            state["error"] = ERROR_CATEGORIZING_ISSUES.format(error=str(e))
            print(CATEGORIZE_ISSUES_ERROR.format(error=state['error']))

        return state

    def _generate_ideas_node(self, state: RetroState) -> RetroState:
        """Generate improvement ideas from issues using LLM structured output."""
        print(GENERATE_IDEAS_HEADER)

        try:
            if not state.get("categorized_issues"):
                state["error"] = "No issues to generate ideas from"
                return state

            # Import Pydantic model for structured output
            try:
                from .schemas import GenerateIdeasOutput
            except ImportError:
                # Fallback for direct script execution
                from schemas import GenerateIdeasOutput

            # Prepare issues summary for LLM
            issues_summary = []
            for issue in state["categorized_issues"]:
                issues_summary.append({
                    "id": issue.get("id"),
                    "category": issue.get("category"),
                    "description": issue.get("description"),
                    "severity": issue.get("severity"),
                    "source": issue.get("source")
                })

            issues_json = json.dumps(issues_summary, indent=2)

            # Create structured LLM with Pydantic output
            print("\n🤖 Calling LLM to generate improvement ideas with structured output...")
            structured_llm = self._llm(temperature=0.7).with_structured_output(GenerateIdeasOutput)

            # Create detailed prompt for idea generation
            prompt = f"""Analyze these retrospective issues and generate 3-5 high-impact improvement ideas.

Issues:
{issues_json}

Requirements:
1. Focus on ROOT CAUSES, not symptoms
2. Prioritize by impact/effort ratio (high impact, low effort first)
3. Make ideas SPECIFIC and ACTIONABLE (not generic like "Improve communication")
4. Provide concrete implementation steps (3-5 steps per idea)
5. Define measurable success metrics
6. Consider risks and mitigation strategies
7. Estimate effort realistically (low/medium/high)

Generate ideas that will prevent similar issues in future sprints and improve team effectiveness."""

            from langchain_core.messages import HumanMessage
            result = structured_llm.invoke([HumanMessage(content=prompt)])

            # Convert Pydantic models to TypedDict format for state
            ideas = []
            for idx, idea_output in enumerate(result.ideas, 1):
                idea = {
                    "id": f"IDEA-{idx:03d}",
                    "title": idea_output.title,
                    "description": idea_output.description,
                    "related_issues": idea_output.related_issue_ids,
                    "expected_benefit": idea_output.expected_benefit,
                    "effort_estimate": idea_output.effort_estimate,
                    "priority": idea_output.priority,
                    # Additional fields from structured output
                    "implementation_steps": idea_output.implementation_steps,
                    "success_metrics": idea_output.success_metrics,
                    "risks": idea_output.risks
                }
                ideas.append(idea)

            state["improvement_ideas"] = ideas

            # Count by priority
            high_priority = len([i for i in ideas if i.get("priority") == "high"])
            medium_priority = len([i for i in ideas if i.get("priority") == "medium"])
            low_priority = len([i for i in ideas if i.get("priority") == "low"])

            # Display summary with rationale
            print(f"\n✅ Generated {len(ideas)} improvement ideas")
            print(f"   📝 Rationale: {result.rationale}")
            print(f"\n   Priority Breakdown:")
            print(f"      • High: {high_priority}")
            print(f"      • Medium: {medium_priority}")
            print(f"      • Low: {low_priority}")
            print(f"\n   Top Ideas:")
            for idea in ideas[:3]:
                print(f"      • {idea['title']}")
                print(f"        Priority: {idea['priority']} | Effort: {idea['effort_estimate']}")
                print(f"        Benefit: {idea['expected_benefit']}")

            print(GENERATE_IDEAS_SUCCESS.format(
                total_ideas=len(ideas),
                high_priority=high_priority,
                medium_priority=medium_priority,
                low_priority=low_priority
            ))

        except Exception as e:
            state["error"] = ERROR_GENERATING_IDEAS.format(error=str(e))
            print(GENERATE_IDEAS_ERROR.format(error=state['error']))
            import traceback
            traceback.print_exc()

        return state

    def _define_actions_node(self, state: RetroState) -> RetroState:
        """Define action items for next sprint using LLM structured output."""
        print(DEFINE_ACTIONS_HEADER)

        try:
            if not state.get("improvement_ideas"):
                state["error"] = "No improvement ideas to create actions from"
                return state

            # Import Pydantic model for structured output
            try:
                from .schemas import DefineActionsOutput
            except ImportError:
                # Fallback for direct script execution
                from schemas import DefineActionsOutput

            # Prepare improvement ideas for LLM
            ideas_json = json.dumps(state["improvement_ideas"], indent=2, default=str)
            sprint_name = state.get("sprint_name", "Next Sprint")

            # Create structured LLM with Pydantic output
            print("\n🤖 Calling LLM to define action items with structured output...")
            structured_llm = self._llm(temperature=0.7).with_structured_output(DefineActionsOutput)

            # Create detailed prompt for action definition
            prompt = f"""Convert these improvement ideas into 3-5 SMART action items for {sprint_name}.

Improvement Ideas:
{ideas_json}

Requirements:
1. Make actions SPECIFIC and MEASURABLE (SMART criteria)
2. Assign realistic OWNERS based on the improvement type:
   - "Developer Team" for technical/code improvements
   - "Tester Team" for quality/testing improvements
   - "Scrum Master" for process/communication improvements
3. Set SPECIFIC due dates (e.g., "Sprint 5 Day 3", "End of Week 2", "Mid-sprint checkpoint")
4. Define clear ACCEPTANCE CRITERIA for each action (how to verify completion)
5. Identify DEPENDENCIES between actions (what must be done first)
6. Prioritize by urgency and impact (high/medium/low)

Focus on actions that can be realistically completed within one sprint.
Each action should directly address one or more improvement ideas."""

            from langchain_core.messages import HumanMessage
            result = structured_llm.invoke([HumanMessage(content=prompt)])

            # Convert Pydantic models to TypedDict format for state
            actions = []
            for idx, action_output in enumerate(result.actions, 1):
                action = {
                    "id": f"ACTION-{idx:03d}",
                    "title": action_output.title,
                    "description": action_output.description,
                    "owner": action_output.owner,
                    "due_date": action_output.due_date,
                    "priority": action_output.priority,
                    "related_improvement": action_output.related_improvement_id,
                    "status": "pending",
                    # Additional fields from structured output
                    "acceptance_criteria": action_output.acceptance_criteria,
                    "dependencies": action_output.dependencies
                }
                actions.append(action)

            state["action_items"] = actions

            # Count by priority
            high_priority = len([a for a in actions if a.get("priority") == "high"])
            medium_priority = len([a for a in actions if a.get("priority") == "medium"])
            low_priority = len([a for a in actions if a.get("priority") == "low"])

            # Display summary with implementation plan
            print(f"\n✅ Defined {len(actions)} action items")
            print(f"   📋 Implementation Plan: {result.implementation_plan}")
            print(f"\n   Priority Breakdown:")
            print(f"      • High: {high_priority}")
            print(f"      • Medium: {medium_priority}")
            print(f"      • Low: {low_priority}")
            print(f"\n   Action Items:")
            for action in actions:
                print(f"      • {action['title']}")
                print(f"        Owner: {action['owner']} | Due: {action['due_date']} | Priority: {action['priority']}")
                if action.get('dependencies'):
                    print(f"        Dependencies: {', '.join(action['dependencies'])}")

            print(DEFINE_ACTIONS_SUCCESS.format(
                total_actions=len(actions),
                high_priority=high_priority,
                medium_priority=medium_priority,
                low_priority=low_priority
            ))

        except Exception as e:
            state["error"] = ERROR_DEFINING_ACTIONS.format(error=str(e))
            print(DEFINE_ACTIONS_ERROR.format(error=state['error']))
            import traceback
            traceback.print_exc()

        return state

    def _extract_learnings_node(self, state: RetroState) -> RetroState:
        """Extract learnings from action items and create project rules.

        This node:
        1. Analyzes action items using LLM
        2. Extracts actionable rules/instructions for developers and testers
        3. Saves rules to knowledge base (RuleService)
        4. Tags rules for future retrieval
        """
        print("\n" + "="*80)
        print("🧠 EXTRACT LEARNINGS FROM RETROSPECTIVE")
        print("="*80)

        try:
            action_items = state.get("action_items", [])
            categorized_issues = state.get("categorized_issues", [])
            project_id = state.get("project_id", "project-001")

            if not action_items:
                print("ℹ️  No action items - skipping learning extraction")
                state["extracted_rules"] = []
                print("="*80 + "\n")
                return state

            print(f"\n📋 Analyzing {len(action_items)} action items to extract learnings...")

            # Prepare data for LLM
            actions_json = json.dumps(action_items, indent=2, default=str)
            issues_json = json.dumps(categorized_issues, indent=2, default=str)

            # LLM prompt to extract learnings
            system_prompt = """You are an expert Scrum Master extracting actionable learnings from retrospective action items.

For each action item, create improvement rules/instructions that developers or testers can follow to prevent similar issues in future sprints.

For each rule, provide:
1. title: Short, actionable title (e.g., "Always write unit tests before integration tests")
2. description: Detailed instruction on how to implement this improvement
3. tags: Array of relevant tags for retrieval (e.g., ["testing", "quality", "best-practice"])
4. category: One of: technical, process, quality, communication
5. severity: high, medium, or low (based on action item priority)
6. rule_type: One of: best_practice, code_standard, process_improvement

Focus on creating rules that are:
- Preventive (not just reactive)
- Specific and actionable
- Applicable to future work
- Tagged appropriately for retrieval

Respond in JSON format with array of rules."""

            human_prompt = f"""Analyze these retrospective action items and related issues to extract improvement rules:

ACTION ITEMS:
{actions_json}

RELATED ISSUES:
{issues_json}

Create rules that will help the team avoid these issues in future sprints."""

            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            # Call LLM
            llm = self._llm(temperature=0.3)

            print("🤖 Calling LLM to extract improvement rules...")
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
                    rule_type=rule_data.get("rule_type", "process_improvement"),
                    title=rule_data.get("title"),
                    description=rule_data.get("description"),
                    tags=rule_data.get("tags", []),
                    category=rule_data.get("category", "process"),
                    severity=rule_data.get("severity", "medium"),
                    source_type="retro_improvement",
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

    def _generate_report_node(self, state: RetroState) -> RetroState:
        """Generate final retrospective summary report with LLM insights."""
        print(GENERATE_REPORT_HEADER)

        try:
            # Create base summary report
            retro_summary = {
                "status": "success",
                "sprint_id": state.get("sprint_id"),
                "sprint_name": state.get("sprint_name"),
                "date": state.get("date"),
                "total_feedback": len(state.get("all_feedback", [])),
                "po_feedback_count": len(state.get("po_feedback", {}).get("feedback", [])),
                "dev_feedback_count": len(state.get("dev_feedback", {}).get("feedback", [])),
                "tester_feedback_count": len(state.get("tester_feedback", {}).get("feedback", [])),
                "total_issues": len(state.get("categorized_issues", [])),
                "high_severity_issues": len([i for i in state.get("categorized_issues", []) if i.get("severity") == "high"]),
                "medium_severity_issues": len([i for i in state.get("categorized_issues", []) if i.get("severity") == "medium"]),
                "low_severity_issues": len([i for i in state.get("categorized_issues", []) if i.get("severity") == "low"]),
                "total_ideas": len(state.get("improvement_ideas", [])),
                "high_priority_ideas": len([i for i in state.get("improvement_ideas", []) if i.get("priority") == "high"]),
                "medium_priority_ideas": len([i for i in state.get("improvement_ideas", []) if i.get("priority") == "medium"]),
                "low_priority_ideas": len([i for i in state.get("improvement_ideas", []) if i.get("priority") == "low"]),
                "total_actions": len(state.get("action_items", [])),
                "high_priority_actions": len([a for a in state.get("action_items", []) if a.get("priority") == "high"]),
                "medium_priority_actions": len([a for a in state.get("action_items", []) if a.get("priority") == "medium"]),
                "low_priority_actions": len([a for a in state.get("action_items", []) if a.get("priority") == "low"]),
                "total_rules": len(state.get("extracted_rules", [])),
                "issues": state.get("categorized_issues", []),
                "ideas": state.get("improvement_ideas", []),
                "actions": state.get("action_items", []),
                "rules": state.get("extracted_rules", [])
            }

            # Use LLM to generate executive summary and strategic recommendations
            print("\n🤖 Calling LLM to generate executive retrospective summary...")
            llm = self._llm(temperature=0.7)

            # Prepare data for LLM
            summary_data = json.dumps({
                "issues": retro_summary["issues"][:3],  # Top 3 issues
                "ideas": retro_summary["ideas"][:3],    # Top 3 ideas
                "actions": retro_summary["actions"][:3], # Top 3 actions
                "metrics": {
                    "total_feedback": retro_summary["total_feedback"],
                    "total_issues": retro_summary["total_issues"],
                    "total_ideas": retro_summary["total_ideas"],
                    "total_actions": retro_summary["total_actions"]
                }
            }, indent=2, default=str)

            # Create prompt for executive summary using simple string format
            system_prompt = """You are an expert Scrum Master creating a retrospective executive summary.
Generate a comprehensive retrospective report including:
1. Sprint performance assessment
2. Key achievements and wins
3. Main challenges and learnings
4. Top 3 priorities for next sprint
5. Team health and engagement assessment
6. Strategic recommendations for continuous improvement

Respond in JSON format with keys: performance_assessment, achievements, challenges, next_priorities, team_health, strategic_recommendations"""

            human_prompt = f"Please generate an executive retrospective summary:\n\n{summary_data}"

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
                retro_summary["executive_summary"] = llm_summary
                print("✅ Executive summary generated")
            except Exception as parse_e:
                import logging
                logging.debug(f"Failed to parse LLM response: {parse_e}")
                retro_summary["executive_summary"] = {"error": str(parse_e)}

            state["retro_summary"] = retro_summary

            print(GENERATE_REPORT_SUCCESS.format(
                sprint_name=state.get("sprint_name"),
                date=state.get("date"),
                total_feedback=retro_summary["total_feedback"],
                total_issues=retro_summary["total_issues"],
                total_ideas=retro_summary["total_ideas"],
                total_actions=retro_summary["total_actions"]
            ))
        except Exception as e:
            state["error"] = ERROR_GENERATING_REPORT.format(error=str(e))
            print(GENERATE_REPORT_ERROR.format(error=state['error']))

        return state

    def run(self, sprint_id: str, sprint_name: str, date: Optional[str] = None, project_id: Optional[str] = None) -> dict:
        """Run retrospective workflow.

        Args:
            sprint_id: Sprint ID
            sprint_name: Sprint name
            date: Date for retrospective (optional, defaults to today)
            project_id: Project ID for rule storage (optional, defaults to 'project-001')

        Returns:
            dict: Retrospective summary with status
        """
        start_time = time.time()

        try:
            # Prepare initial state
            initial_state: RetroState = {
                "sprint_id": sprint_id,
                "sprint_name": sprint_name,
                "date": date or datetime.now().isoformat(),
                "project_id": project_id or "project-001",
                "po_feedback": None,
                "dev_feedback": None,
                "tester_feedback": None,
                "all_feedback": None,
                "categorized_issues": None,
                "improvement_ideas": None,
                "action_items": None,
                "extracted_rules": None,
                "retro_summary": None,
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
            retro_summary = final_state.get("retro_summary")
            execution_time = time.time() - start_time

            if retro_summary:
                # Log successful execution
                if self.langfuse_handler:
                    try:
                        from ...utils.langfuse_utils import log_node_execution
                        log_node_execution(
                            node_name="retro_coordinator_workflow",
                            agent_type="retro_coordinator",
                            execution_time=execution_time,
                            output_data={
                                "status": "success",
                                "total_feedback": retro_summary.get("total_feedback", 0),
                                "total_issues": retro_summary.get("total_issues", 0),
                                "total_ideas": retro_summary.get("total_ideas", 0),
                                "total_actions": retro_summary.get("total_actions", 0)
                            }
                        )
                    except Exception as e:
                        import logging
                        logging.debug(f"Failed to log node execution: {e}")

                return {
                    "status": "success",
                    "retro_summary": retro_summary
                }
            else:
                # Log error
                if self.langfuse_handler:
                    try:
                        from ...utils.langfuse_utils import log_node_execution
                        log_node_execution(
                            node_name="retro_coordinator_workflow",
                            agent_type="retro_coordinator",
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
                        node_name="retro_coordinator_workflow",
                        agent_type="retro_coordinator",
                        execution_time=execution_time,
                        error=str(e)
                    )
                except Exception as log_e:
                    import logging
                    logging.debug(f"Failed to log error: {log_e}")

            print(ERROR_RETRO_COORDINATOR.format(error=str(e)))
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e)
            }


def create_retro_coordinator_agent(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> RetroCoordinatorAgent:
    """Create and return a Retro Coordinator Agent instance.

    Args:
        session_id: Session ID for tracing
        user_id: User ID for tracking

    Returns:
        RetroCoordinatorAgent instance
    """
    return RetroCoordinatorAgent(session_id=session_id, user_id=user_id)


if __name__ == "__main__":
    """Direct test of Retro Coordinator Agent."""

    print("=" * 80)
    print("🚀 RETRO COORDINATOR AGENT - DIRECT TEST")
    print("=" * 80)
    print()

    # Step 1: Initialize agent
    print("📌 Step 1: Initializing Retro Coordinator Agent...")
    try:
        agent = create_retro_coordinator_agent(
            session_id="retro-test-session-001",
            user_id="test-user-001"
        )
        print("✅ Agent initialized successfully")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 2: Prepare test data
    print("📌 Step 2: Preparing test data...")
    sprint_id = "SPRINT-2024-Q1-001"
    sprint_name = "Sprint 1"
    date = datetime.now().isoformat()
    print(f"   Sprint ID: {sprint_id}")
    print(f"   Sprint Name: {sprint_name}")
    print(f"   Date: {date}")
    print("✅ Test data prepared")
    print()

    # Step 3: Run retrospective
    print("📌 Step 3: Running Retro Coordinator Agent workflow...")
    print("   This will execute all 7 nodes:")
    print("   1. CollectPOFeedback - Collect PO feedback")
    print("   2. CollectDevFeedback - Collect developer feedback")
    print("   3. CollectTesterFeedback - Collect tester feedback")
    print("   4. CategorizeIssues - Categorize feedback into issues")
    print("   5. GenerateImprovementIdeas - Generate improvement ideas")
    print("   6. DefineActionItems - Define action items for next sprint")
    print("   7. GenerateSummaryReport - Generate final retrospective report")
    print()

    try:
        result = agent.run(
            sprint_id=sprint_id,
            sprint_name=sprint_name,
            date=date
        )
    except Exception as e:
        print(f"❌ Error running retrospective: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 4: Display results
    print()
    print("=" * 80)
    print("📊 RETRO COORDINATOR AGENT - TEST RESULTS")
    print("=" * 80)
    print()

    if result.get("status") == "success":
        print("✅ Retro Coordinator Agent executed successfully!")
        print()

        summary = result.get("retro_summary", {})

        # Display summary
        print("📋 Retrospective Summary:")
        print(f"   Sprint: {summary.get('sprint_name')}")
        print(f"   Date: {summary.get('date')}")
        print(f"   Total Feedback: {summary.get('total_feedback', 0)}")
        print(f"   Total Issues: {summary.get('total_issues', 0)}")
        print(f"   Total Ideas: {summary.get('total_ideas', 0)}")
        print(f"   Total Actions: {summary.get('total_actions', 0)}")
        print()

        # Display feedback breakdown
        print("📊 Feedback Breakdown:")
        print(f"   - From PO: {summary.get('po_feedback_count', 0)}")
        print(f"   - From Devs: {summary.get('dev_feedback_count', 0)}")
        print(f"   - From Testers: {summary.get('tester_feedback_count', 0)}")
        print()

        # Display issues breakdown
        print("🚨 Issues:")
        print(f"   Total: {summary.get('total_issues', 0)}")
        print(f"   High Severity: {summary.get('high_severity_issues', 0)}")
        print(f"   Medium Severity: {summary.get('medium_severity_issues', 0)}")
        print(f"   Low Severity: {summary.get('low_severity_issues', 0)}")
        print()

        # Display ideas breakdown
        print("💡 Improvement Ideas:")
        print(f"   Total: {summary.get('total_ideas', 0)}")
        print(f"   High Priority: {summary.get('high_priority_ideas', 0)}")
        print(f"   Medium Priority: {summary.get('medium_priority_ideas', 0)}")
        print(f"   Low Priority: {summary.get('low_priority_ideas', 0)}")
        print()

        # Display actions breakdown
        print("✅ Action Items:")
        print(f"   Total: {summary.get('total_actions', 0)}")
        print(f"   High Priority: {summary.get('high_priority_actions', 0)}")
        print(f"   Medium Priority: {summary.get('medium_priority_actions', 0)}")
        print(f"   Low Priority: {summary.get('low_priority_actions', 0)}")
        print()

        # Display detailed data if available
        issues = summary.get("issues", [])
        if issues:
            print("📋 Sample Issues:")
            for i, issue in enumerate(issues[:2], 1):
                print(f"   {i}. {issue.get('description', 'N/A')}")
                print(f"      - Severity: {issue.get('severity')}")
                print(f"      - Frequency: {issue.get('frequency')}")
            print()

        ideas = summary.get("ideas", [])
        if ideas:
            print("💡 Sample Ideas:")
            for i, idea in enumerate(ideas[:2], 1):
                print(f"   {i}. {idea.get('title', 'N/A')}")
                print(f"      - Priority: {idea.get('priority')}")
                print(f"      - Effort: {idea.get('effort_estimate')}")
            print()

        actions = summary.get("actions", [])
        if actions:
            print("✅ Sample Actions:")
            for i, action in enumerate(actions[:2], 1):
                print(f"   {i}. {action.get('title', 'N/A')}")
                print(f"      - Owner: {action.get('owner')}")
                print(f"      - Priority: {action.get('priority')}")
            print()

    else:
        print(f"❌ Retro Coordinator Agent encountered an error!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        print()

    print("=" * 80)
    print("✅ TEST COMPLETED")
    print("=" * 80)

