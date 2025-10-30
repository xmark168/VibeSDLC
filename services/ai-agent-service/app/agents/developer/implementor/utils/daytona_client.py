"""
Daytona Client Utility

Utility functions for managing Daytona sandbox lifecycle in Implementor Agent.
"""

import asyncio
import os
import threading
from typing import Optional

from daytona import AsyncDaytona, DaytonaConfig


def get_daytona_config() -> DaytonaConfig:
    """
    Get Daytona configuration from environment variables.

    Required environment variables:
    - DAYTONA_API_KEY: API key for authentication
    - DAYTONA_API_URL: API URL (defaults to https://app.daytona.io/api)
    - DAYTONA_TARGET: Target runner location (defaults to 'us')

    Returns:
        DaytonaConfig object for client initialization

    Raises:
        ValueError: If required environment variables are missing
    """
    api_key = os.getenv("DAYTONA_API_KEY")
    if not api_key:
        raise ValueError(
            "DAYTONA_API_KEY environment variable is required for Daytona operations"
        )

    api_url = os.getenv("DAYTONA_API_URL", "https://app.daytona.io/api")
    target = os.getenv("DAYTONA_TARGET", "us")

    return DaytonaConfig(api_key=api_key, api_url=api_url, target=target)


async def _delete_sandbox_async(sandbox_id: str, max_retries: int = 2) -> dict:
    """
    Delete Daytona sandbox asynchronously with retry logic.

    Args:
        sandbox_id: ID of the sandbox to delete
        max_retries: Maximum number of retry attempts (default: 2)

    Returns:
        Dictionary with deletion result:
        {
            "success": bool,
            "message": str,
            "sandbox_id": str,
            "retries_used": int,
            "error": str (if failed)
        }
    """
    result = {
        "success": False,
        "message": "",
        "sandbox_id": sandbox_id,
        "retries_used": 0,
        "error": ""
    }

    if not sandbox_id or sandbox_id.strip() == "":
        result["error"] = "Invalid sandbox_id provided"
        result["message"] = "Cannot delete sandbox: invalid ID"
        return result

    try:
        # Get Daytona configuration
        daytona_config = get_daytona_config()
        
        # Attempt deletion with retries
        for attempt in range(max_retries + 1):
            try:
                async with AsyncDaytona(daytona_config) as daytona:
                    # Delete the sandbox
                    await daytona.delete(sandbox_id)
                    
                    result["success"] = True
                    result["message"] = f"Sandbox {sandbox_id} deleted successfully"
                    result["retries_used"] = attempt
                    return result
                    
            except Exception as e:
                result["retries_used"] = attempt
                error_msg = str(e)
                
                # Check if it's a "not found" error (sandbox already deleted)
                if "not found" in error_msg.lower() or "404" in error_msg:
                    result["success"] = True
                    result["message"] = f"Sandbox {sandbox_id} was already deleted or not found"
                    return result
                
                # If this is the last attempt, record the error
                if attempt == max_retries:
                    result["error"] = error_msg
                    result["message"] = f"Failed to delete sandbox after {max_retries + 1} attempts: {error_msg}"
                else:
                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(2 ** attempt)
                    
    except ValueError as e:
        # Configuration error
        result["error"] = str(e)
        result["message"] = f"Daytona configuration error: {str(e)}"
    except Exception as e:
        # Unexpected error
        result["error"] = str(e)
        result["message"] = f"Unexpected error during sandbox deletion: {str(e)}"

    return result


def delete_sandbox_sync(sandbox_id: str, max_retries: int = 2) -> dict:
    """
    Synchronous wrapper for deleting Daytona sandbox.

    This function runs the async deletion in a separate thread to avoid
    event loop conflicts with LangGraph's synchronous node requirements.

    Args:
        sandbox_id: ID of the sandbox to delete
        max_retries: Maximum number of retry attempts (default: 2)

    Returns:
        Dictionary with deletion result:
        {
            "success": bool,
            "message": str,
            "sandbox_id": str,
            "retries_used": int,
            "error": str (if failed)
        }
    """
    result = None
    exception = None

    def run_in_thread():
        nonlocal result, exception
        try:
            # Create a new event loop for this thread
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                result = new_loop.run_until_complete(
                    _delete_sandbox_async(sandbox_id, max_retries)
                )
            finally:
                new_loop.close()
        except Exception as e:
            exception = e

    # Run in separate thread
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join(timeout=60)  # 60 seconds timeout for deletion

    if thread.is_alive():
        # Timeout occurred
        return {
            "success": False,
            "message": f"Sandbox deletion timed out after 60 seconds",
            "sandbox_id": sandbox_id,
            "retries_used": 0,
            "error": "Timeout"
        }

    if exception:
        return {
            "success": False,
            "message": f"Exception during sandbox deletion: {str(exception)}",
            "sandbox_id": sandbox_id,
            "retries_used": 0,
            "error": str(exception)
        }

    return result or {
        "success": False,
        "message": "Unknown error during sandbox deletion",
        "sandbox_id": sandbox_id,
        "retries_used": 0,
        "error": "Unknown error"
    }


def should_delete_sandbox(status: str, sandbox_id: Optional[str]) -> bool:
    """
    Determine if sandbox should be deleted based on workflow status.

    Args:
        status: Current workflow status
        sandbox_id: Sandbox ID (if any)

    Returns:
        True if sandbox should be deleted, False otherwise
    """
    # Only delete if we have a valid sandbox ID
    if not sandbox_id or sandbox_id.strip() == "":
        return False
    
    # Only delete on successful completion
    # Don't delete on errors so user can debug
    success_statuses = ["completed", "pr_ready", "finalized"]
    
    return status in success_statuses
