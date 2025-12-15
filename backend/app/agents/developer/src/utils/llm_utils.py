"""LLM utilities for Developer V2."""
from functools import wraps


def track_node(node_name: str):
    """
    Decorator to track node execution in Langfuse with detailed logging.
    
    Creates a span that captures:
    - Input: story info, current step, plan details
    - Output: result status, files modified, errors
    - Metadata: node name, story_id, complexity, timing
    - Nested LLM calls via CallbackHandler
    
    Usage:
        @track_node("plan")
        async def plan(state, config):
            # ... node logic ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(state, config=None, **kwargs):
            import logging
            import time
            from app.core.config import settings
            
            logger = logging.getLogger(__name__)
            
            # Skip tracking if Langfuse is disabled
            if not settings.LANGFUSE_ENABLED:
                return await func(state, **kwargs)
            
            # Execute function without Langfuse tracking if it fails
            try:
                from langfuse import get_client
                langfuse = get_client()
                
                # Prepare detailed input
                node_input = {
                    "story_code": state.get("story_code"),
                    "story_title": state.get("story_title"),
                    "step": f"{state.get('current_step', 0)}/{state.get('total_steps', 0)}",
                    "complexity": state.get("complexity"),
                    "workspace": state.get("workspace_path", "").split("\\")[-1] if state.get("workspace_path") else None,
                }
                
                # Add node-specific input
                if node_name == "plan":
                    node_input["feature_description"] = state.get("content", "")[:200]
                elif node_name in ["implement", "implement_parallel"]:
                    node_input["plan_steps"] = len(state.get("plan", {}).get("steps", []))
                    node_input["current_file"] = state.get("current_file")
                elif node_name == "review":
                    node_input["review_mode"] = state.get("review_mode", "LGTM")
                elif node_name == "run_code":
                    node_input["services"] = state.get("services", [])
                
                # Prepare metadata
                metadata = {
                    "node": node_name,
                    "story_id": state.get("story_id"),
                    "story_code": state.get("story_code", ""),
                    "agent": state.get("agent_name", "unknown"),
                    "parallel": state.get("parallel", False),
                }
                
                start_time = time.time()
                
                # Create span and set as current observation
                with langfuse.start_as_current_observation(
                    as_type="span",
                    name=f"{node_name}_node",
                    input=node_input,
                    metadata=metadata
                ) as span:
                    logger.info(f"[track_node] Started tracking {node_name} for story {state.get('story_code')}")
                    
                    # Execute original function
                    result = await func(state, **kwargs)
                    
                    # Calculate duration
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Prepare detailed output
                    node_output = {
                        "status": "completed",
                        "duration_ms": round(duration_ms, 2),
                    }
                    
                    # Add node-specific output (handle None result)
                    if result is not None:
                        if node_name == "plan":
                            node_output["total_steps"] = result.get("total_steps", 0)
                            node_output["files_count"] = len(result.get("plan", {}).get("steps", []))
                        elif node_name in ["implement", "implement_parallel"]:
                            node_output["files_modified"] = result.get("files_modified", [])
                            parallel_errors = result.get("parallel_errors")
                            node_output["parallel_errors"] = len(parallel_errors) if parallel_errors else 0
                        elif node_name == "review":
                            node_output["review_result"] = result.get("review_result", "LGTM")
                        elif node_name == "run_code":
                            node_output["run_status"] = result.get("run_status", "UNKNOWN")
                            node_output["build_success"] = result.get("run_status") == "PASS"
                    else:
                        # Result is None - node returned nothing
                        node_output["status"] = "completed_no_output"
                    
                    # Update span with output
                    span.update(
                        output=node_output,
                        metadata={
                            **metadata,
                            "duration_ms": round(duration_ms, 2),
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                    )
                    
                    logger.info(f"[track_node] Completed {node_name} in {duration_ms:.0f}ms")
                    
                    return result
                    
            except Exception as e:
                # If Langfuse fails, still execute the function
                logger.warning(f"[track_node] Langfuse tracking failed for {node_name}: {e}", exc_info=True)
                return await func(state, **kwargs)
        
        return wrapper
    return decorator


def get_callback_config(state: dict, name: str) -> dict | None:
    """Get callback config for Langfuse tracing (Team Leader pattern).
    
    Returns LangChain CallbackHandler for detailed LLM tracking.
    Handler bridges LangChain → Langfuse, capturing tokens, cost, model info.
    
    Args:
        state: Graph state containing 'langfuse_handler'
        name: Name for this specific LLM call (observation name)
        
    Returns:
        Config dict with callbacks and run_name, or None if no handler
    """
    handler = state.get("langfuse_handler")
    return {"callbacks": [handler], "run_name": name} if handler else None


# Alias for backward compatibility
get_langfuse_config = get_callback_config


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
