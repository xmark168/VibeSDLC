"""
Flexible LLM Wrapper for VibeSDLC

This module provides a flexible LLM wrapper that can work with any LLM provider
that supports OpenAI-compatible API format. It allows using custom base URLs,
model names, and API keys without being restricted to OpenAI's official models.

Key Features:
- Support for any OpenAI-compatible API endpoint
- Custom model names (local models, alternative providers, etc.)
- Optional API key (for local models)
- Full LangChain compatibility
- Drop-in replacement for ChatOpenAI
- Environment variable configuration support

Usage Examples:

    # Example 1: Using with custom base URL and model
    llm = FlexibleLLM(
        base_url="http://localhost:1234/v1",
        model_name="llama-3-8b",
        api_key="not-needed",
        temperature=0.7
    )

    # Example 2: Using with alternative provider
    llm = FlexibleLLM(
        base_url="https://api.together.xyz/v1",
        model_name="mistralai/Mixtral-8x7B-Instruct-v0.1",
        api_key="your-together-api-key",
        temperature=0.5
    )

    # Example 3: Using factory function with env vars
    llm = create_flexible_llm()  # Uses OPENAI_BASE_URL and OPENAI_API_KEY

    # Example 4: Override specific parameters
    llm = create_flexible_llm(
        model_name="gpt-4-turbo",
        temperature=0.2
    )
"""

import os
from typing import Any, Dict, List, Optional, Union
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel


class FlexibleLLM(ChatOpenAI):
    """
    Flexible LLM wrapper that extends ChatOpenAI to support any OpenAI-compatible API.
    
    This class inherits from ChatOpenAI but removes restrictions on model names
    and base URLs, allowing it to work with:
    - Local LLM servers (LM Studio, Ollama with OpenAI compatibility, etc.)
    - Alternative LLM providers (Together AI, Anyscale, etc.)
    - Custom LLM proxies and routers
    - Any OpenAI-compatible API endpoint
    
    Attributes:
        model_name (str): Name of the model to use (can be any string)
        base_url (str): Base URL of the API endpoint
        api_key (str): API key (can be "not-needed" for local models)
        temperature (float): Sampling temperature (0.0 to 2.0)
        max_tokens (Optional[int]): Maximum tokens to generate
        timeout (Optional[float]): Request timeout in seconds
        max_retries (int): Maximum number of retries on failure
        streaming (bool): Whether to stream responses
        **kwargs: Additional parameters passed to ChatOpenAI
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4o",
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retries: int = 2,
        streaming: bool = False,
        **kwargs: Any
    ):
        """
        Initialize FlexibleLLM.
        
        Args:
            model_name: Name of the model (can be any string, not restricted to OpenAI models)
            base_url: Base URL of the API endpoint (e.g., "http://localhost:1234/v1")
            api_key: API key (use "not-needed" or any string for local models without auth)
            temperature: Sampling temperature (0.0 = deterministic, 2.0 = very random)
            max_tokens: Maximum tokens to generate (None = model default)
            timeout: Request timeout in seconds (None = no timeout)
            max_retries: Number of retries on API failure
            streaming: Whether to stream responses
            **kwargs: Additional parameters (e.g., top_p, frequency_penalty, presence_penalty)
        """
        
        # Set defaults from environment if not provided
        if base_url is None:
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY", "not-needed")
        
        # Initialize parent ChatOpenAI with all parameters
        super().__init__(
            model=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            streaming=streaming,
            **kwargs
        )
        
        # Store for easy access
        self.model_name = model_name
        self._base_url = base_url
        self._api_key = api_key
    
    def __repr__(self) -> str:
        """String representation of the LLM."""
        return (
            f"FlexibleLLM(model_name='{self.model_name}', "
            f"base_url='{self._base_url}', "
            f"temperature={self.temperature})"
        )
    
    @property
    def _llm_type(self) -> str:
        """Return type of LLM."""
        return "flexible_llm"
    
    @classmethod
    def from_env(
        cls,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> "FlexibleLLM":
        """
        Create FlexibleLLM from environment variables.
        
        Environment variables used:
        - OPENAI_BASE_URL: Base URL for the API
        - OPENAI_API_KEY: API key
        - LLM_MODEL: Default model name (if model_name not provided)
        - DEFAULT_LLM_TEMPERATURE: Default temperature (if temperature not provided)
        
        Args:
            model_name: Override model name from env
            temperature: Override temperature from env
            **kwargs: Additional parameters
        
        Returns:
            FlexibleLLM instance configured from environment
        """
        if model_name is None:
            model_name = os.getenv("LLM_MODEL", "gpt-4o")
        
        if temperature is None:
            temperature = float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.7"))
        
        return cls(
            model_name=model_name,
            temperature=temperature,
            **kwargs
        )


def create_flexible_llm(
    model_name: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: Optional[float] = None,
    max_retries: int = 2,
    streaming: bool = False,
    use_env_defaults: bool = True,
    **kwargs: Any
) -> FlexibleLLM:
    """
    Factory function to create a FlexibleLLM instance.
    
    This is a convenience function that provides a simple interface for creating
    LLM instances with sensible defaults from environment variables.
    
    Args:
        model_name: Model name (defaults to env LLM_MODEL or "gpt-4o")
        base_url: API base URL (defaults to env OPENAI_BASE_URL)
        api_key: API key (defaults to env OPENAI_API_KEY)
        temperature: Sampling temperature (defaults to env DEFAULT_LLM_TEMPERATURE or 0.7)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds
        max_retries: Number of retries on failure
        streaming: Whether to stream responses
        use_env_defaults: Whether to use environment variables for defaults
        **kwargs: Additional parameters
    
    Returns:
        FlexibleLLM instance
    
    Examples:
        # Use all defaults from environment
        llm = create_flexible_llm()
        
        # Override specific parameters
        llm = create_flexible_llm(model_name="llama-3-8b", temperature=0.5)
        
        # Use custom endpoint without env vars
        llm = create_flexible_llm(
            base_url="http://localhost:1234/v1",
            model_name="custom-model",
            api_key="not-needed",
            use_env_defaults=False
        )
    """
    
    if use_env_defaults:
        # Load from environment if not explicitly provided
        if model_name is None:
            model_name = os.getenv("LLM_MODEL", "gpt-4o")
        
        if base_url is None:
            base_url = os.getenv("OPENAI_BASE_URL")
        
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if temperature is None:
            temp_str = os.getenv("DEFAULT_LLM_TEMPERATURE", "0.7")
            temperature = float(temp_str)
        
        if max_tokens is None:
            max_tokens_str = os.getenv("MAX_TOKENS")
            if max_tokens_str:
                max_tokens = int(max_tokens_str)
        
        if max_retries is None:
            max_retries_str = os.getenv("MAX_LLM_CALL_RETRIES", "2")
            max_retries = int(max_retries_str)
    
    return FlexibleLLM(
        model_name=model_name or "gpt-4o",
        base_url=base_url,
        api_key=api_key,
        temperature=temperature or 0.7,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        streaming=streaming,
        **kwargs
    )


# Convenience aliases
create_llm = create_flexible_llm
CustomLLM = FlexibleLLM

