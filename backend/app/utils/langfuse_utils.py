"""LangFuse utility module for agent tracking and monitoring.

This module provides utilities for initializing and managing LangFuse
callback handlers across different agents.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def get_langfuse_config() -> Dict[str, Any]:
    """Get LangFuse configuration from environment variables.
    
    Returns:
        dict: LangFuse configuration with keys:
            - public_key: LANGFUSE_PUBLIC_KEY
            - secret_key: LANGFUSE_SECRET_KEY
            - host: LANGFUSE_HOST (optional)
            - enabled: Whether LangFuse is properly configured
    """
    config = {
        "public_key": os.getenv("LANGFUSE_PUBLIC_KEY"),
        "secret_key": os.getenv("LANGFUSE_SECRET_KEY"),
        "host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        "enabled": False
    }
    
    # Check if LangFuse is properly configured
    if config["public_key"] and config["secret_key"]:
        config["enabled"] = True
    
    return config


def initialize_langfuse_handler(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    agent_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Initialize LangFuse callback handler with proper error handling.
    
    Args:
        session_id: Session ID for tracing
        user_id: User ID for tracking
        agent_type: Type of agent (sprint_planner, retro_coordinator, daily_coordinator)
        metadata: Additional metadata to track
    
    Returns:
        CallbackHandler or None: LangFuse callback handler if configured, None otherwise
    """
    try:
        from langfuse.langchain import CallbackHandler
    except ImportError:
        logger.warning("LangFuse not installed. Skipping LangFuse integration.")
        return None
    
    config = get_langfuse_config()
    
    if not config["enabled"]:
        logger.debug("LangFuse not configured. Skipping LangFuse integration.")
        return None
    
    try:
        # Prepare metadata
        handler_metadata = {
            "session_id": session_id,
            "user_id": user_id,
            "agent_type": agent_type,
            "timestamp": datetime.now().isoformat(),
        }
        
        if metadata:
            handler_metadata.update(metadata)
        
        # Initialize handler with aggressive flushing to avoid 413 errors
        handler = CallbackHandler(
            flush_at=1,  # Flush immediately after each event (prevents 413 errors)
            flush_interval=0.5,  # Flush every 0.5 seconds
            tags=[agent_type] if agent_type else [],
            metadata=handler_metadata
        )
        
        logger.info(f"LangFuse handler initialized for {agent_type} agent")
        return handler
        
    except TypeError:
        # Fallback for older versions without flush_at parameter
        try:
            handler = CallbackHandler()
            logger.info(f"LangFuse handler initialized (fallback) for {agent_type} agent")
            return handler
        except Exception as e:
            logger.error(f"Failed to initialize LangFuse handler: {e}")
            return None
    except Exception as e:
        logger.error(f"Failed to initialize LangFuse handler: {e}")
        return None


def create_langfuse_metadata(
    agent_type: str,
    sprint_id: Optional[str] = None,
    sprint_name: Optional[str] = None,
    date: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create metadata dictionary for LangFuse tracking.
    
    Args:
        agent_type: Type of agent (sprint_planner, retro_coordinator, daily_coordinator)
        sprint_id: Sprint ID (optional)
        sprint_name: Sprint name (optional)
        date: Date (optional)
        additional_data: Additional metadata (optional)
    
    Returns:
        dict: Metadata dictionary for LangFuse
    """
    metadata = {
        "agent_type": agent_type,
        "timestamp": datetime.now().isoformat(),
    }
    
    if sprint_id:
        metadata["sprint_id"] = sprint_id
    
    if sprint_name:
        metadata["sprint_name"] = sprint_name
    
    if date:
        metadata["date"] = date
    
    if additional_data:
        metadata.update(additional_data)
    
    return metadata


def log_node_execution(
    node_name: str,
    agent_type: str,
    input_data: Optional[Dict[str, Any]] = None,
    output_data: Optional[Dict[str, Any]] = None,
    execution_time: Optional[float] = None,
    error: Optional[str] = None
) -> None:
    """Log node execution for debugging and monitoring.
    
    Args:
        node_name: Name of the node
        agent_type: Type of agent
        input_data: Input data to the node
        output_data: Output data from the node
        execution_time: Execution time in seconds
        error: Error message if any
    """
    log_message = f"[{agent_type}] Node: {node_name}"
    
    if execution_time:
        log_message += f" | Time: {execution_time:.2f}s"
    
    if error:
        logger.error(f"{log_message} | Error: {error}")
    else:
        logger.info(log_message)
    
    if input_data:
        logger.debug(f"  Input: {input_data}")
    
    if output_data:
        logger.debug(f"  Output: {output_data}")


def is_langfuse_enabled() -> bool:
    """Check if LangFuse is enabled.
    
    Returns:
        bool: True if LangFuse is properly configured, False otherwise
    """
    config = get_langfuse_config()
    return config["enabled"]


def get_langfuse_session_id(
    base_session_id: Optional[str] = None,
    agent_type: Optional[str] = None
) -> str:
    """Generate a LangFuse session ID.
    
    Args:
        base_session_id: Base session ID
        agent_type: Type of agent
    
    Returns:
        str: LangFuse session ID
    """
    if base_session_id and agent_type:
        return f"{base_session_id}_{agent_type}"
    elif base_session_id:
        return base_session_id
    else:
        return f"session_{datetime.now().timestamp()}"

