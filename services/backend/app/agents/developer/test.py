"""
Simple test script to check if OpenAI API is working
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

def test_openai_connection():
    """Test basic OpenAI API connection"""
    try:
        print("Testing OpenAI API connection...")
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            print(f"API Key: {api_key[:20]}...")
        else:
            print("No API key found")
        print(f"Base URL: {os.getenv('OPENAI_BASE_URL')}")

        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4.1",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            max_retries=2,
        )

        # Simple test prompt
        print("\nSending test prompt...")
        response = llm.invoke("Say 'Hello, API is working!' in one sentence.")

        print("\nAPI Response:")
        print(response.content)
        print("\nConnection successful!")
        return True

    except Exception as e:
        print(f"\nConnection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_openai_connection()
