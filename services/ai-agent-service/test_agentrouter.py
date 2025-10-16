#!/usr/bin/env python3
"""Test AgentRouter API connection"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration
base_url = os.getenv("OPENAI_BASE_URL")
api_key = os.getenv("OPENAI_API_KEY")
system_key = os.getenv("SYSTEM_KEY", "").strip('"')  # Remove quotes if present

print("=" * 60)
print("AgentRouter API Test")
print("=" * 60)
print(f"Base URL: {base_url}")
print(f"API Key: {api_key[:15]}..." if api_key else "API Key: None")
print(f"System Key: {system_key[:15]}..." if system_key else "System Key: None")
print(f"System Key length: {len(system_key)}" if system_key else "System Key length: 0")
print("=" * 60)

# Test API call with different auth methods
test_configs = [
    {
        "name": "Bearer with System Key",
        "headers": {"Authorization": f"Bearer {system_key}", "Content-Type": "application/json"},
    },
    {
        "name": "SYSTEM_KEY Header",
        "headers": {"SYSTEM_KEY": system_key, "Content-Type": "application/json"},
    },
    {
        "name": "X-API-Key with System Key",
        "headers": {"X-API-Key": system_key, "Content-Type": "application/json"},
    },
    {
        "name": "Authorization Bearer + API Key",
        "headers": {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    },
]

for config in test_configs:
    print(f"\n{'=' * 60}")
    print(f"Testing with: {config['name']}")
    print(f"{'=' * 60}")

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=config["headers"],
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Say hello in 3 words"}],
                "max_tokens": 20,
            },
            timeout=30,
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCCESS!")
            print(f"Model: {data.get('model')}")
            print(f"Content: {data['choices'][0]['message']['content']}")
            break  # Stop testing if successful
        else:
            print("❌ FAILED")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

print("=" * 60)
