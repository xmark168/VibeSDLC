"""Priority Agent - Tạo Sprint Plan từ Product Backlog."""

import json
import os
import re
from typing import Any, Literal, Optional
from datetime import datetime, timedelta

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from templates.prompts.product_owner.priority import CALCULATE_PRIORITY_PROMPT


load_dotenv()


# ============================================================================
# Pydantic Models for State Management
# ============================================================================

class WSJFScore(BaseModel):
    """Model cho WSJF score của một item."""
    item_id: str = Field(description="ID của item")
    business_value: int = Field(description="Business Value score (1-10)", ge=1, le=10)
    time_criticality: int = Field(description="Time Criticality score (1-10)", ge=1, le=10)
    risk_reduction: int = Field(description="Risk Reduction score (1-10)", ge=1, le=10)
    job_size: int = Field(description="Job Size (1-13 Fibonacci)", ge=1, le=13)
    reasoning: str = Field(description="Lý do scoring")


class WSJFOutput(BaseModel):
    """Structured output cho WSJF scoring."""
    wsjf_scores: list[WSJFScore] = Field(description="Danh sách WSJF scores")


class Sprint(BaseModel):
    """Model cho một Sprint."""
    sprint_id: str = Field(description="ID: sprint-1, sprint-2, ...")
    sprint_number: int = Field(description="Số thứ tự sprint (1, 2, 3, ...)")
    sprint_goal: str = Field(description="Mục tiêu chính của sprint")
    start_date: Optional[str] = Field(default=None, description="Ngày bắt đầu (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="Ngày kết thúc (YYYY-MM-DD)")
    velocity_plan: int = Field(default=0, description="Planned velocity (story points)")
    velocity_actual: int = Field(default=0, description="Actual velocity (story points)")
    assigned_items: list[str] = Field(default_factory=list, description="IDs của items được assign")
    status: Literal["Planned", "Active", "Completed"] = Field(default="Planned")


class PriorityState(BaseModel):
    """State cho Priority Agent workflow."""
    # Input
    product_backlog: dict = Field(
        default_factory=dict,
        description="Product Backlog từ Backlog Agent (metadata + items)"
    )

    # Configuration
    sprint_duration_weeks: int = Field(
        default=2,
        description="Độ dài mỗi sprint (tuần) - sprint cycle for review/demo"
    )
    sprint_capacity_story_points: int = Field(
        default=30,
        description="Max story points per sprint (AI throughput limit for review process)"
    )

    # Calculate Priority Outputs
    prioritized_backlog: list[dict] = Field(
        default_factory=list,
        description="Backlog items đã được prioritize (có rank field)"
    )
    wsjf_calculations: dict = Field(
        default_factory=dict,
        description="WSJF calculations cho từng item {item_id: wsjf_data}"
    )

    # ========================================================================
    # Plan Sprints Outputs
    # ========================================================================
    sprints: list[dict] = Field(
        default_factory=list,
        description="Danh sách sprints với assigned items"
    )

    # ========================================================================
    # Evaluate Outputs
    # ========================================================================
    capacity_issues: list[dict] = Field(
        default_factory=list,
        description="Issues về capacity (overload, underload)"
    )
    dependency_issues: list[dict] = Field(
        default_factory=list,
        description="Issues về dependencies (sprint order conflicts)"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations để cải thiện sprint plan"
    )
    readiness_score: float = Field(
        default=0.0,
        description="Điểm readiness của sprint plan (0.0-1.0)"
    )
    can_proceed: bool = Field(
        default=False,
        description="Sprint plan có đạt yêu cầu để finalize không"
    )

    # Loop Control
    max_loops: int = Field(
        default=1,
        description="Số lần refine tối đa"
    )
    current_loop: int = Field(
        default=0,
        description="Số lần refine hiện tại"
    )

    # ========================================================================
    # Preview & User Approval
    # ========================================================================
    user_approval: Optional[str] = Field(
        default=None,
        description="User choice: 'approve', 'edit', hoặc 'reprioritize'"
    )
    user_feedback: Optional[str] = Field(
        default=None,
        description="Lý do/yêu cầu chỉnh sửa từ user"
    )

    # Final Output
    sprint_plan: dict = Field(
        default_factory=dict,
        description="Final sprint plan (metadata + prioritized_backlog + sprints)"
    )
    status: str = Field(
        default="initial",
        description="Trạng thái workflow"
    )


# ============================================================================
# Priority Agent Class
# ============================================================================

class PriorityAgent:
    """Priority Agent - Tạo Sprint Plan từ Product Backlog.

    Workflow:
    1. initialize: Load product backlog từ Backlog Agent
    2. calculate_priority: Tính WSJF scores và rank items
    3. plan_sprints: Pack items vào sprints với capacity planning
    4. evaluate: Validate sprint plan
    5. refine (if needed): Adjust sprint assignments
    6. finalize: Finalize sprint plan
    7. preview: Human-in-the-loop approval
    """

    def __init__(self, session_id: str | None = None, user_id: str | None = None):
        """Khởi tạo Priority Agent.

        Args:
            session_id: Session ID tùy chọn
            user_id: User ID tùy chọn
        """
        self.session_id = session_id
        self.user_id = user_id

        # Initialize Langfuse callback handler
        self.langfuse_handler = CallbackHandler()

        self.graph = self._build_graph()

    def _llm(self, model: str, temperature: float) -> ChatOpenAI:
        """Initialize LLM instance."""
        try:
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
            )
            return llm
        except Exception:
            return None

    def _build_graph(self) -> StateGraph:
        """Xây dựng LangGraph workflow theo sơ đồ Priority Agent."""
        graph_builder = StateGraph(PriorityState)

        # Add nodes
        graph_builder.add_node("initialize", self.initialize)
        graph_builder.add_node("calculate_priority", self.calculate_priority)
        graph_builder.add_node("plan_sprints", self.plan_sprints)
        graph_builder.add_node("evaluate", self.evaluate)
        graph_builder.add_node("refine", self.refine)
        graph_builder.add_node("finalize", self.finalize)
        graph_builder.add_node("preview", self.preview)

        # Add edges
        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "calculate_priority")
        graph_builder.add_edge("calculate_priority", "plan_sprints")
        # graph_builder.add_edge("plan_sprints", "evaluate")
        # graph_builder.add_conditional_edges("evaluate", self.evaluate_branch)
        # graph_builder.add_edge("refine", "plan_sprints")  # refine → plan_sprints
        # graph_builder.add_edge("finalize", "preview")
        # graph_builder.add_conditional_edges("preview", self.preview_branch)

        checkpointer = MemorySaver()
        return graph_builder.compile(checkpointer=checkpointer)

    # ========================================================================
    # Nodes (to be implemented)
    # ========================================================================

    def initialize(self, state: PriorityState) -> PriorityState:
        """Initialize - Load và validate product backlog.

        Tasks:
        1. Validate product_backlog structure (metadata + items)
        2. Validate items có đúng format (type, id, title, description)
        3. Count số lượng items theo type (Epic, User Story, Task, Sub-task)
        4. Set status = "initialized"
        """
        print("\n" + "="*80)
        print("🔧 INITIALIZE NODE - Load & Validate Product Backlog")
        print("="*80)

        # Validate product_backlog structure
        if not state.product_backlog:
            raise ValueError("❌ product_backlog is empty")

        if "metadata" not in state.product_backlog:
            raise ValueError("❌ product_backlog missing 'metadata' key")

        if "items" not in state.product_backlog:
            raise ValueError("❌ product_backlog missing 'items' key")

        metadata = state.product_backlog["metadata"]
        items = state.product_backlog["items"]

        print(f"\n📦 Product: {metadata.get('product_name', 'N/A')}")
        print(f"📌 Version: {metadata.get('version', 'N/A')}")
        print(f"📊 Total Items: {len(items)}")

        # Validate items
        if not items or len(items) == 0:
            raise ValueError("❌ product_backlog.items is empty")

        # Count items by type
        type_counts = {
            "Epic": 0,
            "User Story": 0,
            "Task": 0,
            "Sub-task": 0
        }

        invalid_items = []
        for item in items:
            # Validate required fields
            if "id" not in item:
                invalid_items.append(f"Item missing 'id': {item}")
                continue

            if "type" not in item:
                invalid_items.append(f"Item {item.get('id')} missing 'type'")
                continue

            if item["type"] not in type_counts:
                invalid_items.append(f"Item {item.get('id')} has invalid type: {item['type']}")
                continue

            if "title" not in item or not item["title"]:
                invalid_items.append(f"Item {item.get('id')} missing 'title'")
                continue

            if "description" not in item or not item["description"]:
                invalid_items.append(f"Item {item.get('id')} missing 'description'")
                continue

            # Count by type
            type_counts[item["type"]] += 1

        # Report validation results
        if invalid_items:
            print(f"\n⚠️  Found {len(invalid_items)} invalid items:")
            for invalid in invalid_items[:5]:  # Show first 5
                print(f"  - {invalid}")
            if len(invalid_items) > 5:
                print(f"  ... and {len(invalid_items) - 5} more")
            raise ValueError(f"❌ Product backlog contains {len(invalid_items)} invalid items")

        # Print type counts
        print(f"\n📈 Items by Type:")
        print(f"  - Epics: {type_counts['Epic']}")
        print(f"  - User Stories: {type_counts['User Story']}")
        print(f"  - Tasks: {type_counts['Task']}")
        print(f"  - Sub-tasks: {type_counts['Sub-task']}")

        # Validate có ít nhất Epic hoặc User Story để prioritize
        if type_counts["Epic"] == 0 and type_counts["User Story"] == 0:
            raise ValueError("❌ Product backlog must contain at least one Epic or User Story")

        print(f"\n✅ Product backlog validated successfully")
        print(f"✅ Ready to calculate priority for {type_counts['Epic']} Epics and {type_counts['User Story']} User Stories")

        # Update state
        state.status = "initialized"

        return state

    def calculate_priority(self, state: PriorityState) -> PriorityState:
        """Calculate Priority - Tính WSJF và rank items.

        Tasks:
        1. Extract Epic và User Story từ product_backlog
        2. Dùng LLM để analyze business_value và score WSJF factors
        3. Calculate WSJF = (BV + TC + RR) / Job Size
        4. Rank items theo WSJF (cao → thấp)
        5. Update prioritized_backlog với rank
        """
        print("\n" + "="*80)
        print("📊 CALCULATE PRIORITY NODE - Tính WSJF & Rank Items")
        print("="*80)

        items = state.product_backlog.get("items", [])
        if not items:
            print("⚠️  No items to prioritize")
            state.status = "error_no_items"
            return state

        # Filter Epic, User Story, và Task (chỉ prioritize 3 loại này, không rank Sub-task)
        prioritizable_items = [
            item for item in items
            if item.get("type") in ["Epic", "User Story", "Task"]
        ]

        print(f"\n📋 Items to Prioritize:")
        print(f"   - Total items: {len(items)}")
        print(f"   - Epics + User Stories + Tasks: {len(prioritizable_items)}")
        print(f"   - Sub-tasks (not prioritized): {len([i for i in items if i.get('type') == 'Sub-task'])}")

        if not prioritizable_items:
            print("⚠️  No Epic, User Story, or Task to prioritize")
            state.status = "error_no_prioritizable_items"
            return state

        # Prepare prompt for LLM to score WSJF factors
        items_for_scoring = []
        for item in prioritizable_items:
            items_for_scoring.append({
                "id": item.get("id"),
                "type": item.get("type"),
                "title": item.get("title"),
                "description": item.get("description"),
                "business_value": item.get("business_value"),
                "story_point": item.get("story_point"),  # for User Story
                "dependencies": item.get("dependencies", [])
            })

        # Format prompt
        prompt = CALCULATE_PRIORITY_PROMPT.format(
            product_name=state.product_backlog.get('metadata', {}).get('product_name', 'N/A'),
            items_json=json.dumps(items_for_scoring, ensure_ascii=False, indent=2)
        )

        try:
            print("\n🤖 Calling LLM to score WSJF factors...")
            llm = self._llm("gpt-4o", 0.3)

            # Use structured output with Pydantic model
            structured_llm = llm.with_structured_output(WSJFOutput)

            result = structured_llm.invoke([HumanMessage(content=prompt)])

            # result is now a WSJFOutput instance
            wsjf_scores = [score.model_dump() for score in result.wsjf_scores]

            if not wsjf_scores:
                raise ValueError("LLM returned empty wsjf_scores")

            print(f"✓ Received WSJF scores for {len(wsjf_scores)} items")

            # Calculate WSJF and store
            wsjf_calculations = {}
            items_with_wsjf = []

            for score_data in wsjf_scores:
                item_id = score_data.get("item_id")
                bv = score_data.get("business_value", 5)
                tc = score_data.get("time_criticality", 5)
                rr = score_data.get("risk_reduction", 5)
                job_size = score_data.get("job_size", 5)

                # WSJF formula
                wsjf_score = (bv + tc + rr) / job_size if job_size > 0 else 0

                wsjf_calculations[item_id] = {
                    "business_value": bv,
                    "time_criticality": tc,
                    "risk_reduction": rr,
                    "job_size": job_size,
                    "wsjf_score": round(wsjf_score, 2),
                    "reasoning": score_data.get("reasoning", "")
                }

                # Find original item
                original_item = next((i for i in items if i.get("id") == item_id), None)
                if original_item:
                    item_copy = original_item.copy()
                    item_copy["wsjf_score"] = round(wsjf_score, 2)
                    items_with_wsjf.append(item_copy)

            # Sort by WSJF (descending) and assign rank
            items_with_wsjf.sort(key=lambda x: x.get("wsjf_score", 0), reverse=True)

            prioritized_backlog = []
            for rank, item in enumerate(items_with_wsjf, start=1):
                item["rank"] = rank
                prioritized_backlog.append(item)

            # Update state
            state.wsjf_calculations = wsjf_calculations
            state.prioritized_backlog = prioritized_backlog

            # Print summary
            print(f"\n✓ Calculate Priority completed")
            print(f"\n📊 WSJF Scores & Rankings:")
            print(f"   {'Rank':<6} {'ID':<12} {'Type':<12} {'WSJF':<8} {'Title':<50}")
            print(f"   {'-'*6} {'-'*12} {'-'*12} {'-'*8} {'-'*50}")

            for item in prioritized_backlog[:10]:  # Show top 10
                print(f"   {item.get('rank', 'N/A'):<6} {item.get('id', 'N/A'):<12} {item.get('type', 'N/A'):<12} {item.get('wsjf_score', 0):<8.2f} {item.get('title', 'N/A')[:50]}")

            if len(prioritized_backlog) > 10:
                print(f"   ... and {len(prioritized_backlog) - 10} more items")

            # Show sample WSJF details
            print(f"\n📋 Sample WSJF Calculation (Top Item):")
            if prioritized_backlog:
                top_item = prioritized_backlog[0]
                top_id = top_item.get("id")
                if top_id in wsjf_calculations:
                    calc = wsjf_calculations[top_id]
                    print(f"   Item: {top_id} - {top_item.get('title', 'N/A')[:60]}")
                    print(f"   Business Value: {calc['business_value']}")
                    print(f"   Time Criticality: {calc['time_criticality']}")
                    print(f"   Risk Reduction: {calc['risk_reduction']}")
                    print(f"   Job Size: {calc['job_size']}")
                    print(f"   WSJF Score: ({calc['business_value']} + {calc['time_criticality']} + {calc['risk_reduction']}) / {calc['job_size']} = {calc['wsjf_score']}")
                    print(f"   Reasoning: {calc['reasoning'][:100]}...")

            state.status = "priority_calculated"
            print(f"\n✅ Priority calculation complete - {len(prioritized_backlog)} items ranked")

        except Exception as e:
            print(f"❌ Error calculating priority: {e}")
            import traceback
            traceback.print_exc()
            state.status = "error_calculating_priority"

        print("="*80 + "\n")
        return state

    def plan_sprints(self, state: PriorityState) -> PriorityState:
        """Plan Sprints - Pack items vào sprints với capacity planning.

        Tasks:
        1. Lấy prioritized_backlog (đã rank)
        2. Pack items vào sprints theo thứ tự rank
        3. Respect capacity (story points per sprint)
        4. Respect dependencies (không assign item trước khi dependencies xong)
        5. Calculate velocity_plan cho mỗi sprint
        6. Set sprint dates
        """
        print("\n" + "="*80)
        print("🏃 PLAN SPRINTS NODE - Pack Items into Sprints")
        print("="*80)

        prioritized_backlog = state.prioritized_backlog
        if not prioritized_backlog:
            print("⚠️  No prioritized backlog to plan")
            state.status = "error_no_prioritized_backlog"
            return state

        capacity = state.sprint_capacity_story_points
        sprint_duration_weeks = state.sprint_duration_weeks

        print(f"\n📋 Sprint Planning Configuration:")
        print(f"   - Total items to plan: {len(prioritized_backlog)}")
        print(f"   - Capacity per sprint: {capacity} story points")
        print(f"   - Sprint duration: {sprint_duration_weeks} weeks")

        # Sort by rank (should already be sorted)
        prioritized_backlog.sort(key=lambda x: x.get("rank", 999))

        # Track which items are assigned to which sprint
        item_to_sprint = {}  # {item_id: sprint_number}
        sprints = []
        sprint_num = 1
        current_sprint_items = []
        current_sprint_points = 0

        # Calculate start date (today)
        start_date = datetime.now()

        print(f"\n🔄 Packing items into sprints...")

        for item in prioritized_backlog:
            item_id = item.get("id")
            item_type = item.get("type")
            story_point = item.get("story_point", 0)
            dependencies = item.get("dependencies", [])

            # Skip Sub-tasks (they follow their parent)
            if item_type == "Sub-task":
                continue

            # Check dependencies
            can_assign = True
            unmet_deps = []

            for dep_id in dependencies:
                # Check if dependency has been assigned to a sprint
                if dep_id not in item_to_sprint:
                    # Dependency not assigned yet
                    can_assign = False
                    unmet_deps.append(dep_id)
                elif item_to_sprint[dep_id] >= sprint_num:
                    # Dependency in same or future sprint - not acceptable
                    can_assign = False
                    unmet_deps.append(dep_id)

            if not can_assign:
                print(f"   ⚠️  Skipping {item_id}: unmet dependencies {unmet_deps}")
                continue

            # Check capacity
            if item_type in ["Epic", "Task"]:
                # Epic and Task have no story_point, don't count toward capacity
                # But still assign to sprint
                current_sprint_items.append(item_id)
                item_to_sprint[item_id] = sprint_num
                print(f"   ✓ Assigned {item_id} ({item_type}) to Sprint {sprint_num}")

            elif item_type == "User Story":
                # User Story has story_point
                if current_sprint_points + story_point <= capacity:
                    # Fits in current sprint
                    current_sprint_items.append(item_id)
                    current_sprint_points += story_point
                    item_to_sprint[item_id] = sprint_num
                    print(f"   ✓ Assigned {item_id} ({story_point} pts) to Sprint {sprint_num} (total: {current_sprint_points}/{capacity})")
                else:
                    # Doesn't fit, create new sprint
                    if current_sprint_items:
                        # Finalize current sprint
                        sprint_start = start_date + timedelta(weeks=(sprint_num - 1) * sprint_duration_weeks)
                        sprint_end = sprint_start + timedelta(weeks=sprint_duration_weeks)

                        sprints.append({
                            "sprint_id": f"sprint-{sprint_num}",
                            "sprint_number": sprint_num,
                            "sprint_goal": f"Sprint {sprint_num} deliverables",
                            "start_date": sprint_start.strftime("%Y-%m-%d"),
                            "end_date": sprint_end.strftime("%Y-%m-%d"),
                            "velocity_plan": current_sprint_points,
                            "velocity_actual": 0,
                            "assigned_items": current_sprint_items.copy(),
                            "status": "Planned"
                        })

                    # Start new sprint
                    sprint_num += 1
                    current_sprint_items = [item_id]
                    current_sprint_points = story_point
                    item_to_sprint[item_id] = sprint_num
                    print(f"   ✓ Assigned {item_id} ({story_point} pts) to Sprint {sprint_num} (new sprint)")

        # Add last sprint if it has items
        if current_sprint_items:
            sprint_start = start_date + timedelta(weeks=(sprint_num - 1) * sprint_duration_weeks)
            sprint_end = sprint_start + timedelta(weeks=sprint_duration_weeks)

            sprints.append({
                "sprint_id": f"sprint-{sprint_num}",
                "sprint_number": sprint_num,
                "sprint_goal": f"Sprint {sprint_num} deliverables",
                "start_date": sprint_start.strftime("%Y-%m-%d"),
                "end_date": sprint_end.strftime("%Y-%m-%d"),
                "velocity_plan": current_sprint_points,
                "velocity_actual": 0,
                "assigned_items": current_sprint_items.copy(),
                "status": "Planned"
            })

        # Update state
        state.sprints = sprints

        # Print summary
        print(f"\n✓ Sprint planning completed")
        print(f"\n📊 Sprint Plan Summary:")
        print(f"   Total sprints: {len(sprints)}")

        for sprint in sprints:
            print(f"\n   Sprint {sprint['sprint_number']}:")
            print(f"      ID: {sprint['sprint_id']}")
            print(f"      Goal: {sprint['sprint_goal']}")
            print(f"      Dates: {sprint['start_date']} to {sprint['end_date']}")
            print(f"      Velocity Plan: {sprint['velocity_plan']} points")
            print(f"      Assigned Items: {len(sprint['assigned_items'])} items")
            print(f"      Items: {', '.join(sprint['assigned_items'][:5])}{' ...' if len(sprint['assigned_items']) > 5 else ''}")

        # Check for unassigned items
        assigned_ids = set(item_to_sprint.keys())
        all_ids = set(item.get("id") for item in prioritized_backlog if item.get("type") != "Sub-task")
        unassigned_ids = all_ids - assigned_ids

        if unassigned_ids:
            print(f"\n⚠️  Unassigned items ({len(unassigned_ids)}):")
            for item_id in list(unassigned_ids)[:5]:
                item = next((i for i in prioritized_backlog if i.get("id") == item_id), None)
                if item:
                    deps = item.get("dependencies", [])
                    print(f"      - {item_id}: dependencies {deps}")
            if len(unassigned_ids) > 5:
                print(f"      ... and {len(unassigned_ids) - 5} more")

        state.status = "sprints_planned"
        print(f"\n✅ Sprints planned successfully - {len(sprints)} sprints created")
        print("="*80 + "\n")

        return state

    def evaluate(self, state: PriorityState) -> PriorityState:
        """Evaluate - Validate sprint plan."""
        # TODO: Implement
        return state

    def refine(self, state: PriorityState) -> PriorityState:
        """Refine - Adjust sprint assignments."""
        # TODO: Implement
        return state

    def finalize(self, state: PriorityState) -> PriorityState:
        """Finalize - Finalize sprint plan."""
        # TODO: Implement
        return state

    def preview(self, state: PriorityState) -> PriorityState:
        """Preview - Human-in-the-loop approval."""
        # TODO: Implement
        return state

    # ========================================================================
    # Branch Functions
    # ========================================================================

    def evaluate_branch(self, state: PriorityState) -> str:
        """Branch sau evaluate node.

        Logic:
        - score >= 0.8 AND loops < max_loops → finalize
        - score < 0.8 OR loops >= max_loops → refine
        """
        if state.readiness_score >= 0.8 and state.current_loop < state.max_loops:
            return "finalize"
        else:
            return "refine"

    def preview_branch(self, state: PriorityState) -> str:
        """Branch sau preview node.

        Logic:
        - user_approval == 'approve' → END
        - user_approval == 'edit' → plan_sprints
        - user_approval == 'reprioritize' → calculate_priority
        """
        if state.user_approval == "approve":
            return END
        elif state.user_approval == "reprioritize":
            return "calculate_priority"
        else:  # edit
            return "plan_sprints"

    # ========================================================================
    # Run Method
    # ========================================================================

    def run(self, product_backlog: dict, thread_id: str | None = None) -> dict[str, Any]:
        """Chạy Priority Agent workflow.

        Args:
            product_backlog: Product Backlog từ Backlog Agent
            thread_id: Thread ID cho checkpointer

        Returns:
            dict: Final state với sprint_plan
        """
        if thread_id is None:
            thread_id = self.session_id or "default_priority_thread"

        initial_state = PriorityState(product_backlog=product_backlog)

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [self.langfuse_handler],
            "recursion_limit": 50
        }

        final_state = None
        for output in self.graph.stream(
            initial_state.model_dump(),
            config=config,
        ):
            final_state = output

        # return final_state or {}
        return None
