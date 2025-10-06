import os
from dotenv import load_dotenv

def normalize_env():
    load_dotenv()
    os.environ.setdefault("MODEL_NAME", "gpt-4.1")

def main():
    normalize_env()
    from app.agents.gatherer_agent import run_gatherer
    from app.agents.vision_agent import run_vision

    mode = os.getenv("AGENT_MODE", "").lower().strip()
    if mode not in ("gatherer", "vision"):
        mode = input("Chọn agent [gatherer/vision]: ").strip().lower() or "vision"

    runner = run_gatherer if mode == "gatherer" else run_vision
    print(f"{mode.capitalize()} Agent (Langfuse + OpenAI-compatible) đã sẵn sàng. Gõ 'exit' để thoát.")
    while True:
        try:
            user_input = input("User: ")
        except (EOFError, KeyboardInterrupt):
            print("\nThoát.")
            break
        if user_input.strip().lower() == "exit":
            break
        output = runner(user_input)
        print("Agent:", output)

if __name__ == "__main__":
    main()
