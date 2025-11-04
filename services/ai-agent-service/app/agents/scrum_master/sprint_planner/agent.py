"""Sprint Planner Agent - Enrich and Verify sprint planning data."""

import json
import os
import re
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

# Try to import state - handle both relative and absolute imports
try:
    from .state import SprintPlannerState, ValidationIssue, EnrichedItem
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    app_path = Path(__file__).parent
    sys.path.insert(0, str(app_path))
    from state import SprintPlannerState, ValidationIssue, EnrichedItem

# Try to import agents - handle both relative and absolute imports
try:
    from ...developer.developer_agent import DeveloperAgent
    from ...tester.tester_agent import TesterAgent
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    app_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(app_path))
    from developer.developer_agent import DeveloperAgent
    from tester.tester_agent import TesterAgent

# Try to import prompts - handle both relative and absolute imports
try:
    from templates.prompts.scrum_master.sprint_planner import (
        ENRICH_VALIDATION_PROMPT,
        VERIFY_VALIDATION_PROMPT,
        FEEDBACK_PROMPT,
    )
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    app_path = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(app_path))
    from templates.prompts.scrum_master.sprint_planner import (
        ENRICH_VALIDATION_PROMPT,
        VERIFY_VALIDATION_PROMPT,
        FEEDBACK_PROMPT,
    )

load_dotenv()


class SprintPlannerAgent:
    """Sprint Planner Agent - Enrich and verify sprint planning data.

    Workflow:
    1. enrich: Load backlog.json and sprint.json, validate and enrich data
    2. verify: Verify enriched data, if issues found ask user for feedback
    """

    def __init__(self, session_id: Optional[str] = None, user_id: Optional[str] = None):
        """Initialize Sprint Planner Agent.

        Args:
            session_id: Session ID (optional)
            user_id: User ID (optional)
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
                agent_type="sprint_planner",
                additional_data={"session_id": session_id, "user_id": user_id}
            )
            self.langfuse_handler = initialize_langfuse_handler(
                session_id=session_id,
                user_id=user_id,
                agent_type="sprint_planner",
                metadata=metadata
            )
        except Exception as e:
            import logging
            logging.warning(f"Failed to initialize LangFuse handler: {e}")
            self.langfuse_handler = None

        self.graph = self._build_graph()

    def _llm(self, model: str = "gpt-4o-mini", temperature: float = 0.1) -> ChatOpenAI:
        """Initialize LLM instance with low temperature for structured output.

        Args:
            model: Model name (default: gpt-4o-mini)
            temperature: Temperature for LLM (default: 0.1 for deterministic output)

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
            print(f"[ERROR] Failed to initialize LLM: {e}")
            raise

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow."""
        graph_builder = StateGraph(SprintPlannerState)

        # Add nodes
        graph_builder.add_node("initialize", self.initialize)
        graph_builder.add_node("enrich", self.enrich)
        graph_builder.add_node("verify", self.verify)
        graph_builder.add_node("assign_to_dev", self.assign_to_dev)
        graph_builder.add_node("assign_to_tester", self.assign_to_tester)
        graph_builder.add_node("push_to_kanban", self.push_to_kanban)

        # Add edges
        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "enrich")
        graph_builder.add_edge("enrich", "verify")
        graph_builder.add_conditional_edges(
            "verify",
            self.verify_branch,
            {
                "assign_to_dev": "assign_to_dev",
                "enrich": "enrich",
                "__end__": END
            }
        )
        graph_builder.add_edge("assign_to_dev", "assign_to_tester")
        graph_builder.add_edge("assign_to_tester", "push_to_kanban")
        graph_builder.add_edge("push_to_kanban", END)

        checkpointer = MemorySaver()
        return graph_builder.compile(checkpointer=checkpointer)

    def initialize(self, state: SprintPlannerState) -> SprintPlannerState:
        """Initialize - Load backlog.json and sprint.json."""
        print("\n" + "="*80)
        print("[*] INITIALIZE - LOAD DATA")
        print("="*80)

        try:
            # Get base path
            base_path = Path(__file__).parent.parent
            backlog_path = base_path / "backlog.json"
            sprint_path = base_path / "sprint.json"

            # Load backlog items
            if backlog_path.exists():
                with open(backlog_path, 'r', encoding='utf-8') as f:
                    state.backlog_items = json.load(f)
                print(f"[+] Loaded {len(state.backlog_items)} backlog items")
            else:
                print(f"[!] Backlog file not found: {backlog_path}")

            # Load sprints
            if sprint_path.exists():
                with open(sprint_path, 'r', encoding='utf-8') as f:
                    state.sprints = json.load(f)
                print(f"[+] Loaded {len(state.sprints)} sprints")
            else:
                print(f"[!] Sprint file not found: {sprint_path}")

            state.status = "initialized"
            state.total_items = len(state.backlog_items)
            state.total_sprints = len(state.sprints)

            print("="*80 + "\n")
            return state

        except Exception as e:
            print(f"[ERROR] Error during initialization: {e}")
            state.status = "error"
            state.error_message = str(e)
            return state

    def enrich(self, state: SprintPlannerState) -> SprintPlannerState:
        """Enrich - Validate and enrich backlog items and sprints using LLM."""
        print("\n" + "="*80)
        print(f"[*] ENRICH - VALIDATE & ENRICH DATA (Loop {state.current_loop + 1}/{state.max_loops})")
        print("="*80)

        state.current_loop += 1

        try:
            # Prepare data for LLM
            backlog_json = json.dumps(state.backlog_items, indent=2, ensure_ascii=False)
            sprints_json = json.dumps(state.sprints, indent=2, ensure_ascii=False)
            current_issues_json = json.dumps(
                [issue.model_dump() for issue in state.validation_issues],
                indent=2,
                ensure_ascii=False
            )

            # Format prompt
            prompt = ENRICH_VALIDATION_PROMPT.format(
                backlog_items=backlog_json,
                sprints=sprints_json,
                current_issues=current_issues_json
            )

            # Call LLM with low temperature for deterministic output
            print("\n[*] Calling LLM to validate and enrich data...")
            llm = self._llm(temperature=0.1)
            response = llm.invoke([HumanMessage(content=prompt)])

            # Parse JSON response
            response_text = response.content.strip()

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            # Remove trailing commas and comments
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            response_text = re.sub(r'//.*?$', '', response_text, flags=re.MULTILINE)

            result_dict = json.loads(response_text)

            # Parse validation issues
            issues = []
            for issue_data in result_dict.get("validation_issues", []):
                issue = ValidationIssue(**issue_data)
                issues.append(issue)

            # Parse enriched items from LLM (batch processing)
            enrichments_map = {}
            for enriched_item_data in result_dict.get("enriched_items", []):
                item_id = enriched_item_data.get("item_id")
                enrichments_map[item_id] = enriched_item_data.get("enriched_fields", {})

            # Create enriched items with LLM-filled fields
            enriched_items = []
            for item in state.backlog_items:
                item_id = item.get("id")
                item_issues = [i for i in issues if i.item_id == item_id]

                # Apply enrichments from LLM (auto-fill null fields)
                enriched_data = {**item}
                if item_id in enrichments_map:
                    # LLM filled null/empty fields
                    enriched_data.update(enrichments_map[item_id])

                enriched = EnrichedItem(
                    **{k: v for k, v in enriched_data.items() if k in EnrichedItem.model_fields},
                    is_valid=len(item_issues) == 0,
                    validation_issues=item_issues
                )
                enriched_items.append(enriched)

            state.enriched_items = enriched_items
            state.validation_issues = issues
            state.total_issues = len(issues)
            state.critical_issues_count = len([i for i in issues if i.severity == "critical"])

            # Print summary
            print(f"\n[*] Validation Summary:")
            print(f"   Total Items: {len(enriched_items)}")
            print(f"   Total Issues: {len(issues)}")
            print(f"   Critical Issues: {state.critical_issues_count}")

            if issues:
                print(f"\n[!] Issues Found:")
                for issue in issues[:10]:
                    print(f"   [{issue.severity.upper()}] {issue.item_id}: {issue.message}")
                if len(issues) > 10:
                    print(f"   ... and {len(issues) - 10} more")

            state.status = "enriched"

        except Exception as e:
            print(f"[ERROR] Error during enrich: {e}")
            import traceback
            traceback.print_exc()
            state.status = "error"
            state.error_message = str(e)

        print("="*80 + "\n")
        return state

    def verify(self, state: SprintPlannerState) -> SprintPlannerState:
        """Verify - Check if data is valid using LLM."""
        print("\n" + "="*80)
        print("[+] VERIFY - CHECK DATA VALIDITY")
        print("="*80)

        try:
            # Prepare data for LLM
            enriched_items_json = json.dumps(
                [item.model_dump() for item in state.enriched_items],
                indent=2,
                ensure_ascii=False
            )
            validation_issues_json = json.dumps(
                [issue.model_dump() for issue in state.validation_issues],
                indent=2,
                ensure_ascii=False
            )
            sprints_json = json.dumps(state.sprints, indent=2, ensure_ascii=False)

            # Format prompt
            prompt = VERIFY_VALIDATION_PROMPT.format(
                enriched_items=enriched_items_json,
                validation_issues=validation_issues_json,
                sprints=sprints_json
            )

            # Call LLM with low temperature
            print("\n[*] Calling LLM to verify data validity...")
            llm = self._llm(temperature=0.1)
            response = llm.invoke([HumanMessage(content=prompt)])

            # Parse JSON response
            response_text = response.content.strip()

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            # Remove trailing commas and comments
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            response_text = re.sub(r'//.*?$', '', response_text, flags=re.MULTILINE)

            result_dict = json.loads(response_text)

            # Extract verification results
            state.is_valid = result_dict.get("is_valid", False)
            state.verification_passed = result_dict.get("can_proceed", False)
            readiness_score = result_dict.get("readiness_score", 0)

            # Print verification summary
            print(f"\n[*] Verification Summary:")
            print(f"   Is Valid: {state.is_valid}")
            print(f"   Can Proceed: {state.verification_passed}")
            print(f"   Readiness Score: {readiness_score:.2f}")
            print(f"   Critical Issues: {result_dict.get('critical_issues_count', 0)}")

            if not state.verification_passed:
                blocking_issues = result_dict.get("blocking_issues", [])
                if blocking_issues:
                    print(f"\n[X] Blocking Issues:")
                    for issue in blocking_issues[:5]:
                        print(f"   - {issue}")
                    if len(blocking_issues) > 5:
                        print(f"   ... and {len(blocking_issues) - 5} more")
                print(f"\n[!] Readiness Score {readiness_score:.2f} < 0.75, need more enrichment")
                state.status = "verification_failed"
            else:
                print(f"\n[+] Data is ready to proceed!")
                print(f"[+] Readiness Score {readiness_score:.2f} >= 0.75, proceeding to assignment")
                recommendations = result_dict.get("recommendations", [])
                if recommendations:
                    print(f"\n[*] Recommendations (can be addressed during sprint):")
                    for rec in recommendations[:3]:
                        print(f"   - {rec}")
                state.status = "verified"

        except Exception as e:
            print(f"[ERROR] Error during verify: {e}")
            import traceback
            traceback.print_exc()
            state.status = "error"
            state.error_message = str(e)
            state.verification_passed = False

        print("="*80 + "\n")
        return state

    def assign_to_dev(self, state: SprintPlannerState) -> SprintPlannerState:
        """Assign all tasks to development team using Developer Agent with project rules."""
        print("\n" + "="*80)
        print("[*] ASSIGN TO DEVELOPMENT TEAM")
        print("="*80)

        try:
            # Initialize Developer Agent
            dev_agent = DeveloperAgent(
                session_id=self.session_id,
                user_id=self.user_id
            )

            # Convert enriched items to dict for agent
            items_dict = [item.model_dump() for item in state.enriched_items]

            # Retrieve relevant project rules from knowledge base
            try:
                from ...services.rule_service import RuleService
            except ImportError:
                # Fallback for direct script execution
                import sys
                from pathlib import Path
                app_path = Path(__file__).parent.parent.parent.parent
                sys.path.insert(0, str(app_path))
                from services.rule_service import RuleService

            # Extract tags from tasks for rule retrieval
            task_tags = set()
            for item in state.enriched_items:
                task_tags.update(item.labels or [])

            # Query rules by tags
            project_id = getattr(state, 'project_id', 'project-001')
            project_rules = RuleService.get_project_rules(
                project_id=project_id,
                tags=list(task_tags) if task_tags else None,
                category="technical",
                limit=10
            )

            print(f"\n[*] Retrieved {len(project_rules)} relevant rules from knowledge base")
            if project_rules:
                for rule in project_rules[:3]:  # Show top 3
                    print(f"   - {rule.title} (Tags: {', '.join(rule.tags[:3])})")

            # Assign all tasks to development team with rules context
            result = dev_agent.assign_all_tasks(
                items_dict,
                project_rules=[r.model_dump() for r in project_rules]
            )

            state.dev_assignments = result.get("assignments", [])

            # Update enriched items with dev assignments
            for assignment in state.dev_assignments:
                for item in state.enriched_items:
                    if item.id == assignment.get("item_id"):
                        item.assigned_to_dev = assignment.get("developer_id")
                        item.dev_status = assignment.get("status", "pending")

            print(f"\n[+] Assigned {len(state.dev_assignments)} tasks to development team")
            print(f"[+] Applied {len(project_rules)} project rules to assignments")
            print("="*80 + "\n")

        except Exception as e:
            print(f"[ERROR] Error during developer assignment: {e}")
            import traceback
            traceback.print_exc()
            state.error_message = str(e)

        return state

    def assign_to_tester(self, state: SprintPlannerState) -> SprintPlannerState:
        """Assign all test tasks to testing team using Tester Agent with project rules."""
        print("\n" + "="*80)
        print("[*] ASSIGN TO TESTING TEAM")
        print("="*80)

        try:
            # Initialize Tester Agent
            tester_agent = TesterAgent(
                session_id=self.session_id,
                user_id=self.user_id
            )

            # Convert enriched items to dict for agent
            items_dict = [item.model_dump() for item in state.enriched_items]

            # Retrieve relevant project rules from knowledge base
            try:
                from ...services.rule_service import RuleService
            except ImportError:
                # Fallback for direct script execution
                import sys
                from pathlib import Path
                app_path = Path(__file__).parent.parent.parent.parent
                sys.path.insert(0, str(app_path))
                from services.rule_service import RuleService

            # Extract tags from tasks for rule retrieval
            task_tags = set()
            for item in state.enriched_items:
                task_tags.update(item.labels or [])

            # Query rules by tags (focus on quality/testing rules)
            project_id = getattr(state, 'project_id', 'project-001')
            project_rules = RuleService.get_project_rules(
                project_id=project_id,
                tags=list(task_tags) if task_tags else None,
                category="quality",
                limit=10
            )

            print(f"\n[*] Retrieved {len(project_rules)} relevant rules from knowledge base")
            if project_rules:
                for rule in project_rules[:3]:  # Show top 3
                    print(f"   - {rule.title} (Tags: {', '.join(rule.tags[:3])})")

            # Assign all test tasks to testing team with rules context
            result = tester_agent.assign_all_test_tasks(
                items_dict,
                project_rules=[r.model_dump() for r in project_rules]
            )

            state.tester_assignments = result.get("assignments", [])

            # Update enriched items with tester assignments
            for assignment in state.tester_assignments:
                for item in state.enriched_items:
                    if item.id == assignment.get("item_id"):
                        item.assigned_to_tester = assignment.get("tester_id")
                        item.test_status = assignment.get("status", "pending")

            # Final assigned items
            state.assigned_items = state.enriched_items

            print(f"\n[+] Assigned {len(state.tester_assignments)} test tasks to testing team")
            print(f"[+] Applied {len(project_rules)} project rules to assignments")
            print("="*80 + "\n")

        except Exception as e:
            print(f"[ERROR] Error during tester assignment: {e}")
            import traceback
            traceback.print_exc()
            state.error_message = str(e)

        return state

    def push_to_kanban(self, state: SprintPlannerState) -> SprintPlannerState:
        """Push all assigned items to Kanban board."""
        print("\n" + "="*80)
        print("[*] PUSH TO KANBAN BOARD")
        print("="*80)

        try:
            if not state.assigned_items:
                print("[!] No assigned items to push to kanban")
                state.kanban_push_status = "no_items"
                return state

            # Prepare kanban cards from assigned items
            kanban_cards = []
            for item in state.assigned_items:
                card = {
                    "id": item.id,
                    "title": item.title,
                    "type": item.type,
                    "status": "To Do",
                    "assigned_to_dev": item.assigned_to_dev,
                    "assigned_to_tester": item.assigned_to_tester,
                    "story_point": item.story_point,
                    "estimate_value": item.estimate_value,
                    "business_value": item.business_value,
                    "acceptance_criteria": item.acceptance_criteria,
                    "dependencies": item.dependencies,
                    "labels": item.labels,
                }
                kanban_cards.append(card)

            # Log kanban push
            print(f"\n[+] Pushing {len(kanban_cards)} items to kanban board")
            for card in kanban_cards[:5]:  # Show first 5
                print(f"   - {card['id']}: {card['title']}")
            if len(kanban_cards) > 5:
                print(f"   ... and {len(kanban_cards) - 5} more")

            # Store kanban cards in state
            state.kanban_cards = kanban_cards
            state.kanban_push_status = "success"

            print(f"\n[+] Successfully prepared {len(kanban_cards)} kanban cards")
            print("="*80 + "\n")

        except Exception as e:
            print(f"[ERROR] Error during kanban push: {e}")
            import traceback
            traceback.print_exc()
            state.error_message = str(e)
            state.kanban_push_status = "error"

        return state

    def verify_branch(self, state: SprintPlannerState) -> str:
        """Branch after verify node.

        Decision logic:
        - If verification_passed: proceed to assign_to_dev (MANDATORY)
        - If verification_failed AND current_loop < max_loops: go back to enrich
        - If verification_failed AND current_loop >= max_loops: end (don't proceed)
        """
        print(f"\n[*] VERIFY_BRANCH DECISION:")
        print(f"   verification_passed: {state.verification_passed}")
        print(f"   current_loop: {state.current_loop}")
        print(f"   max_loops: {state.max_loops}")

        if state.verification_passed:
            print(f"   [+] DECISION: Go to assign_to_dev (MANDATORY)")
            return "assign_to_dev"
        elif state.current_loop < state.max_loops:
            print(f"   [!] DECISION: Go back to enrich (loop {state.current_loop + 1}/{state.max_loops})")
            return "enrich"
        else:
            print(f"   [!] DECISION: End workflow (max loops reached)")
            print(f"\n[!] Max enrichment loops ({state.max_loops}) reached")
            print(f"[!] Verification failed, cannot proceed to assignment")
            return "__end__"

    def run(self, user_input: Optional[str] = None):
        """Run the sprint planner workflow."""
        start_time = time.time()

        config = {
            "configurable": {
                "thread_id": self.session_id or "default"
            }
        }

        initial_state = SprintPlannerState()

        # Add LangFuse handler to config if available
        if self.langfuse_handler:
            config["callbacks"] = [self.langfuse_handler]

        try:
            # Stream the workflow
            for output in self.graph.stream(initial_state, config=config):
                pass

            # Get final state
            final_state = self.graph.get_state(config).values

            # Log execution time
            execution_time = time.time() - start_time
            if self.langfuse_handler:
                try:
                    from ...utils.langfuse_utils import log_node_execution
                    log_node_execution(
                        node_name="sprint_planner_workflow",
                        agent_type="sprint_planner",
                        execution_time=execution_time,
                        output_data={"status": "success", "items_count": len(final_state.get("assigned_items", []))}
                    )
                except Exception as e:
                    import logging
                    logging.debug(f"Failed to log node execution: {e}")

            return final_state

        except Exception as e:
            execution_time = time.time() - start_time
            if self.langfuse_handler:
                try:
                    from ...utils.langfuse_utils import log_node_execution
                    log_node_execution(
                        node_name="sprint_planner_workflow",
                        agent_type="sprint_planner",
                        execution_time=execution_time,
                        error=str(e)
                    )
                except Exception as log_e:
                    import logging
                    logging.debug(f"Failed to log error: {log_e}")
            raise


if __name__ == "__main__":
    """Test Sprint Planner Agent."""
    print("\n" + "="*80)
    print("[*] TESTING SPRINT PLANNER AGENT")
    print("="*80)

    try:
        # Initialize agent
        print("\n[*] Initializing Sprint Planner Agent...")
        agent = SprintPlannerAgent(
            session_id="test-session-001",
            user_id="test-user-001"
        )
        print("[+] Agent initialized successfully")

        # Run workflow
        print("\n[*] Running Sprint Planner workflow...")
        result = agent.run()

        # Convert dict to object if needed
        if isinstance(result, dict):
            from types import SimpleNamespace
            result = SimpleNamespace(**result)

        # Print results
        print("\n" + "="*80)
        print("[*] SPRINT PLANNER RESULTS")
        print("="*80)

        print(f"\n[+] Status: {result.status}")
        print(f"[+] Is Valid: {result.is_valid}")
        print(f"[+] Verification Passed: {result.verification_passed}")
        print(f"[+] Total Items: {result.total_items}")
        print(f"[+] Total Sprints: {result.total_sprints}")
        print(f"[+] Total Issues: {result.total_issues}")
        print(f"[+] Critical Issues: {result.critical_issues_count}")

        # Print enriched items summary
        if result.enriched_items:
            print(f"\n[*] Enriched Items ({len(result.enriched_items)} items):")
            for item in result.enriched_items[:5]:
                item_obj = item if hasattr(item, 'id') else SimpleNamespace(**item) if isinstance(item, dict) else item
                print(f"   - {item_obj.id}: {item_obj.title} (Valid: {item_obj.is_valid})")
            if len(result.enriched_items) > 5:
                print(f"   ... and {len(result.enriched_items) - 5} more")

        # Print validation issues
        if result.validation_issues:
            print(f"\n[!] Validation Issues ({len(result.validation_issues)} issues):")
            critical = [i for i in result.validation_issues if (i.severity if hasattr(i, 'severity') else i.get('severity')) == "critical"]
            high = [i for i in result.validation_issues if (i.severity if hasattr(i, 'severity') else i.get('severity')) == "high"]
            medium = [i for i in result.validation_issues if (i.severity if hasattr(i, 'severity') else i.get('severity')) == "medium"]
            low = [i for i in result.validation_issues if (i.severity if hasattr(i, 'severity') else i.get('severity')) == "low"]

            if critical:
                print(f"   [CRITICAL] {len(critical)}")
                for issue in critical[:3]:
                    item_id = issue.item_id if hasattr(issue, 'item_id') else issue.get('item_id')
                    message = issue.message if hasattr(issue, 'message') else issue.get('message')
                    print(f"      - {item_id}: {message}")
            if high:
                print(f"   [HIGH] {len(high)}")
                for issue in high[:3]:
                    item_id = issue.item_id if hasattr(issue, 'item_id') else issue.get('item_id')
                    message = issue.message if hasattr(issue, 'message') else issue.get('message')
                    print(f"      - {item_id}: {message}")
            if medium:
                print(f"   [MEDIUM] {len(medium)}")
            if low:
                print(f"   [LOW] {len(low)}")
        else:
            print(f"\n[+] No validation issues found!")

        # Print error if any
        if hasattr(result, 'error_message') and result.error_message:
            print(f"\n[ERROR] {result.error_message}")

        print("\n" + "="*80)
        print("[+] TEST COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*80 + "\n")
