# app/agents/gatherer_agent/app.py

import json
import uuid
from dotenv import load_dotenv
from app.agents.gatherer_agent.graph import build_graph

RECURSION_LIMIT = 8

def _print_ai(state, tail=2):
    msgs = state.get("ai_messages", [])
    if not msgs:
        return
    for m in msgs[-tail:]:
        print("\nAI:", m)

def main():
    load_dotenv()
    app, _ = build_graph()

    thread_id = str(uuid.uuid4())
    state = {"last_user_input": "", "user_messages": [], "ai_messages": []}
    did_init = False

    print("=== Product Gatherer (LangGraph + Langfuse) ===")
    print("Gõ mô tả sản phẩm của bạn (hoặc 'quit' để thoát).")

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
            state = app.invoke(
                state,
                config={"configurable": {"thread_id": thread_id},
                        "recursion_limit": RECURSION_LIMIT},
                start_at="initialize",
            )
            did_init = True
            _print_ai(state)
            continue

        # 1) Nếu đang ở PREVIEW
        if state.get("awaiting_user") and state.get("mode") == "preview":
            cmd = user.strip()
            if cmd.startswith("approve"):
                state = app.invoke(
                    state,
                    config={"configurable": {"thread_id": thread_id},
                            "recursion_limit": RECURSION_LIMIT},
                    start_at="finalize",
                )
                print("\n✅ Hoàn tất. Brief JSON:")
                print(json.dumps(state["brief"], ensure_ascii=False, indent=2))
                return

            elif cmd.startswith("edit"):
                note = cmd.replace("edit", "", 1).strip() or "Chỉnh sửa nhỏ"
                state["last_user_input"] = note
                state = app.invoke(
                    state,
                    config={"configurable": {"thread_id": thread_id},
                            "recursion_limit": RECURSION_LIMIT},
                    start_at="edit_mode",
                )
                state = app.invoke(
                    state,
                    config={"configurable": {"thread_id": thread_id},
                            "recursion_limit": RECURSION_LIMIT},
                )
                _print_ai(state)
                continue

            else:  # regen
                state = app.invoke(
                    state,
                    config={"configurable": {"thread_id": thread_id},
                            "recursion_limit": RECURSION_LIMIT},
                    start_at="generate",
                )
                state = app.invoke(
                    state,
                    config={"configurable": {"thread_id": thread_id},
                            "recursion_limit": RECURSION_LIMIT},
                )
                _print_ai(state)
                continue

        # 2) Nếu đang chờ user (ask_user / wait_for_user)
        if state.get("awaiting_user") and state.get("mode") in ("ask_user", "wait_for_user"):
            if user.strip().lower() == "skip":
                state["force_preview"] = True
                state = app.invoke(
                    state,
                    config={"configurable": {"thread_id": thread_id},
                            "recursion_limit": RECURSION_LIMIT},
                    start_at="force_generate",
                )
            else:
                state["last_user_input"] = user
                state = app.invoke(
                    state,
                    config={"configurable": {"thread_id": thread_id},
                            "recursion_limit": RECURSION_LIMIT},
                    start_at="collect_inputs",
                )
            _print_ai(state)
            continue

        # 3) Các lượt bình thường sau đó: entry = collect_inputs
        state["last_user_input"] = user
        state = app.invoke(
            state,
            config={"configurable": {"thread_id": thread_id},
                    "recursion_limit": RECURSION_LIMIT},
        )
        _print_ai(state)

if __name__ == "__main__":
    main()
