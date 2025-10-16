"""
LLM Configuration Presets for VibeSDLC

This module provides pre-configured LLM setups for common use cases and providers.
It makes it easy to switch between different LLM providers without changing code.

Supported Providers:
- OpenAI (official API)
- Local LLMs (LM Studio, Ollama, etc.)
- Together AI
- Anyscale
- Custom endpoints

Usage:
    from app.utils.llm_config import LLMConfig, get_llm_for_provider
    
    # Get LLM for specific provider
    llm = get_llm_for_provider("local", model_name="llama-3-8b")
    
    # Or use config directly
    config = LLMConfig.LOCAL_LLAMA
    llm = create_flexible_llm(**config)
"""

import os
from typing import Dict, Any, Optional
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    LOCAL = "local"
    TOGETHER = "together"
    ANYSCALE = "anyscale"
    CUSTOM = "custom"


class LLMConfig:
    """
    Pre-configured LLM settings for common providers.
    
    Each configuration is a dictionary that can be passed directly to
    create_flexible_llm() or FlexibleLLM().
    """
    
    # OpenAI Official API
    OPENAI_GPT4 = {
        "model_name": "gpt-4o",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.7,
        "max_tokens": None,
        "max_retries": 3,
    }
    
    OPENAI_GPT4_TURBO = {
        "model_name": "gpt-4-turbo",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.7,
        "max_tokens": None,
        "max_retries": 3,
    }
    
    OPENAI_GPT35 = {
        "model_name": "gpt-3.5-turbo",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.7,
        "max_tokens": None,
        "max_retries": 3,
    }
    
    # Local LLM Server (LM Studio, Ollama with OpenAI compatibility, etc.)
    LOCAL_LLAMA = {
        "model_name": "llama-3-8b-instruct",
        "base_url": "http://localhost:1234/v1",
        "api_key": "not-needed",
        "temperature": 0.7,
        "max_tokens": 2048,
        "max_retries": 2,
    }
    
    LOCAL_MISTRAL = {
        "model_name": "mistral-7b-instruct",
        "base_url": "http://localhost:1234/v1",
        "api_key": "not-needed",
        "temperature": 0.7,
        "max_tokens": 2048,
        "max_retries": 2,
    }
    
    LOCAL_CODELLAMA = {
        "model_name": "codellama-13b-instruct",
        "base_url": "http://localhost:1234/v1",
        "api_key": "not-needed",
        "temperature": 0.3,  # Lower for code generation
        "max_tokens": 4096,
        "max_retries": 2,
    }
    
    # Together AI
    TOGETHER_MIXTRAL = {
        "model_name": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "base_url": "https://api.together.xyz/v1",
        "temperature": 0.7,
        "max_tokens": 4096,
        "max_retries": 3,
    }
    
    TOGETHER_LLAMA3_70B = {
        "model_name": "meta-llama/Llama-3-70b-chat-hf",
        "base_url": "https://api.together.xyz/v1",
        "temperature": 0.7,
        "max_tokens": 4096,
        "max_retries": 3,
    }
    
    # Anyscale
    ANYSCALE_MIXTRAL = {
        "model_name": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "base_url": "https://api.endpoints.anyscale.com/v1",
        "temperature": 0.7,
        "max_tokens": 4096,
        "max_retries": 3,
    }
    
    ANYSCALE_LLAMA3_70B = {
        "model_name": "meta-llama/Meta-Llama-3-70B-Instruct",
        "base_url": "https://api.endpoints.anyscale.com/v1",
        "temperature": 0.7,
        "max_tokens": 4096,
        "max_retries": 3,
    }


def get_llm_config(
    provider: str = "openai",
    model_variant: Optional[str] = None,
    **overrides: Any
) -> Dict[str, Any]:
    """
    Get LLM configuration for a specific provider.
    
    Args:
        provider: Provider name (openai, local, together, anyscale, custom)
        model_variant: Specific model variant (e.g., "gpt4", "llama", "mixtral")
        **overrides: Override specific configuration values
    
    Returns:
        Configuration dictionary
    
    Examples:
        # Get default OpenAI config
        config = get_llm_config("openai")
        
        # Get local Llama config
        config = get_llm_config("local", "llama")
        
        # Get config with overrides
        config = get_llm_config("local", "llama", temperature=0.5, max_tokens=1024)
    """
    
    provider = provider.lower()
    
    # Map provider + variant to config
    config_map = {
        ("openai", "gpt4"): LLMConfig.OPENAI_GPT4,
        ("openai", "gpt4-turbo"): LLMConfig.OPENAI_GPT4_TURBO,
        ("openai", "gpt35"): LLMConfig.OPENAI_GPT35,
        ("openai", None): LLMConfig.OPENAI_GPT4,
        
        ("local", "llama"): LLMConfig.LOCAL_LLAMA,
        ("local", "mistral"): LLMConfig.LOCAL_MISTRAL,
        ("local", "codellama"): LLMConfig.LOCAL_CODELLAMA,
        ("local", None): LLMConfig.LOCAL_LLAMA,
        
        ("together", "mixtral"): LLMConfig.TOGETHER_MIXTRAL,
        ("together", "llama3-70b"): LLMConfig.TOGETHER_LLAMA3_70B,
        ("together", None): LLMConfig.TOGETHER_MIXTRAL,
        
        ("anyscale", "mixtral"): LLMConfig.ANYSCALE_MIXTRAL,
        ("anyscale", "llama3-70b"): LLMConfig.ANYSCALE_LLAMA3_70B,
        ("anyscale", None): LLMConfig.ANYSCALE_MIXTRAL,
    }
    
    # Get base config
    config = config_map.get((provider, model_variant), LLMConfig.OPENAI_GPT4).copy()
    
    # Apply overrides
    config.update(overrides)
    
    # Add API key from environment if not provided
    if "api_key" not in config or config["api_key"] is None:
        if provider == "openai":
            config["api_key"] = os.getenv("OPENAI_API_KEY")
        elif provider == "together":
            config["api_key"] = os.getenv("TOGETHER_API_KEY")
        elif provider == "anyscale":
            config["api_key"] = os.getenv("ANYSCALE_API_KEY")
    
    return config


def get_llm_for_provider(
    provider: str = "openai",
    model_variant: Optional[str] = None,
    **overrides: Any
):
    """
    Create a FlexibleLLM instance for a specific provider.
    
    Args:
        provider: Provider name (openai, local, together, anyscale, custom)
        model_variant: Specific model variant
        **overrides: Override specific configuration values
    
    Returns:
        FlexibleLLM instance
    
    Examples:
        # Create OpenAI LLM
        llm = get_llm_for_provider("openai")
        
        # Create local Llama LLM
        llm = get_llm_for_provider("local", "llama")
        
        # Create with custom settings
        llm = get_llm_for_provider("local", "llama", temperature=0.3)
    """
    from .custom_llm import create_flexible_llm
    
    config = get_llm_config(provider, model_variant, **overrides)
    return create_flexible_llm(**config)


def get_llm_from_env() -> Any:
    """
    Create LLM from environment variables.
    
    Environment variables:
    - LLM_PROVIDER: Provider name (default: "openai")
    - LLM_MODEL_VARIANT: Model variant (optional)
    - LLM_MODEL: Override model name
    - OPENAI_BASE_URL: Override base URL
    - DEFAULT_LLM_TEMPERATURE: Override temperature
    
    Returns:
        FlexibleLLM instance configured from environment
    
    Example:
        # In .env file:
        # LLM_PROVIDER=local
        # LLM_MODEL_VARIANT=llama
        # DEFAULT_LLM_TEMPERATURE=0.5
        
        llm = get_llm_from_env()
    """
    from .custom_llm import create_flexible_llm
    
    provider = os.getenv("LLM_PROVIDER", "openai")
    model_variant = os.getenv("LLM_MODEL_VARIANT")
    
    config = get_llm_config(provider, model_variant)
    
    # Override with specific env vars if present
    if os.getenv("LLM_MODEL"):
        config["model_name"] = os.getenv("LLM_MODEL")
    
    if os.getenv("OPENAI_BASE_URL"):
        config["base_url"] = os.getenv("OPENAI_BASE_URL")
    
    if os.getenv("DEFAULT_LLM_TEMPERATURE"):
        config["temperature"] = float(os.getenv("DEFAULT_LLM_TEMPERATURE"))
    
    return create_flexible_llm(**config)

