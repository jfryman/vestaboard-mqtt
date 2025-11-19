"""Vestaboard Local API client implementation."""

import logging
import time
from typing import Dict, List, Optional, Union

import requests

from .base import BaseVestaboardClient, RateLimitMixin
from .board_types import BoardType
from .constants import ANIMATION_STRATEGIES
from .utils import debug_layout_preview, text_to_layout


class LocalVestaboardClient(BaseVestaboardClient, RateLimitMixin):
    """Client for interacting with the Vestaboard Local API."""

    RATE_LIMIT_SECONDS = 1  # Local API has lower rate limits
    DEFAULT_HOST = "vestaboard.local"
    DEFAULT_PORT = 7000

    def __init__(
        self,
        api_key: str,
        board_type: BoardType = BoardType.STANDARD,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        max_queue_size: int = 10,
    ):
        """Initialize the Local Vestaboard client.

        Args:
            api_key: The Local API key from enablement
            board_type: BoardType enum (default: BoardType.STANDARD)
            host: Vestaboard device hostname or IP
            port: Local API port
            max_queue_size: Maximum number of messages to queue when rate limited
        """
        RateLimitMixin.__init__(self, self.RATE_LIMIT_SECONDS, max_queue_size)

        self.api_key = api_key
        self.board_type = board_type
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/local-api/message"
        self.headers = {"X-Vestaboard-Local-Api-Key": api_key, "Content-Type": "application/json"}
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized Local API client for {board_type} board at {host}:{port}")

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
        return "Local API"

    def read_current_message(self) -> Optional[Dict]:
        """Read the current message from the Vestaboard via Local API.

        Returns:
            Dictionary containing current message layout, or None if error
        """
        try:
            self.logger.debug("Reading current message from Vestaboard (Local API)")
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            layout = response.json()

            # Handle both direct array response and dict with "message" key
            if isinstance(layout, dict) and "message" in layout:
                self.logger.debug("Extracting layout from 'message' wrapper")
                layout = layout["message"]

            self.logger.info("Successfully read current message (Local API)")

            # Return in format consistent with cloud API
            return {
                "currentMessage": {
                    "layout": layout,
                    "id": f"local-{int(time.time())}",  # Generate pseudo-ID for consistency
                }
            }
        except requests.RequestException as e:
            self.logger.error(f"Error reading current message (Local API): {e}")
            return None

    def write_message(self, message: Union[str, List[List[int]]]) -> bool:
        """Write a message to the Vestaboard with rate limiting.

        Args:
            message: Either a text string or a layout array matching board dimensions

        Returns:
            True if successful or queued, False if failed
        """
        # Convert text messages to layout arrays for Local API
        if isinstance(message, str):
            try:
                message = text_to_layout(message, self.board_type)
            except Exception as e:
                self.logger.error(f"Failed to convert text to layout: {e}")
                return False

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

    def write_animated_message(
        self,
        message: Union[str, List[List[int]]],
        strategy: str = "column",
        step_interval_ms: Optional[int] = None,
        step_size: Optional[int] = None,
    ) -> bool:
        """Write an animated message to the Vestaboard with rate limiting.

        Args:
            message: Either a text string or a layout array matching board dimensions
            strategy: Animation strategy (e.g., 'column', 'reverse-column', 'edges-to-center')
            step_interval_ms: Optional delay in milliseconds between animation steps (1-60000)
            step_size: Optional number of updates to apply simultaneously (1-132)

        Returns:
            True if successful, False if failed or rate-limited
        """
        # Validate strategy
        if strategy not in ANIMATION_STRATEGIES:
            self.logger.error(
                f"Invalid animation strategy: {strategy}. "
                f"Valid options: {ANIMATION_STRATEGIES}"
            )
            return False

        # Validate animation parameters
        if not self._validate_step_interval_ms(step_interval_ms):
            return False
        if not self._validate_step_size(step_size):
            return False

        # Convert text to layout if needed
        if isinstance(message, str):
            try:
                message = text_to_layout(message, self.board_type)
            except Exception as e:
                self.logger.error(f"Failed to convert text to layout: {e}")
                return False

        # Send with rate limiting
        if self._can_send_now():
            return self._send_animated_message_direct(
                message, strategy, step_interval_ms, step_size
            )
        else:
            self.logger.warning(
                "Rate limit exceeded - animated message dropped. "
                "Consider increasing rate limit or spacing out requests."
            )
            return False

    def _validate_step_interval_ms(self, step_interval_ms: Optional[int]) -> bool:
        """Validate step_interval_ms parameter.

        Args:
            step_interval_ms: Optional delay in milliseconds between animation steps

        Returns:
            True if valid or None, False if invalid
        """
        if step_interval_ms is None:
            return True

        if not isinstance(step_interval_ms, int) or isinstance(step_interval_ms, bool):
            self.logger.error(
                f"step_interval_ms must be an integer, got {type(step_interval_ms).__name__}"
            )
            return False

        if step_interval_ms <= 0:
            self.logger.error(f"step_interval_ms must be positive, got {step_interval_ms}")
            return False

        if step_interval_ms > 60000:
            self.logger.error(
                f"step_interval_ms must be <= 60000ms (60s), got {step_interval_ms}"
            )
            return False

        return True

    def _validate_step_size(self, step_size: Optional[int]) -> bool:
        """Validate step_size parameter.

        Args:
            step_size: Optional number of updates to apply simultaneously

        Returns:
            True if valid or None, False if invalid
        """
        if step_size is None:
            return True

        if not isinstance(step_size, int) or isinstance(step_size, bool):
            self.logger.error(f"step_size must be an integer, got {type(step_size).__name__}")
            return False

        if step_size <= 0:
            self.logger.error(f"step_size must be positive, got {step_size}")
            return False

        max_cells = self.board_type.rows * self.board_type.cols
        if step_size > max_cells:
            self.logger.error(
                f"step_size must be <= {max_cells} (board size), got {step_size}"
            )
            return False

        return True

    def _send_message_direct(self, layout: List[List[int]]) -> bool:
        """Send layout directly to Vestaboard Local API without rate limiting checks.

        Args:
            layout: 6x22 array of character codes

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Writing layout array to Vestaboard (Local API - {self.board_type})")
            debug_layout_preview(layout, self.logger)

            response = requests.post(self.base_url, headers=self.headers, json=layout, timeout=10)

            if response.status_code == 429:
                self.logger.warning("Received 429 rate limit response from Vestaboard Local API")
                return False

            response.raise_for_status()

            self.logger.info("Successfully wrote message to Vestaboard (Local API)")
            self.last_send_time = time.time()
            return True

        except requests.RequestException as e:
            return self._handle_request_error(e)

    def _send_animated_message_direct(
        self,
        layout: List[List[int]],
        strategy: str,
        step_interval_ms: Optional[int],
        step_size: Optional[int],
    ) -> bool:
        """Send animated layout directly to Vestaboard Local API without rate limiting checks.

        Args:
            layout: Array of character codes matching board dimensions
            strategy: Animation strategy (e.g., 'column', 'reverse-column')
            step_interval_ms: Optional delay between animation steps
            step_size: Optional number of updates to apply simultaneously

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(
                f"Writing animated layout to Vestaboard (Local API - {self.board_type}, "
                f"strategy={strategy})"
            )
            debug_layout_preview(layout, self.logger)

            payload = {"characters": layout, "strategy": strategy}

            if step_interval_ms is not None:
                payload["step_interval_ms"] = step_interval_ms
            if step_size is not None:
                payload["step_size"] = step_size

            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=10)

            if response.status_code == 429:
                self.logger.warning("Received 429 rate limit response from Vestaboard Local API")
                return False

            response.raise_for_status()

            self.logger.info(
                f"Successfully wrote animated message to Vestaboard "
                f"(Local API, strategy={strategy})"
            )
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
        self.logger.error(f"Error writing message (Local API): {error}")

        if hasattr(error, "response") and error.response is not None:
            if error.response.status_code == 429:
                self.logger.warning("Hit Vestaboard rate limit (429) - Local API")
            try:
                error_detail = error.response.text
                self.logger.error(f"Local API Error Details: {error_detail}")
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
