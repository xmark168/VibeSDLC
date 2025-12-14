"""LLM utilities for Developer V2."""


def get_langfuse_config(state: dict, run_name: str) -> dict:
    handler = state.get("langfuse_handler")
    return {"callbacks": [handler], "run_name": run_name} if handler else {"run_name": run_name}


def flush_langfuse(state: dict) -> None:
    client = state.get("langfuse_client")
    if client:
        try:
            client.flush()
        except Exception:
            pass


def get_langfuse_span(state: dict, name: str, input_data: dict = None):
    if not state.get("langfuse_handler"):
        return None
    try:
        from langfuse import get_client
        return get_client().span(name=name, input=input_data or {})
    except Exception:
        return None
