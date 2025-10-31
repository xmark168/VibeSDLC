"""Response Queue Manager for WebSocket-based human-in-the-loop interactions.

This module provides infrastructure for agents to ask questions via WebSocket
and wait for user responses asynchronously.
"""

import asyncio
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
        # Store pending questions: {project_id: {question_id: Event}}
        self._pending: dict[str, dict[str, asyncio.Event]] = {}

        # Store responses: {project_id: {question_id: response}}
        self._responses: dict[str, dict[str, Any]] = {}

        # Lock for thread safety
        self._lock = asyncio.Lock()

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
        async with self._lock:
            # Create event for this question
            if project_id not in self._pending:
                self._pending[project_id] = {}

            event = asyncio.Event()
            self._pending[project_id][question_id] = event

        print(f"[ResponseManager] Waiting for response: project={project_id}, question={question_id}, timeout={timeout}s")

        try:
            # Wait for response with timeout
            await asyncio.wait_for(event.wait(), timeout=timeout)

            # Get response
            async with self._lock:
                response = self._responses.get(project_id, {}).get(question_id)

                # Cleanup
                if project_id in self._responses and question_id in self._responses[project_id]:
                    del self._responses[project_id][question_id]
                if project_id in self._pending and question_id in self._pending[project_id]:
                    del self._pending[project_id][question_id]

                print(f"[ResponseManager] Response received: {response}")
                return response

        except asyncio.TimeoutError:
            print(f"[ResponseManager] Timeout waiting for response: {question_id}")

            # Cleanup on timeout
            async with self._lock:
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

        async with self._lock:
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
            event.set()

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
