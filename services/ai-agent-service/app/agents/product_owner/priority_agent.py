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

from templates.prompts.product_owner.priority import (
    CALCULATE_PRIORITY_PROMPT,
    EVALUATE_SPRINT_PLAN_PROMPT,
    REFINE_SPRINT_PLAN_PROMPT,
    ADJUST_SPRINT_PLAN_PROMPT,
)


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


class CapacityIssue(BaseModel):
    """Model cho capacity issue."""
    sprint_id: str = Field(description="ID của sprint có issue")
    issue_type: str = Field(description="Loại issue: overload, underload")
    description: str = Field(description="Mô tả chi tiết issue")
    severity: str = Field(description="Mức độ nghiêm trọng: critical, high, medium, low")


class DependencyIssue(BaseModel):
    """Model cho dependency issue."""
    item_id: str = Field(description="ID của item có issue")
    sprint_id: str = Field(description="ID của sprint chứa item")
    issue_type: str = Field(description="Loại issue: dependency_not_met, circular_dependency")
    description: str = Field(description="Mô tả chi tiết issue")
    severity: str = Field(description="Mức độ nghiêm trọng: critical, high, medium, low")


class EvaluateOutput(BaseModel):
    """Structured output cho evaluate node."""
    readiness_score: float = Field(description="Điểm readiness (0.0-1.0)", ge=0.0, le=1.0)
    can_proceed: bool = Field(description="Sprint plan có đạt yêu cầu không")
    capacity_issues: list[CapacityIssue] = Field(default_factory=list, description="Danh sách capacity issues")
    dependency_issues: list[DependencyIssue] = Field(default_factory=list, description="Danh sách dependency issues")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations để cải thiện")


class RefineOutput(BaseModel):
    """Structured output cho refine node."""
    refined_sprints: list[dict] = Field(description="Danh sách sprints đã được refine")
    changes_made: list[str] = Field(default_factory=list, description="Danh sách changes đã apply")
    issues_fixed: dict = Field(default_factory=dict, description="Số lượng issues đã fix")


class AdjustSprintPlanOutput(BaseModel):
    """Structured output cho adjust sprint plan (when user edits)."""
    adjusted_sprints: list[dict] = Field(description="Danh sách sprints đã được adjust theo user feedback")
    changes_made: list[str] = Field(default_factory=list, description="Danh sách changes đã apply")


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

        # Initialize Langfuse callback handler (without session_id/user_id in constructor)
        # Session/user metadata will be passed via config metadata during invoke/stream
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
        graph_builder.add_edge("plan_sprints", "evaluate")
        graph_builder.add_conditional_edges("evaluate", self.evaluate_branch)
        graph_builder.add_edge("refine", "plan_sprints")  # refine → plan_sprints
        graph_builder.add_edge("finalize", "preview")
        graph_builder.add_conditional_edges("preview", self.preview_branch)

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

        # Check if user provided feedback for reprioritization
        user_feedback_section = ""
        if state.user_feedback:
            print(f"\n📝 User Feedback Detected: {state.user_feedback}")
            user_feedback_section = f"""
**User Feedback (MUST APPLY):**
{state.user_feedback}

**Action Required:** You MUST adjust the WSJF scores according to the user feedback above.
"""

        # Format prompt
        prompt = CALCULATE_PRIORITY_PROMPT.format(
            product_name=state.product_backlog.get('metadata', {}).get('product_name', 'N/A'),
            items_json=json.dumps(items_for_scoring, ensure_ascii=False, indent=2),
            user_feedback_section=user_feedback_section
        )

        try:
            print("\n🤖 Calling LLM to score WSJF factors...")
            llm = self._llm("gpt-4.1", 0.3)

            # Call LLM without structured output (to avoid API 500 error)
            response = llm.invoke([HumanMessage(content=prompt)])

            # Parse JSON response manually
            response_text = response.content

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result_dict = json.loads(response_text)

            # Extract wsjf_scores from parsed JSON
            wsjf_scores = result_dict.get("wsjf_scores", [])

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

            # Clear user_feedback after processing to avoid reapplying in next iteration
            if state.user_feedback:
                print(f"\n✓ User feedback applied successfully, clearing feedback state")
                state.user_feedback = None

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

        # Check if user provided feedback (from edit mode)
        if state.user_feedback:
            print(f"\n📝 User Feedback Detected: {state.user_feedback}")
            print("🤖 Using LLM to adjust sprint plan based on feedback...")
            return self._adjust_sprints_with_llm(state)

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

        print(f"\n🔄 Packing items into sprints (multi-pass for dependencies)...")

        # Multi-pass packing: duyệt lại backlog nhiều lần để xử lý dependencies
        max_passes = 5  # Giới hạn số lần duyệt
        for pass_num in range(1, max_passes + 1):
            items_assigned_this_pass = 0
            print(f"\n🔁 Pass {pass_num}/{max_passes}:")

            for item in prioritized_backlog:
                item_id = item.get("id")
                item_type = item.get("type")
                story_point = item.get("story_point", 0)
                dependencies = item.get("dependencies", [])

                # Skip Sub-tasks (they follow their parent)
                if item_type == "Sub-task":
                    continue

                # Skip if already assigned
                if item_id in item_to_sprint:
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
                    elif item_to_sprint[dep_id] > sprint_num:
                        # Dependency in future sprint - not acceptable
                        can_assign = False
                        unmet_deps.append(dep_id)
                    # Note: Dependencies in same sprint (item_to_sprint[dep_id] == sprint_num) are OK
                    # because they were assigned earlier in the priority order

                if not can_assign:
                    print(f"   ⏭️  Deferring {item_id}: waiting for dependencies {unmet_deps}")
                    continue

                # Check capacity
                if item_type in ["Epic", "Task"]:
                    # Epic and Task have no story_point, don't count toward capacity
                    # But still assign to sprint
                    current_sprint_items.append(item_id)
                    item_to_sprint[item_id] = sprint_num
                    items_assigned_this_pass += 1
                    print(f"   ✓ Assigned {item_id} ({item_type}) to Sprint {sprint_num}")

                elif item_type == "User Story":
                    # User Story has story_point
                    if current_sprint_points + story_point <= capacity:
                        # Fits in current sprint
                        current_sprint_items.append(item_id)
                        current_sprint_points += story_point
                        item_to_sprint[item_id] = sprint_num
                        items_assigned_this_pass += 1
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
                        items_assigned_this_pass += 1
                        print(f"   ✓ Assigned {item_id} ({story_point} pts) to Sprint {sprint_num} (new sprint)")

            # Check if any items were assigned in this pass
            print(f"   📊 Pass {pass_num} summary: {items_assigned_this_pass} items assigned")

            if items_assigned_this_pass == 0:
                print(f"   ✅ No more items can be assigned (dependencies resolved or capacity full)")
                break

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

        # NOTE: Sub-tasks are NOT assigned to sprints directly
        # Sub-tasks are implementation details that belong to their parent User Story/Task
        # When querying a sprint, sub-tasks can be fetched via parent_id relationship

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

    def _adjust_sprints_with_llm(self, state: PriorityState) -> PriorityState:
        """Use LLM to adjust sprint plan based on user feedback.

        This method is called from plan_sprints when user_feedback is present.
        """
        # Prepare simplified backlog data (only essential fields to reduce token usage)
        simplified_backlog = []
        for item in state.prioritized_backlog:
            simplified_backlog.append({
                "id": item.get("id"),
                "type": item.get("type"),
                "title": item.get("title"),
                "rank": item.get("rank"),
                "story_point": item.get("story_point", 0),
                "dependencies": item.get("dependencies", [])
            })

        # Prepare data for LLM
        sprint_plan_json = json.dumps(state.sprints, ensure_ascii=False, indent=2)
        prioritized_backlog_json = json.dumps(simplified_backlog, ensure_ascii=False, indent=2)

        # Format prompt
        prompt = ADJUST_SPRINT_PLAN_PROMPT.format(
            sprint_plan_json=sprint_plan_json,
            prioritized_backlog_json=prioritized_backlog_json,
            sprint_duration_weeks=state.sprint_duration_weeks,
            sprint_capacity=state.sprint_capacity_story_points,
            user_feedback=state.user_feedback
        )

        try:
            print("\n🤖 Calling LLM to adjust sprint plan based on user feedback...")
            llm = self._llm("gpt-4.1", 0.3)

            # Call LLM without structured output (to avoid API 500 error)
            response = llm.invoke([HumanMessage(content=prompt)])

            # Parse JSON response manually
            response_text = response.content

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result_dict = json.loads(response_text)

            # Update state with adjusted sprints
            adjusted_sprints = result_dict.get("adjusted_sprints", [])
            changes_made = result_dict.get("changes_made", [])

            state.sprints = adjusted_sprints

            # Print summary
            print(f"\n✓ Sprint plan adjusted by LLM")
            print(f"   Total Sprints: {len(adjusted_sprints)}")

            # Print changes
            if changes_made:
                print(f"\n🔄 Changes Applied:")
                for change in changes_made:
                    print(f"   - {change}")

            # Print adjusted sprint summary
            print(f"\n📊 Adjusted Sprint Plan:")
            for sprint in adjusted_sprints:
                sprint_num = sprint.get("sprint_number")
                velocity = sprint.get("velocity_plan", 0)
                items_count = len(sprint.get("assigned_items", []))
                start_date = sprint.get("start_date", "N/A")
                end_date = sprint.get("end_date", "N/A")

                # Calculate capacity utilization
                capacity = state.sprint_capacity_story_points
                utilization = (velocity / capacity * 100) if capacity > 0 else 0

                # Capacity status indicator
                if utilization > 100:
                    status_icon = "🔴"  # Overload
                elif utilization < 70:
                    status_icon = "🟡"  # Underload
                else:
                    status_icon = "🟢"  # Good

                print(f"   Sprint {sprint_num}: {status_icon} {velocity}/{capacity} pts ({utilization:.0f}%) - {items_count} items ({start_date} to {end_date})")

            # Clear user_feedback after processing
            print(f"\n✓ User feedback applied successfully, clearing feedback state")
            state.user_feedback = None
            state.status = "sprints_planned"

            print(f"\n✅ Sprint plan adjusted successfully - {len(adjusted_sprints)} sprints created")
            print("="*80 + "\n")

        except Exception as e:
            print(f"❌ Error adjusting sprint plan: {e}")
            import traceback
            traceback.print_exc()
            state.status = "error_adjusting_sprints"

        return state

    def evaluate(self, state: PriorityState) -> PriorityState:
        """Evaluate - Validate sprint plan.

        Tasks:
        1. Check capacity issues (overload/underload)
        2. Check dependency issues (sprint order conflicts)
        3. Check MVP readiness (sprint 1 has critical items)
        4. Calculate readiness_score (0.0-1.0)
        5. Set can_proceed flag (score >= 0.8)
        """
        print("\n" + "="*80)
        print("🔍 EVALUATE NODE - Validate Sprint Plan")
        print("="*80)

        if not state.sprints:
            print("⚠️  No sprints to evaluate")
            state.can_proceed = False
            state.readiness_score = 0.0
            state.status = "error_no_sprints"
            return state

        if not state.prioritized_backlog:
            print("⚠️  No prioritized backlog to reference")
            state.can_proceed = False
            state.readiness_score = 0.0
            state.status = "error_no_backlog"
            return state

        print(f"\n📊 Evaluating Sprint Plan:")
        print(f"   - Total Sprints: {len(state.sprints)}")
        print(f"   - Total Prioritized Items: {len(state.prioritized_backlog)}")
        print(f"   - Capacity per Sprint: {state.sprint_capacity_story_points} points")

        # Prepare data for LLM evaluation
        sprint_plan_data = {
            "sprints": state.sprints,
            "prioritized_backlog": state.prioritized_backlog,
            "wsjf_calculations": state.wsjf_calculations
        }

        sprint_plan_json = json.dumps(sprint_plan_data, ensure_ascii=False, indent=2)

        # Format prompt
        prompt = EVALUATE_SPRINT_PLAN_PROMPT.format(
            sprint_plan_json=sprint_plan_json,
            sprint_duration_weeks=state.sprint_duration_weeks,
            sprint_capacity=state.sprint_capacity_story_points
        )

        try:
            print("\n🤖 Calling LLM to evaluate sprint plan...")
            llm = self._llm("gpt-4.1", 0.3)

            # Call LLM without structured output (to avoid API 500 error)
            response = llm.invoke([HumanMessage(content=prompt)])

            # Parse JSON response manually
            response_text = response.content

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result_dict = json.loads(response_text)

            # Update state with evaluation results from parsed JSON
            state.readiness_score = result_dict.get("readiness_score", 0.0)
            state.can_proceed = result_dict.get("can_proceed", False)
            state.capacity_issues = result_dict.get("capacity_issues", [])
            state.dependency_issues = result_dict.get("dependency_issues", [])
            state.recommendations = result_dict.get("recommendations", [])

            # Print evaluation summary
            print(f"\n✓ Evaluate completed")
            print(f"   Readiness Score: {state.readiness_score:.2f}")
            print(f"   Can Proceed: {state.can_proceed}")

            if state.capacity_issues:
                print(f"\n⚠️  Capacity Issues ({len(state.capacity_issues)}):")
                for i, issue in enumerate(state.capacity_issues[:5], 1):
                    severity = issue.get('severity', 'unknown')
                    severity_icon = "🔴" if severity == "critical" else "🟡" if severity == "high" else "🟢"
                    print(f"   {i}. {severity_icon} [{issue.get('sprint_id')}] {issue.get('issue_type')}: {issue.get('description')[:60]}...")
                if len(state.capacity_issues) > 5:
                    print(f"   ... và {len(state.capacity_issues) - 5} issues khác")

            if state.dependency_issues:
                print(f"\n⚠️  Dependency Issues ({len(state.dependency_issues)}):")
                for i, issue in enumerate(state.dependency_issues[:5], 1):
                    severity = issue.get('severity', 'unknown')
                    severity_icon = "🔴" if severity == "critical" else "🟡" if severity == "high" else "🟢"
                    print(f"   {i}. {severity_icon} [{issue.get('item_id')}] {issue.get('issue_type')}: {issue.get('description')[:60]}...")
                if len(state.dependency_issues) > 5:
                    print(f"   ... và {len(state.dependency_issues) - 5} issues khác")

            if state.recommendations:
                print(f"\n💡 Recommendations ({len(state.recommendations)}):")
                for i, rec in enumerate(state.recommendations[:3], 1):
                    print(f"   {i}. {rec}")
                if len(state.recommendations) > 3:
                    print(f"   ... và {len(state.recommendations) - 3} recommendations khác")

            # Print structured output
            print(f"\n📊 Evaluation Result:")
            eval_output = {
                "readiness_score": state.readiness_score,
                "can_proceed": state.can_proceed,
                "capacity_issues_count": len(state.capacity_issues),
                "dependency_issues_count": len(state.dependency_issues),
                "recommendations_count": len(state.recommendations)
            }
            print(json.dumps(eval_output, ensure_ascii=False, indent=2))
            print()

            # Update status
            if state.can_proceed:
                state.status = "evaluated_pass"
                print("✅ Sprint plan đạt yêu cầu, ready để finalize")
            else:
                state.status = "evaluated_needs_refine"
                print("⚠️  Sprint plan cần refine")

        except Exception as e:
            print(f"❌ Error evaluating sprint plan: {e}")
            import traceback
            traceback.print_exc()
            state.can_proceed = False
            state.readiness_score = 0.0
            state.status = "error_evaluating"

        print("="*80 + "\n")
        return state

    def refine(self, state: PriorityState) -> PriorityState:
        """Refine - Adjust sprint assignments.

        Tasks:
        1. Increment current_loop counter
        2. Fix capacity issues (overload/underload)
        3. Fix dependency issues (reorder items)
        4. Balance sprint workload
        5. Update sprints with refined assignments
        """
        print("\n" + "="*80)
        print("🔧 REFINE NODE - Adjust Sprint Assignments")
        print("="*80)

        # Increment loop counter
        state.current_loop += 1
        print(f"\n🔄 Refine Loop: {state.current_loop}/{state.max_loops}")

        if not state.sprints:
            print("⚠️  No sprints to refine")
            state.status = "error_no_sprints"
            return state

        if not state.capacity_issues and not state.dependency_issues:
            print("⚠️  No issues to fix (this shouldn't happen)")
            print("   Evaluation should have passed if there are no issues")
            state.status = "refined_no_changes"
            return state

        print(f"\n📊 Issues to Fix:")
        print(f"   - Capacity Issues: {len(state.capacity_issues)}")
        print(f"   - Dependency Issues: {len(state.dependency_issues)}")
        print(f"   - Total Recommendations: {len(state.recommendations)}")

        # Prepare data for LLM
        sprint_plan_data = {
            "sprints": state.sprints,
            "prioritized_backlog": state.prioritized_backlog,
            "wsjf_calculations": state.wsjf_calculations
        }

        issues_data = {
            "capacity_issues": state.capacity_issues,
            "dependency_issues": state.dependency_issues
        }

        sprint_plan_json = json.dumps(sprint_plan_data, ensure_ascii=False, indent=2)
        issues_json = json.dumps(issues_data, ensure_ascii=False, indent=2)
        recommendations_text = "\n".join([f"- {rec}" for rec in state.recommendations])

        # Format prompt
        prompt = REFINE_SPRINT_PLAN_PROMPT.format(
            sprint_plan_json=sprint_plan_json,
            sprint_duration_weeks=state.sprint_duration_weeks,
            sprint_capacity=state.sprint_capacity_story_points,
            issues_json=issues_json,
            recommendations=recommendations_text
        )

        try:
            print("\n🤖 Calling LLM to refine sprint plan...")
            llm = self._llm("gpt-4.1", 0.3)

            # Call LLM without structured output (to avoid API 500 error)
            response = llm.invoke([HumanMessage(content=prompt)])

            # Parse JSON response manually
            response_text = response.content

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result_dict = json.loads(response_text)

            # Extract results from parsed JSON
            refined_sprints = result_dict.get("refined_sprints", [])
            changes_made = result_dict.get("changes_made", [])
            issues_fixed = result_dict.get("issues_fixed", {})

            # Update state with refined sprints
            state.sprints = refined_sprints

            # Print summary
            print(f"\n✓ Refine completed")
            print(f"   Total Sprints: {len(refined_sprints)}")
            print(f"   Changes Made: {len(changes_made)}")

            # Print changes
            if changes_made:
                print(f"\n🔄 Changes Applied ({len(changes_made)}):")
                for i, change in enumerate(changes_made[:10], 1):
                    print(f"   {i}. {change}")
                if len(changes_made) > 10:
                    print(f"   ... và {len(changes_made) - 10} changes khác")

            # Print issues fixed
            if issues_fixed:
                print(f"\n✅ Issues Fixed:")
                capacity_fixed = issues_fixed.get("capacity_issues", 0)
                dependency_fixed = issues_fixed.get("dependency_issues", 0)
                print(f"   - Capacity Issues: {capacity_fixed}")
                print(f"   - Dependency Issues: {dependency_fixed}")

            # Print refined sprint summary
            print(f"\n📊 Refined Sprint Plan:")
            for sprint in refined_sprints:
                sprint_num = sprint.get("sprint_number")
                velocity = sprint.get("velocity_plan", 0)
                capacity = state.sprint_capacity_story_points
                utilization = (velocity / capacity * 100) if capacity > 0 else 0
                items_count = len(sprint.get("assigned_items", []))

                # Capacity status indicator
                if utilization > 100:
                    status_icon = "🔴"  # Overload
                elif utilization < 70:
                    status_icon = "🟡"  # Underload
                else:
                    status_icon = "🟢"  # Good

                print(f"   Sprint {sprint_num}: {status_icon} {velocity}/{capacity} pts ({utilization:.0f}%) - {items_count} items")

            # Check for unassigned items after refine
            assigned_ids = set()
            for sprint in refined_sprints:
                assigned_ids.update(sprint.get("assigned_items", []))

            all_ids = set(item.get("id") for item in state.prioritized_backlog if item.get("type") != "Sub-task")
            unassigned_ids = all_ids - assigned_ids

            if unassigned_ids:
                print(f"\n⚠️  Still {len(unassigned_ids)} unassigned items after refine:")
                for item_id in list(unassigned_ids)[:5]:
                    print(f"      - {item_id}")
                if len(unassigned_ids) > 5:
                    print(f"      ... and {len(unassigned_ids) - 5} more")

            # Update status
            state.status = "refined"
            print(f"\n✅ Sprint plan refined successfully (loop {state.current_loop}/{state.max_loops})")

        except Exception as e:
            print(f"❌ Error refining sprint plan: {e}")
            import traceback
            traceback.print_exc()
            state.status = "error_refining"

        print("="*80 + "\n")
        return state

    def finalize(self, state: PriorityState) -> PriorityState:
        """Finalize - Finalize sprint plan.

        Tasks:
        1. Validate sprint plan completeness
        2. Calculate sprint statistics
        3. Add sprint goals (có thể dùng LLM hoặc template)
        4. Format sprint plan thành final output
        5. Prepare handoff cho Dev Agent
        """
        print("\n" + "="*80)
        print("✅ FINALIZE NODE - Finalize Sprint Plan")
        print("="*80)

        if not state.sprints:
            print("⚠️  No sprints to finalize")
            state.status = "error_no_sprints"
            return state

        if not state.prioritized_backlog:
            print("⚠️  No prioritized backlog")
            state.status = "error_no_backlog"
            return state

        print(f"\n📊 Finalizing Sprint Plan:")
        print(f"   - Total Sprints: {len(state.sprints)}")
        print(f"   - Total Items: {len(state.prioritized_backlog)}")

        # Calculate statistics
        total_story_points = 0
        total_items_assigned = 0
        sprints_with_items = 0

        for sprint in state.sprints:
            if sprint.get("assigned_items"):
                sprints_with_items += 1
                total_items_assigned += len(sprint["assigned_items"])
                total_story_points += sprint.get("velocity_plan", 0)

        # Calculate unassigned items
        assigned_ids = set()
        for sprint in state.sprints:
            assigned_ids.update(sprint.get("assigned_items", []))

        all_ids = set(item.get("id") for item in state.prioritized_backlog if item.get("type") != "Sub-task")
        unassigned_ids = all_ids - assigned_ids

        print(f"\n📈 Sprint Plan Statistics:")
        print(f"   - Total Sprints: {len(state.sprints)}")
        print(f"   - Sprints with Items: {sprints_with_items}")
        print(f"   - Total Items Assigned: {total_items_assigned}/{len(all_ids)}")
        print(f"   - Total Story Points: {total_story_points}")
        print(f"   - Unassigned Items: {len(unassigned_ids)}")

        # Validate completeness
        validation_warnings = []

        if len(unassigned_ids) > 0:
            validation_warnings.append(f"{len(unassigned_ids)} items remain unassigned (possible circular dependencies or capacity constraints)")

        if total_items_assigned == 0:
            validation_warnings.append("No items have been assigned to any sprint")

        if len(state.sprints) == 0:
            validation_warnings.append("No sprints have been created")

        # Print validation warnings
        if validation_warnings:
            print(f"\n⚠️  Validation Warnings ({len(validation_warnings)}):")
            for i, warning in enumerate(validation_warnings, 1):
                print(f"   {i}. {warning}")

        # Build final sprint plan
        metadata = state.product_backlog.get("metadata", {})

        sprint_plan_metadata = {
            "product_name": metadata.get("product_name", "N/A"),
            "version": metadata.get("version", "v1.0"),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sprint_duration_weeks": state.sprint_duration_weeks,
            "sprint_capacity_story_points": state.sprint_capacity_story_points,
            "total_sprints": len(state.sprints),
            "total_items_assigned": total_items_assigned,
            "total_story_points": total_story_points,
            "total_unassigned_items": len(unassigned_ids),
            "readiness_score": state.readiness_score,
            "status": "finalized"
        }

        # Add unassigned items info if any
        unassigned_items_data = []
        if unassigned_ids:
            for item_id in unassigned_ids:
                item = next((i for i in state.prioritized_backlog if i.get("id") == item_id), None)
                if item:
                    unassigned_items_data.append({
                        "id": item_id,
                        "type": item.get("type"),
                        "title": item.get("title"),
                        "rank": item.get("rank"),
                        "dependencies": item.get("dependencies", []),
                        "reason": "Dependencies not met or capacity exceeded"
                    })

        # Build final sprint plan
        state.sprint_plan = {
            "metadata": sprint_plan_metadata,
            "prioritized_backlog": state.prioritized_backlog,
            "wsjf_calculations": state.wsjf_calculations,
            "sprints": state.sprints,
            "unassigned_items": unassigned_items_data
        }

        # Print final summary
        print(f"\n📊 Final Sprint Plan:")
        print(f"   Product: {sprint_plan_metadata['product_name']}")
        print(f"   Version: {sprint_plan_metadata['version']}")
        print(f"   Created: {sprint_plan_metadata['created_at']}")
        print(f"   Total Sprints: {sprint_plan_metadata['total_sprints']}")
        print(f"   Total Items Assigned: {sprint_plan_metadata['total_items_assigned']}")
        print(f"   Total Story Points: {sprint_plan_metadata['total_story_points']}")
        print(f"   Readiness Score: {sprint_plan_metadata['readiness_score']:.2f}")

        # Print sprint breakdown
        print(f"\n📋 Sprint Breakdown:")
        for sprint in state.sprints:
            sprint_num = sprint.get("sprint_number")
            velocity = sprint.get("velocity_plan", 0)
            items_count = len(sprint.get("assigned_items", []))
            dates = f"{sprint.get('start_date')} to {sprint.get('end_date')}"
            print(f"   Sprint {sprint_num}: {velocity} pts, {items_count} items ({dates})")

        if unassigned_items_data:
            print(f"\n⚠️  Unassigned Items ({len(unassigned_items_data)}):")
            for item in unassigned_items_data[:5]:
                print(f"      - {item['id']}: {item['title'][:50]} (dependencies: {item['dependencies']})")
            if len(unassigned_items_data) > 5:
                print(f"      ... and {len(unassigned_items_data) - 5} more")

        print(f"\n📤 Handoff Status:")
        print(f"   ✅ Sprint plan finalized and ready for preview")
        print(f"   → Next: Preview for human approval")

        # Update state status
        state.status = "finalized"

        print("="*80 + "\n")
        return state

    def preview(self, state: PriorityState) -> PriorityState:
        """Preview - Human-in-the-loop approval.

        Tasks:
        1. Hiển thị sprint plan summary
        2. Hiển thị sample items cho mỗi sprint
        3. Prompt user để approve/edit/reprioritize
        4. Set user_approval và user_feedback
        """
        print("\n" + "="*80)
        print("👀 PREVIEW NODE - Sprint Plan Preview & Approval")
        print("="*80)

        if not state.sprint_plan:
            print("⚠️  No sprint plan to preview")
            state.user_approval = "edit"
            state.status = "error_no_sprint_plan"
            return state

        metadata = state.sprint_plan.get("metadata", {})
        sprints = state.sprint_plan.get("sprints", [])
        prioritized_backlog = state.sprint_plan.get("prioritized_backlog", [])
        unassigned_items = state.sprint_plan.get("unassigned_items", [])

        print(f"\n📊 Sprint Plan Summary:")
        print(f"   Product: {metadata.get('product_name', 'N/A')}")
        print(f"   Version: {metadata.get('version', 'N/A')}")
        print(f"   Created: {metadata.get('created_at', 'N/A')}")
        print(f"   Sprint Duration: {metadata.get('sprint_duration_weeks', 2)} weeks")
        print(f"   Sprint Capacity: {metadata.get('sprint_capacity_story_points', 30)} points")
        print(f"   Total Sprints: {metadata.get('total_sprints', 0)}")
        print(f"   Total Items Assigned: {metadata.get('total_items_assigned', 0)}")
        print(f"   Total Story Points: {metadata.get('total_story_points', 0)}")
        print(f"   Readiness Score: {metadata.get('readiness_score', 0.0):.2f}")

        # Show sprint breakdown với sample items
        print(f"\n📋 Sprint Breakdown:")
        for sprint in sprints:
            sprint_num = sprint.get("sprint_number")
            sprint_id = sprint.get("sprint_id")
            velocity = sprint.get("velocity_plan", 0)
            items_count = len(sprint.get("assigned_items", []))
            start_date = sprint.get("start_date", "N/A")
            end_date = sprint.get("end_date", "N/A")

            # Calculate capacity utilization
            capacity = state.sprint_capacity_story_points
            utilization = (velocity / capacity * 100) if capacity > 0 else 0

            # Capacity status indicator
            if utilization > 100:
                status_icon = "🔴"  # Overload
            elif utilization < 70:
                status_icon = "🟡"  # Underload
            else:
                status_icon = "🟢"  # Good

            print(f"\n   {status_icon} Sprint {sprint_num} ({sprint_id}):")
            print(f"      Dates: {start_date} to {end_date}")
            print(f"      Velocity: {velocity}/{capacity} pts ({utilization:.0f}%)")
            print(f"      Items: {items_count} items")

            # Show top 5 items in this sprint
            assigned_item_ids = sprint.get("assigned_items", [])
            sprint_items = [item for item in prioritized_backlog if item.get("id") in assigned_item_ids]

            if sprint_items:
                print(f"      Top Items:")
                for i, item in enumerate(sprint_items[:5], 1):
                    item_id = item.get("id")
                    item_type = item.get("type")
                    item_title = item.get("title", "N/A")[:50]
                    rank = item.get("rank", "N/A")
                    story_point = item.get("story_point", 0)

                    if item_type == "User Story":
                        print(f"         {i}. [{item_id}] {item_title} (Rank: {rank}, {story_point} pts)")
                    else:
                        print(f"         {i}. [{item_id}] {item_title} (Rank: {rank}, {item_type})")

                if len(sprint_items) > 5:
                    print(f"         ... and {len(sprint_items) - 5} more items")

        # Show unassigned items if any
        if unassigned_items:
            print(f"\n⚠️  Unassigned Items ({len(unassigned_items)}):")
            for i, item in enumerate(unassigned_items[:5], 1):
                item_id = item.get("id")
                item_title = item.get("title", "N/A")[:50]
                dependencies = item.get("dependencies", [])
                reason = item.get("reason", "Unknown")
                print(f"   {i}. [{item_id}] {item_title}")
                print(f"      Dependencies: {dependencies}")
                print(f"      Reason: {reason}")
            if len(unassigned_items) > 5:
                print(f"   ... and {len(unassigned_items) - 5} more")

        # Prompt for user approval
        print("\n" + "="*80)
        print("🔔 HUMAN INPUT REQUIRED:")
        print("   Sprint plan đã sẵn sàng để handoff đến Dev Agent.")
        print("   Bạn có muốn:")
        print("   - 'approve': Chấp nhận và kết thúc")
        print("   - 'edit': Yêu cầu chỉnh sửa sprint assignments (quay lại plan_sprints)")
        print("   - 'reprioritize': Yêu cầu tính lại priority (quay lại calculate_priority)")
        print()

        # For automated testing/production, get user input
        # In production API, this should be handled via callback or interrupt
        try:
            user_input = input("   Your choice (approve/edit/reprioritize): ").strip().lower()
        except EOFError:
            # For automated environments without stdin
            print("   ⚠️  No stdin available, defaulting to 'approve'")
            user_input = "approve"

        if user_input == "approve":
            state.user_approval = "approve"
            state.user_feedback = None
            state.status = "approved"
            print("\n✅ User approved! Sprint plan sẽ được handoff đến Dev Agent.")

        elif user_input == "reprioritize":
            state.user_approval = "reprioritize"
            state.status = "needs_reprioritize"
            print("\n🔄 User requested reprioritize.")

            # Ask for feedback
            print("\n📝 Vui lòng nhập lý do/yêu cầu reprioritize:")
            print("   (Ví dụ: 'Thay đổi business value của US-001', 'Tăng priority cho Epic-002')")
            print()
            try:
                feedback = input("   Feedback: ").strip()
            except EOFError:
                feedback = "User requested reprioritization"

            if feedback:
                state.user_feedback = feedback
                print(f"\n✓ Đã ghi nhận feedback: {feedback[:100]}...")
            else:
                print("\n⚠️  Không có feedback, sẽ reprioritize với thông tin hiện có")
                state.user_feedback = "Reprioritize với WSJF factors mới"

            print("\n🔄 Returning to calculate_priority...")

        elif user_input == "edit":
            state.user_approval = "edit"
            state.status = "needs_edit"
            print("\n🔧 User requested edit.")

            # Ask for feedback
            print("\n📝 Vui lòng nhập lý do/yêu cầu chỉnh sửa:")
            print("   (Ví dụ: 'Di chuyển US-007 từ Sprint 2 sang Sprint 1', 'Tạo thêm sprint mới')")
            print()
            try:
                feedback = input("   Feedback: ").strip()
            except EOFError:
                feedback = "User requested sprint plan edit"

            if feedback:
                state.user_feedback = feedback
                print(f"\n✓ Đã ghi nhận feedback: {feedback[:100]}...")
            else:
                print("\n⚠️  Không có feedback, sẽ yêu cầu chỉnh sửa tổng quát")
                state.user_feedback = "Cải thiện sprint plan dựa trên recommendations"

            print("\n🔧 Returning to plan_sprints...")

        else:
            # Invalid input, default to approve
            print(f"\n⚠️  Invalid input '{user_input}', defaulting to 'approve'")
            state.user_approval = "approve"
            state.user_feedback = None
            state.status = "approved"

        print("="*80 + "\n")
        return state

    # ========================================================================
    # Branch Functions
    # ========================================================================

    def evaluate_branch(self, state: PriorityState) -> str:
        """Branch sau evaluate node.

        Logic:
        - loops >= max_loops → finalize (FORCE finalize để tránh infinite loop)
        - score >= 0.8 → finalize
        - score < 0.8 AND loops < max_loops → refine
        """
        print(f"\n🔀 Evaluate Branch Decision:")
        print(f"   Readiness Score: {state.readiness_score:.2f}")
        print(f"   Current Loop: {state.current_loop}")
        print(f"   Max Loops: {state.max_loops}")

        # Force finalize if reached max loops
        if state.current_loop >= state.max_loops:
            print(f"   → Decision: FINALIZE (reached max_loops {state.max_loops})")
            return "finalize"

        # Finalize if score is good
        if state.readiness_score >= 0.8:
            print(f"   → Decision: FINALIZE (score >= 0.8)")
            return "finalize"

        # Otherwise refine
        print(f"   → Decision: REFINE (score < 0.8 and loops < max)")
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
            dict: Final sprint plan JSON structure cho Dev Agent
        """
        if thread_id is None:
            thread_id = self.session_id or "default_priority_thread"

        initial_state = PriorityState(product_backlog=product_backlog)

        # Build metadata for Langfuse tracing with session_id and user_id
        metadata = {}
        if self.session_id:
            metadata["langfuse_session_id"] = self.session_id
        if self.user_id:
            metadata["langfuse_user_id"] = self.user_id
        # Add tags
        metadata["langfuse_tags"] = ["priority_agent"]

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [self.langfuse_handler],
            "metadata": metadata,  # Pass session_id/user_id via metadata
            "recursion_limit": 50
        }

        final_state = None
        for output in self.graph.stream(
            initial_state.model_dump(),
            config=config,
        ):
            final_state = output

        # Extract final state from graph output
        if final_state:
            # final_state is a dict with node name as key
            # Get the last node's state (should be 'preview' when approved)
            state_dict = next(iter(final_state.values()))

            # Return sprint_plan if available (approved path)
            if state_dict.get("sprint_plan"):
                sprint_plan = state_dict["sprint_plan"]

                print("\n" + "="*80)
                print("📤 PRIORITY AGENT - FINAL OUTPUT")
                print("="*80)
                print(f"✅ Sprint plan ready for handoff to Dev Agent")
                print(f"   Product: {sprint_plan.get('metadata', {}).get('product_name', 'N/A')}")
                print(f"   Total Sprints: {sprint_plan.get('metadata', {}).get('total_sprints', 0)}")
                print(f"   Total Items: {sprint_plan.get('metadata', {}).get('total_items_assigned', 0)}")
                print(f"   Status: {sprint_plan.get('metadata', {}).get('status', 'N/A')}")
                print("="*80 + "\n")

                return sprint_plan

            # If user chose edit/reprioritize (loop back), return intermediate state
            return state_dict

        return {}
