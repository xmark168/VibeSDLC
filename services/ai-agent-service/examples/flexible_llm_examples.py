"""
FlexibleLLM Usage Examples

This script demonstrates various ways to use FlexibleLLM with different providers.

Run examples:
    python examples/flexible_llm_examples.py
"""

import asyncio
import os
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.custom_llm import FlexibleLLM, create_flexible_llm
from app.utils.llm_config import get_llm_for_provider, get_llm_from_env


def example_1_basic_usage():
    """Example 1: Basic usage with custom parameters"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Usage")
    print("="*80)
    
    # Create LLM with explicit parameters
    llm = FlexibleLLM(
        model_name="llama-3-8b-instruct",
        base_url="http://localhost:1234/v1",
        api_key="not-needed",
        temperature=0.7,
        max_tokens=100
    )
    
    print(f"Created LLM: {llm}")
    print(f"Model: {llm.model_name}")
    print(f"Base URL: {llm._base_url}")
    print(f"Temperature: {llm.temperature}")
    
    # Test invocation (will fail if server not running)
    try:
        response = llm.invoke("Say hello in one sentence")
        print(f"\nResponse: {response.content}")
    except Exception as e:
        print(f"\n⚠️ Could not connect to LLM server: {e}")
        print("Make sure your local LLM server is running on http://localhost:1234")


def example_2_factory_function():
    """Example 2: Using factory function"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Factory Function")
    print("="*80)
    
    # Simple creation with defaults
    llm = create_flexible_llm()
    print(f"Default LLM: {llm}")
    
    # With custom parameters
    llm = create_flexible_llm(
        model_name="gpt-4o",
        temperature=0.5,
        max_tokens=200
    )
    print(f"Custom LLM: {llm}")
    
    # Without env defaults
    llm = create_flexible_llm(
        model_name="custom-model",
        base_url="http://localhost:8000/v1",
        api_key="test-key",
        use_env_defaults=False
    )
    print(f"No env defaults: {llm}")


def example_3_provider_presets():
    """Example 3: Using provider presets"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Provider Presets")
    print("="*80)
    
    # Local Llama
    llm_local = get_llm_for_provider("local", "llama")
    print(f"Local Llama: {llm_local}")
    
    # OpenAI GPT-4
    llm_openai = get_llm_for_provider("openai", "gpt4")
    print(f"OpenAI GPT-4: {llm_openai}")
    
    # Together AI Mixtral
    llm_together = get_llm_for_provider("together", "mixtral")
    print(f"Together Mixtral: {llm_together}")
    
    # With overrides
    llm_custom = get_llm_for_provider(
        "local", 
        "llama",
        temperature=0.3,
        max_tokens=512
    )
    print(f"Custom local: {llm_custom}")


def example_4_environment_config():
    """Example 4: Configuration from environment"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Environment Configuration")
    print("="*80)
    
    # Show current environment variables
    print("Current environment:")
    print(f"  LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'not set')}")
    print(f"  LLM_MODEL: {os.getenv('LLM_MODEL', 'not set')}")
    print(f"  OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL', 'not set')}")
    print(f"  DEFAULT_LLM_TEMPERATURE: {os.getenv('DEFAULT_LLM_TEMPERATURE', 'not set')}")
    
    # Create from environment
    llm = get_llm_from_env()
    print(f"\nLLM from env: {llm}")


def example_5_multiple_providers():
    """Example 5: Using multiple providers simultaneously"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Multiple Providers")
    print("="*80)
    
    # Create LLMs for different providers
    providers = {
        "Local Llama": get_llm_for_provider("local", "llama"),
        "Local Mistral": get_llm_for_provider("local", "mistral"),
        "OpenAI GPT-4": get_llm_for_provider("openai", "gpt4"),
        "Together Mixtral": get_llm_for_provider("together", "mixtral"),
    }
    
    print("Created LLMs for multiple providers:")
    for name, llm in providers.items():
        print(f"  {name}: {llm.model_name} @ {llm._base_url}")


def example_6_streaming():
    """Example 6: Streaming responses"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Streaming Responses")
    print("="*80)
    
    llm = create_flexible_llm(
        model_name="llama-3-8b-instruct",
        base_url="http://localhost:1234/v1",
        api_key="not-needed",
        streaming=True,
        temperature=0.7
    )
    
    print(f"Streaming LLM: {llm}")
    print("\nTrying to stream response...")
    
    try:
        print("Response: ", end="", flush=True)
        for chunk in llm.stream("Count from 1 to 5"):
            print(chunk.content, end="", flush=True)
        print()  # New line
    except Exception as e:
        print(f"\n⚠️ Could not stream: {e}")


def example_7_agent_integration():
    """Example 7: Integration with agent"""
    print("\n" + "="*80)
    print("EXAMPLE 7: Agent Integration")
    print("="*80)
    
    # This shows how FlexibleLLM is used in agent.py
    print("In agent.py, FlexibleLLM is used like this:")
    print("""
    from app.utils.custom_llm import create_flexible_llm
    
    def create_implementor_agent(model_name="gpt-4o", **config):
        llm = create_flexible_llm(
            model_name=model_name,
            base_url=AGENT_ROUTER_URL,
            api_key=AGENT_ROUTER_KEY,
            temperature=0.1,
            max_tokens=None,
            max_retries=2,
        )
        
        agent = create_deep_agent(
            tools=tools,
            instructions=instructions,
            model=llm,
        )
        
        return agent
    """)
    
    # Create example LLM
    llm = create_flexible_llm(
        model_name="gpt-4o",
        temperature=0.1
    )
    print(f"\nExample agent LLM: {llm}")


def example_8_custom_parameters():
    """Example 8: Advanced custom parameters"""
    print("\n" + "="*80)
    print("EXAMPLE 8: Advanced Custom Parameters")
    print("="*80)
    
    llm = create_flexible_llm(
        model_name="llama-3-8b",
        base_url="http://localhost:1234/v1",
        api_key="not-needed",
        temperature=0.7,
        max_tokens=500,
        top_p=0.9,
        frequency_penalty=0.5,
        presence_penalty=0.5,
        timeout=30.0,
        max_retries=3,
    )
    
    print(f"LLM with custom parameters: {llm}")
    print(f"  Temperature: {llm.temperature}")
    print(f"  Max tokens: {llm.max_tokens}")
    print(f"  Timeout: {llm.timeout}")
    print(f"  Max retries: {llm.max_retries}")


def main():
    """Run all examples"""
    print("\n" + "🚀"*40)
    print("FLEXIBLE LLM EXAMPLES")
    print("🚀"*40)
    
    examples = [
        example_1_basic_usage,
        example_2_factory_function,
        example_3_provider_presets,
        example_4_environment_config,
        example_5_multiple_providers,
        example_6_streaming,
        example_7_agent_integration,
        example_8_custom_parameters,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n❌ Error in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "✅"*40)
    print("ALL EXAMPLES COMPLETED")
    print("✅"*40)
    print("\nNote: Some examples may fail if LLM servers are not running.")
    print("To test with local LLM:")
    print("  1. Start LM Studio or Ollama")
    print("  2. Load a model")
    print("  3. Enable OpenAI API compatibility")
    print("  4. Run this script again")


if __name__ == "__main__":
    main()

