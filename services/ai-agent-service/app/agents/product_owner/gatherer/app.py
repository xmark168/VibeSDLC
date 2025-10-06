# app/agents/product_owner/gatherer/app.py

import json
import uuid
import os
from dotenv import load_dotenv
from .graph import build_graph, run_with_trace
from langfuse import Langfuse

RECURSION_LIMIT = 8


def _print_ai(state, tail=1):
    msgs = state.get("ai_messages", [])
    if not msgs:
        return
    for m in msgs[-tail:]:
        print("\nAI:", m)


def main():
    load_dotenv()
    app, _ = build_graph()
    lf = Langfuse(
        public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
        host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )

    thread_id = str(uuid.uuid4())
    state = {"last_user_input": "", "user_messages": [], "ai_messages": [], "brief": None}
    did_init = False

    print("=== Product Gatherer (LangGraph + Langfuse) ===")
    print("Gõ mô tả sản phẩm của bạn (hoặc 'quit' để thoát).")

    # Root span for the whole interactive session
    with lf.start_as_current_span(name="gatherer_session_root"):
        while True:
            user = input("\nYou: ")
            if user.strip().lower() == "quit":
                break
            if user.strip() == "":
                continue

            # 🔹 LẦN ĐẦU TIÊN: ép đi qua initialize → collect_inputs
            if not did_init:
                state["last_user_input"] = user
                print("[DEBUG] first message → start_at=initialize")
                state = run_with_trace(
                    app,
                    state,
                    thread_id=thread_id,
                    start_at="initialize",
                    recursion_limit=RECURSION_LIMIT,
                )
                did_init = True
                _print_ai(state)
                continue

            # 1) Nếu đang ở PREVIEW
            if state.get("awaiting_user") and state.get("mode") == "preview":
                cmd = user.strip()
                if cmd.startswith("approve"):
                    state = run_with_trace(
                        app,
                        state,
                        thread_id=thread_id,
                        start_at="finalize",
                        recursion_limit=RECURSION_LIMIT,
                    )
                    print("\n✅ Hoàn tất. Brief JSON:")
                    print(json.dumps(state["brief"], ensure_ascii=False, indent=2))
                    break

                elif cmd.startswith("edit"):
                    note = cmd.replace("edit", "", 1).strip() or "Chỉnh sửa nhỏ"
                    state["last_user_input"] = note
                    state = run_with_trace(
                        app,
                        state,
                        thread_id=thread_id,
                        start_at="edit_mode",
                        recursion_limit=RECURSION_LIMIT,
                    )
                    state = run_with_trace(
                        app,
                        state,
                        thread_id=thread_id,
                        recursion_limit=RECURSION_LIMIT,
                    )
                    _print_ai(state)
                    continue

                else:  # regen
                    state = run_with_trace(
                        app,
                        state,
                        thread_id=thread_id,
                        start_at="generate",
                        recursion_limit=RECURSION_LIMIT,
                    )
                    state = run_with_trace(
                        app,
                        state,
                        thread_id=thread_id,
                        recursion_limit=RECURSION_LIMIT,
                    )
                    _print_ai(state)
                    continue

            # 2) Nếu đang chờ user (ask_user / wait_for_user)
            if state.get("awaiting_user") and state.get("mode") in ("ask_user", "wait_for_user"):
                if user.strip().lower() == "skip":
                    state["force_preview"] = True
                    state = run_with_trace(
                        app,
                        state,
                        thread_id=thread_id,
                        start_at="force_generate",
                        recursion_limit=RECURSION_LIMIT,
                    )
                else:
                    state["last_user_input"] = user
                    state = run_with_trace(
                        app,
                        state,
                        thread_id=thread_id,
                        start_at="collect_inputs",
                        recursion_limit=RECURSION_LIMIT,
                    )
                _print_ai(state)
                continue

            # 3) Các lượt bình thường sau đó: entry = collect_inputs
            state["last_user_input"] = user
            state = run_with_trace(
                app,
                state,
                thread_id=thread_id,
                recursion_limit=RECURSION_LIMIT,
            )
            _print_ai(state)
    try:
        lf.flush()
    except Exception:
        pass


if __name__ == "__main__":
    main()


