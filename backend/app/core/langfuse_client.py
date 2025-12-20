def get_langfuse_client():
    try:
        from langfuse import get_client
        return get_client()
    except Exception:
        return None


def get_langfuse_handler():
    try:
        from langfuse.langchain import CallbackHandler
        return CallbackHandler()
    except Exception:
        return None


def observe_decorator(*args, **kwargs):
    try:
        from langfuse import observe
        return observe(*args, **kwargs)
    except Exception:
        def noop_decorator(func):
            return func
        return noop_decorator(*args, **kwargs)


def create_observation_span(name: str, as_type: str = "span", **kwargs):
    try:
        from langfuse import get_client
        langfuse = get_client()
        return langfuse.start_as_current_observation(as_type=as_type, name=name, **kwargs)
    except Exception:
        return None


def create_event(name: str, **kwargs):
    try:
        from langfuse import get_client
        langfuse = get_client()
        return langfuse.create_event(name=name, **kwargs)
    except Exception:
        return None


def propagate_attributes(*, user_id: str = None, session_id: str = None, 
                        tags: list = None, metadata: dict = None, 
                        version: str = None):
    try:
        from langfuse import get_client
        langfuse = get_client()
        return langfuse.propagate_attributes(
            user_id=user_id,
            session_id=session_id,
            tags=tags,
            metadata=metadata,
            version=version
        )
    except Exception:
        return None


def flush_langfuse():
    try:
        from langfuse import get_client
        get_client().flush()
    except Exception:
        pass


async def async_flush_langfuse():
    """Async flush langfuse client - non-blocking."""
    try:
        from langfuse import get_client
        await get_client().async_api.flush()
    except Exception:
        pass


def shutdown_langfuse():
    try:
        from langfuse import get_client
        get_client().shutdown()
    except Exception:
        pass


async def async_shutdown_langfuse():
    """Async shutdown langfuse client - non-blocking."""
    try:
        from langfuse import get_client
        await get_client().async_api.shutdown()
    except Exception:
        pass


def get_langfuse_context():
    return None

def update_current_trace(**kwargs):
    return False

def update_current_observation(**kwargs):
    return False

def score_current(name, value, **kwargs):
    return False

def create_session_id(project_id, conversation_id=None):
    return f"proj_{project_id[:50]}" if project_id else "unknown"

def format_llm_usage(response):
    return {}

def format_chat_messages(messages):
    return []

def get_langchain_callback(**kwargs):
    return get_langfuse_handler()
