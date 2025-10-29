"""Vestaboard Cloud API client implementation."""

import logging
import time
from typing import Dict, List, Optional, Union

import requests

from .base import BaseVestaboardClient, RateLimitMixin
from .board_types import BoardType
from .utils import debug_layout_preview


class VestaboardClient(BaseVestaboardClient, RateLimitMixin):
    """Client for interacting with the Vestaboard Cloud Read/Write API."""

    BASE_URL = "https://rw.vestaboard.com/"
    RATE_LIMIT_SECONDS = 15  # Cloud API rate limit

    def __init__(
        self,
        api_key: str,
        board_type: BoardType = BoardType.STANDARD,
        max_queue_size: int = 10
    ):
        """Initialize the Vestaboard Cloud API client.

        Args:
            api_key: The Read/Write API key from Vestaboard settings
            board_type: BoardType enum (default: BoardType.STANDARD)
            max_queue_size: Maximum number of messages to queue when rate limited
        """
        RateLimitMixin.__init__(self, self.RATE_LIMIT_SECONDS, max_queue_size)

        self.api_key = api_key
        self.board_type = board_type
        self.headers = {
            "X-Vestaboard-Read-Write-Key": api_key,
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized Cloud API client for {board_type} board")

    @property
    def board_rows(self) -> int:
        """Number of rows on the board (backward compatibility)."""
        return self.board_type.rows

    @property
    def board_cols(self) -> int:
        """Number of columns on the board (backward compatibility)."""
        return self.board_type.cols

    @property
    def _api_label(self) -> str:
        """API type label for logging."""
        return ""  # Cloud API doesn't need a label

    def read_current_message(self) -> Optional[Dict]:
        """Read the current message from the Vestaboard.

        Returns:
            Dictionary containing current message layout and ID, or None if error
        """
        try:
            self.logger.debug("Reading current message from Vestaboard")
            response = requests.get(self.BASE_URL, headers=self.headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            message_id = result.get('currentMessage', {}).get('id', 'unknown')
            self.logger.info(f"Successfully read current message (ID: {message_id})")
            return result

        except requests.RequestException as e:
            self.logger.error(f"Error reading current message: {e}")
            return None

    def write_message(self, message: Union[str, List[List[int]]]) -> bool:
        """Write a message to the Vestaboard with rate limiting.

        Args:
            message: Either a text string or a 6x22 array of character codes

        Returns:
            True if successful or queued, False if failed
        """
        if self._can_send_now():
            return self._send_message_direct(message)
        else:
            return self._queue_message(message)

    def get_current_layout(self) -> Optional[List[List[int]]]:
        """Get the current message layout array.

        Returns:
            Layout array of character codes matching board dimensions, or None if error
        """
        current = self.read_current_message()
        if current and "currentMessage" in current:
            return current["currentMessage"]["layout"]
        return None

    def _send_message_direct(self, message: Union[str, List[List[int]]]) -> bool:
        """Send message directly to Vestaboard API without rate limiting checks.

        Args:
            message: Either a text string or a 6x22 array of character codes

        Returns:
            True if successful, False otherwise
        """
        try:
            if isinstance(message, str):
                payload = {"text": message}
                self.logger.info(f"Writing text message to Vestaboard: '{message}'")
            else:
                payload = message
                self.logger.info(f"Writing layout array to Vestaboard ({self.board_type})")
                debug_layout_preview(message, self.logger)

            response = requests.post(
                self.BASE_URL,
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 429:
                self.logger.warning("Received 429 rate limit response from Vestaboard API")
                return False

            response.raise_for_status()

            result = response.json()
            message_id = result.get('id', 'unknown')
            self.logger.info(f"Successfully wrote message to Vestaboard (ID: {message_id})")

            self.last_send_time = time.time()
            return True

        except requests.RequestException as e:
            return self._handle_request_error(e)

    def _handle_request_error(self, error: requests.RequestException) -> bool:
        """Handle request errors with consistent logging.

        Args:
            error: The RequestException that occurred

        Returns:
            False (indicating failure)
        """
        self.logger.error(f"Error writing message: {error}")

        if hasattr(error, 'response') and error.response is not None:
            if error.response.status_code == 429:
                self.logger.warning("Hit Vestaboard rate limit (429)")
            try:
                error_detail = error.response.json()
                self.logger.error(f"API Error Details: {error_detail}")
            except (ValueError, AttributeError):
                self.logger.error(f"HTTP Status: {error.response.status_code}")

        return False

    def cleanup(self):
        """Clean up any active timers and resources."""
        self._cleanup_rate_limiting()

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except Exception:
            pass  # Silently ignore cleanup errors during destruction
