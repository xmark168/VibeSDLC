import os
from dotenv import load_dotenv

def normalize_env():
    """

    """
    load_dotenv()  # load từ .env

    os.environ.setdefault("MODEL_NAME", "gpt-4.1")

def main():
    normalize_env()

    from app.agents.gatherer_agent import run_gatherer

    print("Gatherer Agent (Langfuse + OpenAI-compatible) đã sẵn sàng. Gõ 'exit' để thoát.")
    while True:
        try:
            user_input = input("User: ")
        except (EOFError, KeyboardInterrupt):
            print("\nThoát.")
            break
        if user_input.strip().lower() == "exit":
            break
        output = run_gatherer(user_input)
        print("Agent:", output)

if __name__ == "__main__":
    main()
