#!/usr/bin/env python3
"""Simple test with OpenAI client"""

from openai import OpenAI

# Test with System Access Token
client = OpenAI(
    api_key="Y35gPkMnTQBFLw1iYowPALRcXQNEKgk=",
    base_url="https://agentrouter.org/v1"
)

print("Testing AgentRouter with OpenAI client...")
print("=" * 60)

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "Say hello in 3 words"}
        ],
        max_tokens=20
    )
    
    print("✅ SUCCESS!")
    print(f"Model: {response.model}")
    print(f"Content: {response.choices[0].message.content}")
    print(f"Usage: {response.usage}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    print(f"Error type: {type(e).__name__}")

print("=" * 60)

