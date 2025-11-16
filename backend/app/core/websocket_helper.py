"""WebSocket Helper - Runs WebSocket operations in a dedicated event loop thread.

This solves the deadlock issue when calling async WebSocket operations from
sync contexts (like DeepAgent tools) while the main loop is blocked.
"""

import asyncio
import threading
from typing import Any, Callable, Coroutine
from concurrent.futures import Future


class WebSocketHelper:
    """Helper to run WebSocket operations in a dedicated thread with its own event loop."""

    def __init__(self):
        """Initialize WebSocket helper with dedicated thread and event loop."""
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()

    def start(self):
        """Start the dedicated event loop thread."""
        if self._thread is not None and self._thread.is_alive():
            return  # Already started

        def run_loop():
            """Run event loop in thread."""
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._started.set()  # Signal that loop is ready
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_loop, daemon=True, name="WebSocketHelperThread")
        self._thread.start()
        self._started.wait()  # Wait for loop to be ready

    def stop(self):
        """Stop the event loop thread."""
        if self._loop and self._thread:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)
            self._loop = None
            self._thread = None

    def run_coroutine(self, coro: Coroutine, timeout: float | None = None) -> Any:
        """Run a coroutine in the dedicated event loop and wait for result.

        Args:
            coro: Coroutine to run
            timeout: Optional timeout in seconds

        Returns:
            Result of the coroutine

        Raises:
            RuntimeError: If helper is not started
            TimeoutError: If timeout is exceeded
        """
        if not self._loop:
            raise RuntimeError("WebSocketHelper not started. Call start() first.")

        # Schedule coroutine in dedicated loop
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        # Wait for result
        return future.result(timeout=timeout)


# Global instance
websocket_helper = WebSocketHelper()
