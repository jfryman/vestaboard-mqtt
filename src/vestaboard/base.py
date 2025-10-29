"""Base classes for Vestaboard clients."""

import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from typing import Dict, List, Optional, Union

from .constants import QUEUE_PROCESSING_DELAY
from .utils import format_log_suffix


class BaseVestaboardClient(ABC):
    """Abstract base class for Vestaboard clients."""

    @abstractmethod
    def read_current_message(self) -> Optional[Dict]:
        """Read the current message from the Vestaboard."""
        ...

    @abstractmethod
    def write_message(self, message: Union[str, List[List[int]]]) -> bool:
        """Write a message to the Vestaboard."""
        ...

    @abstractmethod
    def get_current_layout(self) -> Optional[List[List[int]]]:
        """Get the current message layout as a 6x22 array."""
        ...

    @abstractmethod
    def cleanup(self):
        """Clean up any active timers and resources."""
        ...


class RateLimitMixin:
    """Mixin providing rate limiting and message queue functionality.

    Classes using this mixin must provide:
    - logger: logging.Logger instance
    - _send_message_direct: method to send messages
    """

    # Type hints for attributes that must be provided by the using class
    logger: logging.Logger

    def _send_message_direct(self, message: Union[str, List[List[int]]]) -> bool:
        """Send a message directly (must be implemented by using class)."""
        raise NotImplementedError("_send_message_direct must be implemented by the using class")

    def __init__(self, rate_limit_seconds: float, max_queue_size: int):
        """Initialize rate limiting.

        Args:
            rate_limit_seconds: Minimum seconds between API calls
            max_queue_size: Maximum number of queued messages
        """
        self.rate_limit_seconds = rate_limit_seconds
        self.last_send_time = 0.0
        self.message_queue: deque = deque(maxlen=max_queue_size)
        self.queue_lock = threading.RLock()
        self.processing_queue = False
        self.queue_timer: Optional[threading.Timer] = None

    @property
    def _api_label(self) -> str:
        """Get the API type label for logging. Override in subclasses."""
        return ""

    def _can_send_now(self) -> bool:
        """Check if we can send a message now based on rate limiting."""
        return (time.time() - self.last_send_time) >= self.rate_limit_seconds

    def _queue_message(self, message: Union[str, List[List[int]]]) -> bool:
        """Add a message to the queue.

        Args:
            message: Message to queue

        Returns:
            True if queued successfully, False if queue is full
        """
        with self.queue_lock:
            try:
                self.message_queue.append(message)
                queue_len = len(self.message_queue)
                log_suffix = format_log_suffix(self._api_label)
                self.logger.info(
                    f"Message queued due to rate limit (queue size: {queue_len}){log_suffix}"
                )

                if not self.processing_queue:
                    self._schedule_queue_processing()

                return True
            except Exception as e:
                log_suffix = format_log_suffix(self._api_label)
                self.logger.error(f"Failed to queue message{log_suffix}: {e}")
                return False

    def _schedule_queue_processing(self):
        """Schedule processing of the message queue."""
        with self.queue_lock:
            if self.queue_timer:
                self.queue_timer.cancel()

            time_until_next_send = self.rate_limit_seconds - (time.time() - self.last_send_time)
            if time_until_next_send <= 0:
                time_until_next_send = QUEUE_PROCESSING_DELAY

            self.processing_queue = True
            self.queue_timer = threading.Timer(time_until_next_send, self._process_queue)
            self.queue_timer.start()

            log_suffix = format_log_suffix(self._api_label)
            self.logger.debug(
                f"Scheduled queue processing in {time_until_next_send:.1f} seconds{log_suffix}"
            )

    def _process_queue(self):
        """Process messages from the queue."""
        with self.queue_lock:
            self.processing_queue = False

            if not self.message_queue:
                return

            if not self._can_send_now():
                self._schedule_queue_processing()
                return

            message = self.message_queue.popleft()
            queue_len = len(self.message_queue)
            log_suffix = format_log_suffix(self._api_label)
            self.logger.info(f"Processing queued message (remaining: {queue_len}){log_suffix}")

            success = self._send_message_direct(message)

            if self.message_queue and success:
                self._schedule_queue_processing()

    def _cleanup_rate_limiting(self):
        """Clean up rate limiting resources."""
        with self.queue_lock:
            if self.queue_timer:
                self.queue_timer.cancel()
                self.queue_timer = None

            self.processing_queue = False
            queue_size = len(self.message_queue)

            if queue_size > 0:
                log_suffix = format_log_suffix(self._api_label)
                self.logger.warning(f"Discarding {queue_size} queued messages{log_suffix}")
                self.message_queue.clear()
