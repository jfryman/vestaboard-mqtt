"""Vestaboard API client for reading and writing messages."""

import os
import time
import threading
from collections import deque
from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod

import requests

from .logger import setup_logger


# Vestaboard character code mapping (shared across all clients)
# Official mapping from https://docs.vestaboard.com/docs/charactercodes/
CHAR_CODE_MAP = {
    0: ' ',   # blank
    **{i: chr(ord('A') + i - 1) for i in range(1, 27)},  # A-Z (1-26)
    27: '1', 28: '2', 29: '3', 30: '4', 31: '5', 32: '6',  # 1-9 (27-35)
    33: '7', 34: '8', 35: '9', 36: '0',                    # 0 is 36
    37: '!', 38: '@', 39: '#', 40: '$', 41: '(', 42: ')',
    44: '-', 46: '.', 47: '/', 59: ':', 63: '?', 64: '°'
}

# Reverse mapping for text-to-code conversion
TEXT_TO_CODE_MAP = {
    ' ': 0,
    **{chr(ord('A') + i): i + 1 for i in range(26)},  # A-Z -> 1-26
    '1': 27, '2': 28, '3': 29, '4': 30, '5': 31,       # 1-9 -> 27-35
    '6': 32, '7': 33, '8': 34, '9': 35, '0': 36,       # 0 -> 36
    '!': 37, '@': 38, '#': 39, '$': 40, '(': 41, ')': 42,
    '-': 44, '.': 46, '/': 47, ':': 59, '?': 63, '°': 64
}

# Board dimensions for different Vestaboard models
class BoardType:
    """Vestaboard board type dimensions (rows, cols)."""
    # Standard Vestaboard (6 rows x 22 columns)
    STANDARD = (6, 22)
    # Vestaboard Note (3 rows x 15 columns)
    NOTE = (3, 15)

# Constants
PREVIEW_ROWS = 3
IMMEDIATE_PROCESSING_DELAY = 0.1  # seconds


class BaseVestaboardClient(ABC):
    """Abstract base class for Vestaboard clients."""

    @abstractmethod
    def read_current_message(self) -> Optional[Dict]:
        """Read the current message from the Vestaboard."""
        pass

    @abstractmethod
    def write_message(self, message: Union[str, List[List[int]]]) -> bool:
        """Write a message to the Vestaboard."""
        pass

    @abstractmethod
    def get_current_layout(self) -> Optional[List[List[int]]]:
        """Get the current message layout as a 6x22 array."""
        pass

    @abstractmethod
    def cleanup(self):
        """Clean up any active timers and resources."""
        pass


class RateLimitMixin:
    """Mixin providing rate limiting and message queue functionality."""

    def __init__(self, rate_limit_seconds: float, max_queue_size: int):
        """Initialize rate limiting.

        Args:
            rate_limit_seconds: Minimum seconds between API calls
            max_queue_size: Maximum number of queued messages
        """
        self.rate_limit_seconds = rate_limit_seconds
        self.last_send_time = 0.0
        self.message_queue = deque(maxlen=max_queue_size)
        self.queue_lock = threading.RLock()
        self.processing_queue = False
        self.queue_timer: Optional[threading.Timer] = None

    def _can_send_now(self) -> bool:
        """Check if we can send a message now based on rate limiting."""
        return (time.time() - self.last_send_time) >= self.rate_limit_seconds

    def _queue_message(self, message: Union[str, List[List[int]]], api_type: str = "") -> bool:
        """Add a message to the queue.

        Args:
            message: Message to queue
            api_type: API type label for logging (e.g., "Local API")

        Returns:
            True if queued successfully, False if queue is full
        """
        with self.queue_lock:
            try:
                self.message_queue.append(message)
                queue_len = len(self.message_queue)
                log_suffix = f" - {api_type}" if api_type else ""
                self.logger.info(f"Message queued due to rate limit (queue size: {queue_len}){log_suffix}")

                if not self.processing_queue:
                    self._schedule_queue_processing(api_type)

                return True
            except Exception as e:
                log_suffix = f" ({api_type})" if api_type else ""
                self.logger.error(f"Failed to queue message{log_suffix}: {e}")
                return False

    def _schedule_queue_processing(self, api_type: str = ""):
        """Schedule processing of the message queue.

        Args:
            api_type: API type label for logging
        """
        with self.queue_lock:
            if self.queue_timer:
                self.queue_timer.cancel()

            time_until_next_send = self.rate_limit_seconds - (time.time() - self.last_send_time)
            if time_until_next_send <= 0:
                time_until_next_send = IMMEDIATE_PROCESSING_DELAY

            self.processing_queue = True
            self.queue_timer = threading.Timer(
                time_until_next_send,
                lambda: self._process_queue(api_type)
            )
            self.queue_timer.start()

            log_suffix = f" ({api_type})" if api_type else ""
            self.logger.debug(
                f"Scheduled queue processing in {time_until_next_send:.1f} seconds{log_suffix}"
            )

    def _process_queue(self, api_type: str = ""):
        """Process messages from the queue.

        Args:
            api_type: API type label for logging
        """
        with self.queue_lock:
            self.processing_queue = False

            if not self.message_queue:
                return

            if not self._can_send_now():
                self._schedule_queue_processing(api_type)
                return

            message = self.message_queue.popleft()
            queue_len = len(self.message_queue)
            log_suffix = f" - {api_type}" if api_type else ""
            self.logger.info(f"Processing queued message (remaining: {queue_len}){log_suffix}")

            success = self._send_message_direct(message)

            if self.message_queue and success:
                self._schedule_queue_processing(api_type)

    def _cleanup_rate_limiting(self, api_type: str = ""):
        """Clean up rate limiting resources.

        Args:
            api_type: API type label for logging
        """
        with self.queue_lock:
            if self.queue_timer:
                self.queue_timer.cancel()
                self.queue_timer = None

            self.processing_queue = False
            queue_size = len(self.message_queue)

            if queue_size > 0:
                log_suffix = f" ({api_type})" if api_type else ""
                self.logger.warning(f"Discarding {queue_size} queued messages{log_suffix}")
                self.message_queue.clear()


def debug_layout_preview(layout: List[List[int]], logger, max_preview_rows: int = PREVIEW_ROWS) -> None:
    """Generate a readable preview of the layout array for debugging.

    Args:
        layout: Layout array (any dimensions)
        logger: Logger instance for output
        max_preview_rows: Maximum number of rows to preview
    """
    try:
        if not layout:
            logger.debug("Empty layout")
            return

        rows = len(layout)
        cols = len(layout[0]) if layout else 0

        preview_lines = []
        for row_idx, row in enumerate(layout[:max_preview_rows]):
            line = ''.join(CHAR_CODE_MAP.get(code, f'[{code}]') for code in row)
            preview_lines.append(f"Row {row_idx + 1}: '{line.strip()}'")

        if rows > max_preview_rows:
            preview_lines.append(f"... ({rows} total rows)")

        logger.debug(f"Layout preview ({rows}x{cols}):")
        for line in preview_lines:
            logger.debug(line)

    except Exception as e:
        logger.warning(f"Preview generation failed: {e}")
        try:
            logger.debug(f"Raw layout dimensions: {len(layout)}x{len(layout[0]) if layout else 0}")
        except Exception:
            logger.debug("Unable to determine layout dimensions")


def text_to_layout(text: str, rows: int, cols: int) -> List[List[int]]:
    """Convert text string to layout array.

    This is a simplified conversion that centers text on the first row.
    For production use, consider using Vestaboard's text-to-layout service
    or implementing more sophisticated text wrapping.

    Args:
        text: Text string to convert
        rows: Number of rows in the layout
        cols: Number of columns in the layout

    Returns:
        Layout array of specified dimensions

    Examples:
        >>> # Standard Vestaboard
        >>> text_to_layout("HELLO", *BoardType.STANDARD)  # Returns 6x22 array
        >>> # Vestaboard Note
        >>> text_to_layout("HELLO", *BoardType.NOTE)  # Returns 3x15 array
    """
    # Create empty layout
    layout = [[0 for _ in range(cols)] for _ in range(rows)]

    # Simple centering on first row
    text_upper = text.upper()[:cols]  # Truncate to fit width
    start_col = max(0, (cols - len(text_upper)) // 2)

    for i, char in enumerate(text_upper):
        if start_col + i < cols:
            layout[0][start_col + i] = TEXT_TO_CODE_MAP.get(char, 0)

    return layout


class VestaboardClient(BaseVestaboardClient, RateLimitMixin):
    """Client for interacting with the Vestaboard Cloud Read/Write API."""

    BASE_URL = "https://rw.vestaboard.com/"
    RATE_LIMIT_SECONDS = 15  # Cloud API rate limit

    def __init__(
        self,
        api_key: str,
        board_type: tuple[int, int] = BoardType.STANDARD,
        max_queue_size: int = 10
    ):
        """Initialize the Vestaboard Cloud API client.

        Args:
            api_key: The Read/Write API key from Vestaboard settings
            board_type: Board dimensions as (rows, cols) tuple (default: BoardType.STANDARD)
            max_queue_size: Maximum number of messages to queue when rate limited
        """
        RateLimitMixin.__init__(self, self.RATE_LIMIT_SECONDS, max_queue_size)

        self.api_key = api_key
        self.board_rows, self.board_cols = board_type
        self.headers = {
            "X-Vestaboard-Read-Write-Key": api_key,
            "Content-Type": "application/json"
        }
        self.logger = setup_logger(__name__)
        self.logger.info(f"Initialized Cloud API client for {self.board_rows}x{self.board_cols} board")

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
                self.logger.info(f"Writing layout array to Vestaboard ({self.board_rows}x{self.board_cols})")
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
            self.logger.error(f"Error writing message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 429:
                    self.logger.warning("Hit Vestaboard rate limit (429)")
                try:
                    error_detail = e.response.json()
                    self.logger.error(f"API Error Details: {error_detail}")
                except (ValueError, AttributeError):
                    self.logger.error(f"HTTP Status: {e.response.status_code}")
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


class LocalVestaboardClient(BaseVestaboardClient, RateLimitMixin):
    """Client for interacting with the Vestaboard Local API."""

    RATE_LIMIT_SECONDS = 1  # Local API has lower rate limits
    DEFAULT_HOST = "vestaboard.local"
    DEFAULT_PORT = 7000

    def __init__(
        self,
        api_key: str,
        board_type: tuple[int, int] = BoardType.STANDARD,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        max_queue_size: int = 10
    ):
        """Initialize the Local Vestaboard client.

        Args:
            api_key: The Local API key from enablement
            board_type: Board dimensions as (rows, cols) tuple (default: BoardType.STANDARD)
            host: Vestaboard device hostname or IP
            port: Local API port
            max_queue_size: Maximum number of messages to queue when rate limited
        """
        RateLimitMixin.__init__(self, self.RATE_LIMIT_SECONDS, max_queue_size)

        self.api_key = api_key
        self.board_rows, self.board_cols = board_type
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/local-api/message"
        self.headers = {
            "X-Vestaboard-Local-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        self.logger = setup_logger(__name__)
        self.logger.info(f"Initialized Local API client for {self.board_rows}x{self.board_cols} board at {host}:{port}")

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
                    "id": f"local-{int(time.time())}"  # Generate pseudo-ID for consistency
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
                message = text_to_layout(message, self.board_rows, self.board_cols)
            except Exception as e:
                self.logger.error(f"Failed to convert text to layout: {e}")
                return False

        if self._can_send_now():
            return self._send_message_direct(message)
        else:
            return self._queue_message(message, "Local API")

    def get_current_layout(self) -> Optional[List[List[int]]]:
        """Get the current message layout array.

        Returns:
            Layout array of character codes matching board dimensions, or None if error
        """
        current = self.read_current_message()
        if current and "currentMessage" in current:
            return current["currentMessage"]["layout"]
        return None

    def _send_message_direct(self, layout: List[List[int]]) -> bool:
        """Send layout directly to Vestaboard Local API without rate limiting checks.

        Args:
            layout: 6x22 array of character codes

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Writing layout array to Vestaboard (Local API - {self.board_rows}x{self.board_cols})")
            debug_layout_preview(layout, self.logger)

            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=layout,
                timeout=10
            )

            if response.status_code == 429:
                self.logger.warning("Received 429 rate limit response from Vestaboard Local API")
                return False

            response.raise_for_status()

            self.logger.info("Successfully wrote message to Vestaboard (Local API)")
            self.last_send_time = time.time()
            return True

        except requests.RequestException as e:
            self.logger.error(f"Error writing message (Local API): {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 429:
                    self.logger.warning("Hit Vestaboard rate limit (429) - Local API")
                try:
                    error_detail = e.response.text
                    self.logger.error(f"Local API Error Details: {error_detail}")
                except (ValueError, AttributeError):
                    self.logger.error(f"HTTP Status: {e.response.status_code}")
            return False

    def cleanup(self):
        """Clean up any active timers and resources."""
        self._cleanup_rate_limiting("Local API")

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except Exception:
            pass  # Silently ignore cleanup errors during destruction


def create_vestaboard_client(
    api_key: Optional[str] = None,
    board_type: Optional[tuple[int, int]] = None,
    use_local_api: Optional[bool] = None,
    local_host: Optional[str] = None,
    local_port: Optional[int] = None,
    max_queue_size: int = 10
) -> BaseVestaboardClient:
    """Factory function to create appropriate Vestaboard client.

    This function auto-detects the API type from environment variables if not
    explicitly specified. Priority order for API key detection:
    1. api_key parameter
    2. VESTABOARD_LOCAL_API_KEY environment variable
    3. VESTABOARD_API_KEY environment variable

    Board type can be specified via VESTABOARD_BOARD_TYPE environment variable:
    - "standard" or "STANDARD" -> BoardType.STANDARD (6x22)
    - "note" or "NOTE" -> BoardType.NOTE (3x15)
    - Or custom dimensions as "rows,cols" (e.g., "3,15")

    Args:
        api_key: API key (cloud or local). If None, read from environment
        board_type: Board dimensions as (rows, cols) tuple. If None, reads from
                   VESTABOARD_BOARD_TYPE env var or defaults to BoardType.STANDARD
        use_local_api: If True, use Local API; if False, use Cloud API;
                      if None, auto-detect from environment
        local_host: Hostname for Local API (default from env or vestaboard.local)
        local_port: Port for Local API (default from env or 7000)
        max_queue_size: Maximum queue size for rate limiting

    Returns:
        VestaboardClient or LocalVestaboardClient instance

    Raises:
        ValueError: If no API key is provided or found in environment, or if
                   board_type environment variable has invalid format

    Examples:
        >>> # Standard Vestaboard with Cloud API
        >>> client = create_vestaboard_client(api_key="...", board_type=BoardType.STANDARD)
        >>> # Vestaboard Note with Local API
        >>> client = create_vestaboard_client(
        ...     api_key="...",
        ...     board_type=BoardType.NOTE,
        ...     use_local_api=True,
        ...     local_host="192.168.1.100"
        ... )
        >>> # Using environment variables
        >>> # export VESTABOARD_BOARD_TYPE=note
        >>> client = create_vestaboard_client()  # Auto-detects as 3x15
    """
    logger = setup_logger(__name__)

    # Auto-detect API key from environment if not provided
    if api_key is None:
        api_key = os.getenv("VESTABOARD_LOCAL_API_KEY") or os.getenv("VESTABOARD_API_KEY")
        if not api_key:
            raise ValueError(
                "No API key provided. Set VESTABOARD_API_KEY or "
                "VESTABOARD_LOCAL_API_KEY environment variable, or pass api_key parameter"
            )

    # Auto-detect board type from environment if not provided
    if board_type is None:
        board_type_env = os.getenv("VESTABOARD_BOARD_TYPE", "standard").lower()
        if board_type_env in ("standard", ""):
            board_type = BoardType.STANDARD
        elif board_type_env == "note":
            board_type = BoardType.NOTE
        elif "," in board_type_env:
            # Custom dimensions as "rows,cols"
            try:
                rows, cols = board_type_env.split(",")
                board_type = (int(rows.strip()), int(cols.strip()))
            except (ValueError, AttributeError) as e:
                raise ValueError(
                    f"Invalid VESTABOARD_BOARD_TYPE format: '{board_type_env}'. "
                    f"Use 'standard', 'note', or 'rows,cols' (e.g., '3,15')"
                ) from e
        else:
            raise ValueError(
                f"Unknown VESTABOARD_BOARD_TYPE: '{board_type_env}'. "
                f"Use 'standard', 'note', or 'rows,cols' (e.g., '3,15')"
            )

    # Auto-detect API type if not specified
    if use_local_api is None:
        use_local_api = bool(os.getenv("VESTABOARD_LOCAL_API_KEY")) or \
                       os.getenv("USE_LOCAL_API", "").lower() in ("true", "1", "yes")

    # Get Local API configuration from environment
    if local_host is None:
        local_host = os.getenv("VESTABOARD_LOCAL_HOST", LocalVestaboardClient.DEFAULT_HOST)

    if local_port is None:
        local_port = int(os.getenv("VESTABOARD_LOCAL_PORT", str(LocalVestaboardClient.DEFAULT_PORT)))

    # Create appropriate client
    if use_local_api:
        logger.info(f"Creating Local API client for {local_host}:{local_port}")
        return LocalVestaboardClient(
            api_key=api_key,
            board_type=board_type,
            host=local_host,
            port=local_port,
            max_queue_size=max_queue_size
        )
    else:
        logger.info("Creating Cloud API client")
        return VestaboardClient(
            api_key=api_key,
            board_type=board_type,
            max_queue_size=max_queue_size
        )
