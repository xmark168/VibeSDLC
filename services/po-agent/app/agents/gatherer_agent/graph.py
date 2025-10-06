# app/agents/gatherer_agent/graph.py
from typing import Dict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import BriefState
from . import nodes

def _tid(config: Dict) -> str:
    return (config or {}).get("configurable", {}).get("thread_id", "default-thread")

def build_graph() -> tuple:
    g = StateGraph(BriefState)

    # === Nodes (y nguyên sơ đồ) ===
    g.add_node("initialize",          lambda s, *, config: nodes.initialize(s, _tid(config)))
    g.add_node("collect_inputs",      lambda s, *, config: nodes.collect_inputs(s, _tid(config)))
    g.add_node("evaluate",            lambda s, *, config: nodes.evaluate(s, _tid(config)))
    g.add_node("clarify",             lambda s, *, config: nodes.clarify(s, _tid(config)))
    g.add_node("suggest",             lambda s, *, config: nodes.suggest(s, _tid(config)))
    g.add_node("ask_user",            lambda s, *, config: nodes.ask_user(s, _tid(config)))
    g.add_node("increment_iteration", lambda s, *, config: nodes.increment_iteration(s, _tid(config)))
    g.add_node("wait_for_user",       lambda s, *, config: nodes.wait_for_user(s, _tid(config)))
    g.add_node("generate",            lambda s, *, config: nodes.generate(s, _tid(config)))
    g.add_node("validate",            lambda s, *, config: nodes.validate(s, _tid(config)))
    g.add_node("retry_decision",      lambda s, *, config: nodes.retry_decision(s, _tid(config)))
    g.add_node("preview",             lambda s, *, config: nodes.preview(s, _tid(config)))
    g.add_node("edit_mode",           lambda s, *, config: nodes.edit_mode(s, _tid(config)))
    g.add_node("finalize",            lambda s, *, config: nodes.finalize(s, _tid(config)))
    g.add_node("force_generate",      lambda s, *, config: nodes.force_generate(s, _tid(config)))

    # Entry-point: vẫn là collect_inputs để không log trước khi nhập
    g.set_entry_point("initialize")

    # Chuỗi chuẩn
    g.add_edge("collect_inputs", "evaluate")

    # ✅ THÊM LẠI CẠNH NÀY (để có thể thấy initialize đúng một lần khi bạn chủ động gọi):
    g.add_edge("initialize", "collect_inputs")

    # === After evaluate (đúng sơ đồ) ===
    def after_evaluate(state: BriefState):
        if state.get("iteration_count", 0) >= state.get("max_iterations", 3):
            return "force_generate"
        ev = state.get("eval")
        if not ev:
            return "generate"
        if ev.status == "invalid" or (ev.confidence or 0) <= 0.7:
            return "clarify"
        if ev.gaps and (ev.confidence or 0) > 0.6:
            return "suggest"
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

    # clarify/suggest -> ask_user -> increment_iteration -> wait_for_user (HIL sink)
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
