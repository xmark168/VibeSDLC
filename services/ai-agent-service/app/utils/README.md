# FlexibleLLM - Universal LLM Wrapper for VibeSDLC

## 📋 Overview

FlexibleLLM là một wrapper linh hoạt cho LangChain's ChatOpenAI, cho phép sử dụng **bất kỳ LLM provider nào** có API tương thích với OpenAI format, mà không bị giới hạn bởi các model chính thức của OpenAI.

## 🎯 Key Features

- ✅ **Universal Compatibility**: Hoạt động với bất kỳ OpenAI-compatible API
- ✅ **Custom Model Names**: Không bị giới hạn bởi danh sách model của OpenAI
- ✅ **Flexible Base URLs**: Hỗ trợ local servers, custom proxies, alternative providers
- ✅ **Optional API Keys**: Có thể dùng "not-needed" cho local models
- ✅ **LangChain Compatible**: Drop-in replacement cho ChatOpenAI
- ✅ **Environment Configuration**: Tự động load từ .env files
- ✅ **Pre-configured Presets**: Sẵn config cho các providers phổ biến

## 🚀 Quick Start

### Basic Usage

```python
from app.utils.custom_llm import create_flexible_llm

# Sử dụng với local LLM server (LM Studio, Ollama, etc.)
llm = create_flexible_llm(
    model_name="llama-3-8b-instruct",
    base_url="http://localhost:1234/v1",
    api_key="not-needed",
    temperature=0.7
)

# Sử dụng với OpenAI
llm = create_flexible_llm(
    model_name="gpt-4o",
    base_url="https://api.openai.com/v1",
    api_key="your-openai-api-key",
    temperature=0.7
)

# Sử dụng với Together AI
llm = create_flexible_llm(
    model_name="mistralai/Mixtral-8x7B-Instruct-v0.1",
    base_url="https://api.together.xyz/v1",
    api_key="your-together-api-key",
    temperature=0.7
)
```

### Using Pre-configured Presets

```python
from app.utils.llm_config import get_llm_for_provider

# Local Llama
llm = get_llm_for_provider("local", "llama")

# OpenAI GPT-4
llm = get_llm_for_provider("openai", "gpt4")

# Together AI Mixtral
llm = get_llm_for_provider("together", "mixtral")

# With custom overrides
llm = get_llm_for_provider("local", "llama", temperature=0.3, max_tokens=1024)
```

### Using Environment Variables

```python
from app.utils.llm_config import get_llm_from_env

# Tự động load từ .env
llm = get_llm_from_env()
```

**.env file:**
```bash
# Provider configuration
LLM_PROVIDER=local
LLM_MODEL_VARIANT=llama
LLM_MODEL=llama-3-8b-instruct

# API configuration
OPENAI_BASE_URL=http://localhost:1234/v1
OPENAI_API_KEY=not-needed

# LLM parameters
DEFAULT_LLM_TEMPERATURE=0.7
MAX_TOKENS=2048
MAX_LLM_CALL_RETRIES=2
```

## 📖 Detailed Usage

### 1. FlexibleLLM Class

```python
from app.utils.custom_llm import FlexibleLLM

llm = FlexibleLLM(
    model_name="custom-model-v1",      # Bất kỳ tên model nào
    base_url="http://localhost:8000",   # Custom endpoint
    api_key="optional-key",             # Optional
    temperature=0.7,                    # 0.0 - 2.0
    max_tokens=2048,                    # None = model default
    timeout=60.0,                       # Request timeout
    max_retries=3,                      # Retry on failure
    streaming=False,                    # Stream responses
    # Additional OpenAI parameters
    top_p=0.9,
    frequency_penalty=0.0,
    presence_penalty=0.0,
)
```

### 2. Factory Function

```python
from app.utils.custom_llm import create_flexible_llm

# Minimal - uses env defaults
llm = create_flexible_llm()

# With specific parameters
llm = create_flexible_llm(
    model_name="llama-3-70b",
    temperature=0.5
)

# Without env defaults
llm = create_flexible_llm(
    model_name="custom-model",
    base_url="http://localhost:1234/v1",
    api_key="not-needed",
    use_env_defaults=False
)
```

### 3. Pre-configured Providers

```python
from app.utils.llm_config import get_llm_for_provider

# OpenAI
llm = get_llm_for_provider("openai", "gpt4")
llm = get_llm_for_provider("openai", "gpt4-turbo")
llm = get_llm_for_provider("openai", "gpt35")

# Local LLMs
llm = get_llm_for_provider("local", "llama")
llm = get_llm_for_provider("local", "mistral")
llm = get_llm_for_provider("local", "codellama")

# Together AI
llm = get_llm_for_provider("together", "mixtral")
llm = get_llm_for_provider("together", "llama3-70b")

# Anyscale
llm = get_llm_for_provider("anyscale", "mixtral")
llm = get_llm_for_provider("anyscale", "llama3-70b")
```

## 🔧 Integration with Agent

FlexibleLLM đã được tích hợp vào `agent.py`:

```python
# In agent.py
from app.utils.custom_llm import create_flexible_llm

def create_implementor_agent(
    model_name: str = "gpt-4o",
    **config
):
    # FlexibleLLM automatically used if available
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
```

## 🌐 Supported Providers

### 1. OpenAI (Official)
```python
llm = create_flexible_llm(
    model_name="gpt-4o",
    base_url="https://api.openai.com/v1",
    api_key="sk-..."
)
```

### 2. Local LLM Servers

**LM Studio:**
```python
llm = create_flexible_llm(
    model_name="llama-3-8b-instruct",
    base_url="http://localhost:1234/v1",
    api_key="not-needed"
)
```

**Ollama (with OpenAI compatibility):**
```bash
# Start Ollama with OpenAI API
ollama serve --openai-api
```
```python
llm = create_flexible_llm(
    model_name="llama3",
    base_url="http://localhost:11434/v1",
    api_key="not-needed"
)
```

### 3. Together AI
```python
llm = create_flexible_llm(
    model_name="mistralai/Mixtral-8x7B-Instruct-v0.1",
    base_url="https://api.together.xyz/v1",
    api_key="your-together-api-key"
)
```

### 4. Anyscale
```python
llm = create_flexible_llm(
    model_name="meta-llama/Meta-Llama-3-70B-Instruct",
    base_url="https://api.endpoints.anyscale.com/v1",
    api_key="your-anyscale-api-key"
)
```

### 5. Custom Proxies/Routers
```python
llm = create_flexible_llm(
    model_name="any-model-name",
    base_url="https://your-custom-proxy.com/v1",
    api_key="your-api-key"
)
```

## ⚙️ Environment Variables

```bash
# Provider selection
LLM_PROVIDER=local                    # openai, local, together, anyscale, custom
LLM_MODEL_VARIANT=llama               # gpt4, llama, mistral, mixtral, etc.

# Model configuration
LLM_MODEL=llama-3-8b-instruct         # Override model name
OPENAI_BASE_URL=http://localhost:1234/v1
OPENAI_API_KEY=not-needed

# LLM parameters
DEFAULT_LLM_TEMPERATURE=0.7
MAX_TOKENS=2048
MAX_LLM_CALL_RETRIES=2

# Alternative provider keys
TOGETHER_API_KEY=your-together-key
ANYSCALE_API_KEY=your-anyscale-key
```

## 🎨 Use Cases

### Use Case 1: Development with Local LLM
```python
# .env.development
LLM_PROVIDER=local
LLM_MODEL_VARIANT=llama
OPENAI_BASE_URL=http://localhost:1234/v1
OPENAI_API_KEY=not-needed
```

### Use Case 2: Production with OpenAI
```python
# .env.production
LLM_PROVIDER=openai
LLM_MODEL_VARIANT=gpt4
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-...
```

### Use Case 3: Cost-Effective with Together AI
```python
# .env
LLM_PROVIDER=together
LLM_MODEL_VARIANT=mixtral
OPENAI_BASE_URL=https://api.together.xyz/v1
OPENAI_API_KEY=your-together-key
```

## 🔍 Advanced Features

### Custom Parameters
```python
llm = create_flexible_llm(
    model_name="custom-model",
    temperature=0.7,
    top_p=0.9,
    frequency_penalty=0.5,
    presence_penalty=0.5,
    stop=["END", "STOP"],
)
```

### Streaming
```python
llm = create_flexible_llm(
    model_name="llama-3-8b",
    streaming=True
)

for chunk in llm.stream("Hello, how are you?"):
    print(chunk.content, end="", flush=True)
```

## 📚 API Reference

See inline documentation in:
- `app/utils/custom_llm.py` - FlexibleLLM class and factory
- `app/utils/llm_config.py` - Pre-configured presets

## 🤝 Contributing

When adding new provider presets:
1. Add configuration to `LLMConfig` class in `llm_config.py`
2. Update `get_llm_config()` mapping
3. Add example to this README
4. Test with actual provider

## 📞 Support

For issues or questions:
1. Check environment variables are set correctly
2. Verify base URL is accessible
3. Test with curl to ensure API is working
4. Check API key permissions

---

**Version:** 1.0.0  
**Last Updated:** 2025-10-16  
**Status:** ✅ Production Ready

