#!/usr/bin/env python3

import os
import asyncio
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage

# Load environment variables
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")


from langchain_openai import ChatOpenAI
if __name__ == "__main__":
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1, base_url=base_url, api_key=api_key)

    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Say hello in Vietnamese"),
    ]

    response = llm.invoke(messages)
    print("✅ Mock LLM call successful!")
    print(f"Response: {response.content}")
