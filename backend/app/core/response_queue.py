"""Response Queue Manager for WebSocket-based human-in-the-loop interactions.

This module provides infrastructure for agents to ask questions via WebSocket
and wait for user responses asynchronously.
"""

import asyncio
import threading
import uuid
from typing import Any, Optional
from datetime import datetime


class ResponseManager:
    """Manages pending questions and awaits user responses via WebSocket.

    Usage:
        # In agent code
        question_id = str(uuid.uuid4())

        # Send question via WebSocket
        await websocket_broadcast_fn({
            "type": "agent_question",
            "question_id": question_id,
            "question": "What is your target audience?"
        }, project_id)

        # Wait for response
        answer = await response_manager.await_response(
            project_id,
            question_id,
            timeout=600
        )
    """

    def __init__(self):
        """Initialize ResponseManager."""
        # Store pending questions: {project_id: {question_id: threading.Event}}
        # Use threading.Event instead of asyncio.Event for cross-loop support
        self._pending: dict[str, dict[str, threading.Event]] = {}

        # Store responses: {project_id: {question_id: response}}
        self._responses: dict[str, dict[str, Any]] = {}

        # Lock for thread safety (use threading.Lock, not asyncio.Lock)
        self._lock = threading.Lock()

        # Broadcast queue for messages that need to be sent from main loop
        # Format: (message_data, project_id)
        self._broadcast_queue: asyncio.Queue = asyncio.Queue()

    def get_broadcast_queue(self) -> asyncio.Queue:
        """Get the broadcast queue for WebSocket messages."""
        return self._broadcast_queue

    async def queue_broadcast(self, message_data: dict, project_id: str):
        """Queue a message to be broadcast from main loop.

        This is thread-safe and can be called from any thread.
        """
        await self._broadcast_queue.put((message_data, project_id))
        print(f"[ResponseManager] Message queued for broadcast: {message_data.get('type')}", flush=True)

    async def await_response(
        self,
        project_id: str,
        question_id: str,
        timeout: float = 600.0
    ) -> Optional[Any]:
        """Wait for user response to a question.

        Args:
            project_id: Project ID
            question_id: Unique question ID
            timeout: Timeout in seconds (default 10 minutes)

        Returns:
            User's response, or None if timeout
        """
        # Create threading.Event for cross-loop support
        with self._lock:
            # Create event for this question
            if project_id not in self._pending:
                self._pending[project_id] = {}

            event = threading.Event()
            self._pending[project_id][question_id] = event

        print(f"[ResponseManager] Waiting for response: project={project_id}, question={question_id}, timeout={timeout}s", flush=True)

        # Wait for event in executor to not block event loop
        import asyncio
        loop = asyncio.get_event_loop()

        def wait_for_event():
            """Wait for threading.Event (blocking)"""
            return event.wait(timeout=timeout)

        try:
            # Run blocking wait in executor
            result = await loop.run_in_executor(None, wait_for_event)

            if result:
                # Event was set, get response
                with self._lock:
                    response = self._responses.get(project_id, {}).get(question_id)

                    # Cleanup
                    if project_id in self._responses and question_id in self._responses[project_id]:
                        del self._responses[project_id][question_id]
                    if project_id in self._pending and question_id in self._pending[project_id]:
                        del self._pending[project_id][question_id]

                    print(f"[ResponseManager] Response received: {response}", flush=True)
                    return response
            else:
                # Timeout
                print(f"[ResponseManager] Timeout waiting for response: {question_id}", flush=True)

                # Cleanup on timeout
                with self._lock:
                    if project_id in self._pending and question_id in self._pending[project_id]:
                        del self._pending[project_id][question_id]

                return None

        except Exception as e:
            print(f"[ResponseManager] Error waiting for response: {e}", flush=True)
            # Cleanup on error
            with self._lock:
                if project_id in self._pending and question_id in self._pending[project_id]:
                    del self._pending[project_id][question_id]
            return None

    async def submit_response(
        self,
        project_id: str,
        question_id: str,
        answer: Any
    ) -> bool:
        """Submit user response to a pending question.

        Args:
            project_id: Project ID
            question_id: Question ID
            answer: User's answer

        Returns:
            True if question was pending, False otherwise
        """
        print(f"\n[ResponseManager] ===== submit_response called =====", flush=True)
        print(f"[ResponseManager] project_id: {project_id}", flush=True)
        print(f"[ResponseManager] question_id: {question_id}", flush=True)
        print(f"[ResponseManager] answer: {answer}", flush=True)

        with self._lock:
            # Debug: show all pending questions
            print(f"[ResponseManager] Current _pending projects: {list(self._pending.keys())}", flush=True)
            if project_id in self._pending:
                print(f"[ResponseManager] Pending questions for project {project_id}: {list(self._pending[project_id].keys())}", flush=True)
            else:
                print(f"[ResponseManager] ✗ Project {project_id} not in _pending!", flush=True)

            # Check if question is pending
            if project_id not in self._pending or question_id not in self._pending[project_id]:
                print(f"[ResponseManager] ✗ Question not found: {question_id}", flush=True)
                return False

            # Store response
            if project_id not in self._responses:
                self._responses[project_id] = {}

            self._responses[project_id][question_id] = answer

            # Trigger event to wake up awaiting agent
            event = self._pending[project_id][question_id]
            event.set()  # threading.Event.set() is thread-safe!

            print(f"[ResponseManager] ✓ Response submitted successfully: project={project_id}, question={question_id}", flush=True)
            return True

    def get_pending_questions(self, project_id: str) -> list[str]:
        """Get list of pending question IDs for a project.

        Args:
            project_id: Project ID

        Returns:
            List of question IDs
        """
        return list(self._pending.get(project_id, {}).keys())

    async def cancel_question(self, project_id: str, question_id: str) -> bool:
        """Cancel a pending question.

        Args:
            project_id: Project ID
            question_id: Question ID

        Returns:
            True if cancelled, False if not found
        """
        async with self._lock:
            if project_id in self._pending and question_id in self._pending[project_id]:
                # Set event to wake up with None response
                event = self._pending[project_id][question_id]

                # Store None as response
                if project_id not in self._responses:
                    self._responses[project_id] = {}
                self._responses[project_id][question_id] = None

                # Trigger event
                event.set()

                print(f"[ResponseManager] Question cancelled: {question_id}")
                return True

            return False


# Global instance
response_manager = ResponseManager()
