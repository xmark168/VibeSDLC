# app/agents/product_owner/gatherer/graph.py
from typing import Dict, Optional
import os
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import BriefState
from . import nodes
import os
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
    host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)
callback_handler = CallbackHandler()

def build_graph() -> tuple:
    g = StateGraph(BriefState)

    # === Nodes (mapping theo thiết kế trong po-agent) ===
    g.add_node("initialize", lambda s, *, config: nodes.initialize(s))
    g.add_node("collect_inputs", lambda s, *, config: nodes.collect_inputs(s))
    g.add_node("evaluate", lambda s, *, config: nodes.evaluate(s))
    g.add_node("clarify", lambda s, *, config: nodes.clarify(s))
    g.add_node("suggest", lambda s, *, config: nodes.suggest(s))
    g.add_node("ask_user", lambda s, *, config: nodes.ask_user(s))
    g.add_node("increment_iteration", lambda s, *, config: nodes.increment_iteration(s))
    g.add_node("wait_for_user", lambda s, *, config: nodes.wait_for_user(s))
    g.add_node("generate", lambda s, *, config: nodes.generate(s))
    g.add_node("validate", lambda s, *, config: nodes.validate(s))
    g.add_node("retry_decision", lambda s, *, config: nodes.retry_decision(s))
    g.add_node("preview", lambda s, *, config: nodes.preview(s))
    g.add_node("edit_mode", lambda s, *, config: nodes.edit_mode(s))
    g.add_node("finalize", lambda s, *, config: nodes.finalize(s))
    g.add_node("force_generate", lambda s, *, config: nodes.force_generate(s))

    # Entry-point
    g.set_entry_point("initialize")

    # Chuỗi chuẩn
    g.add_edge("collect_inputs", "evaluate")
    g.add_edge("initialize", "collect_inputs")

    # === After evaluate ===
    def after_evaluate(state: BriefState):
        # Nếu user đã chọn skip ở UI, ưu tiên đi nhánh force_generate
        if state.get("force_preview"):
            return "force_generate"
        if state.get("iteration_count", 0) >= state.get("max_iterations", 3):
            return "force_generate"
        ev = state.get("eval")
        if not ev:
            return "generate"
        if ev.status == "invalid" or (ev.confidence or 0) <= 0.7:
            return "clarify"
        # Hỏi người dùng tối đa 1 vòng; sau đó chuyển sang generate
        if ev.gaps and (ev.confidence or 0) > 0.6:
            if state.get("iteration_count", 0) == 0:
                return "suggest"
            else:
                return "generate"
        if ev.status == "done" or (ev.score or 0) >= 0.8:
            return "preview"
        return "generate"

    g.add_conditional_edges(
        "evaluate",
        after_evaluate,
        {
            "force_generate": "force_generate",
            "clarify": "clarify",
            "suggest": "suggest",
            "preview": "preview",
            "generate": "generate",
        },
    )

    # clarify/suggest -> ask_user -> increment_iteration -> wait_for_user (SINK)
    g.add_edge("clarify", "ask_user")
    g.add_edge("suggest", "ask_user")
    g.add_edge("ask_user", "increment_iteration")
    g.add_edge("increment_iteration", "wait_for_user")

    # generate -> validate -> retry_decision
    g.add_edge("generate", "validate")
    g.add_edge("force_generate", "validate")
    g.add_edge("validate", "retry_decision")

    # === After retry_decision ===
    def after_retry(state: BriefState):
        if state.get("force_preview"):
            state["force_preview"] = False
            return "preview"
        ev = state.get("eval")
        if ev and ev.status != "invalid" and (ev.confidence or 0) > 0.7:
            return "preview"
        if state.get("retry_count", 0) >= 1:
            return "preview"
        if ev and ev.gaps:
            return "clarify"
        return "evaluate"

    g.add_conditional_edges(
        "retry_decision",
        after_retry,
        {"preview": "preview", "clarify": "clarify", "evaluate": "evaluate"},
    )

    # SINKs
    g.add_edge("wait_for_user", END)
    g.add_edge("preview", END)

    # edit_mode -> validate -> ...
    g.add_edge("edit_mode", "validate")

    # finalize
    g.add_edge("finalize", END)

    memory = MemorySaver()
    app = g.compile(checkpointer=memory)
    return app, memory


def run_with_trace(
    app,
    state: dict,
    *,
    thread_id: str,
    start_at: Optional[str] = None,
    recursion_limit: int = 8,
):
    """Invoke the graph inside a Langfuse root span so the whole run appears as one trace.

    Args:
        app: compiled graph
        state: initial state dict
        thread_id: identifier for the session (used as metadata)
        start_at: optional node name to start at
        recursion_limit: graph recursion limit
    """
    try:
        # Create a child span; root span is opened at session level in app.main
        span_name = f"node:{start_at or 'flow'}"
        with langfuse.start_as_current_span(
            name=span_name,
            metadata={"thread_id": thread_id},
        ):
            result = app.invoke(
                state,
                config={
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": recursion_limit,
                    "callbacks": [callback_handler],
                },
                start_at=start_at,
            )
        langfuse.flush()
        return result
    except Exception:
        # still try to flush on error
        try:
            langfuse.flush()
        except Exception:
            pass
        raise

