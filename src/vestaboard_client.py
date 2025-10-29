"""Vestaboard API client for reading and writing messages."""

import logging
import time
import threading
from collections import deque
from typing import Dict, List, Optional, Union, TYPE_CHECKING
from abc import ABC, abstractmethod
from enum import Enum

import requests

if TYPE_CHECKING:
    from .config import AppConfig, VestaboardConfig


# Vestaboard character code mapping (shared across all clients)
# Official mapping from https://docs.vestaboard.com/docs/charactercodes/
CHAR_CODE_MAP = {
    0: ' ',   # blank
    **{i: chr(ord('A') + i - 1) for i in range(1, 27)},  # A-Z (1-26)
    27: '1', 28: '2', 29: '3', 30: '4', 31: '5', 32: '6',  # 1-9 (27-35)
    33: '7', 34: '8', 35: '9', 36: '0',                    # 0 is 36
    37: '!', 38: '@', 39: '#', 40: '$', 41: '(', 42: ')',  # punctuation
    44: '-', 46: '+', 47: '&', 48: '=', 49: ';', 50: ':',  # punctuation continued
    52: "'", 53: '"', 54: '%', 55: ',', 56: '.', 59: '/',  # punctuation continued
    60: '?', 62: '♥',  # question mark, heart (Note) / degree (Flagship)
    # Color codes
    63: '🟥', 64: '🟧', 65: '🟨', 66: '🟩', 67: '🟦', 68: '🟪',  # red, orange, yellow, green, blue, violet
    69: '⬜', 70: '⬛', 71: '⬛'  # white, black, filled
}

# Reverse mapping for text-to-code conversion
TEXT_TO_CODE_MAP = {
    ' ': 0,
    **{chr(ord('A') + i): i + 1 for i in range(26)},  # A-Z -> 1-26
    '1': 27, '2': 28, '3': 29, '4': 30, '5': 31,       # 1-9 -> 27-35
    '6': 32, '7': 33, '8': 34, '9': 35, '0': 36,       # 0 -> 36
    '!': 37, '@': 38, '#': 39, '$': 40, '(': 41, ')': 42,  # punctuation
    '-': 44, '+': 46, '&': 47, '=': 48, ';': 49, ':': 50,  # punctuation continued
    "'": 52, '"': 53, '%': 54, ',': 55, '.': 56, '/': 59,  # punctuation continued
    '?': 60, '♥': 62, '❤': 62,  # question mark, heart (both ♥ and ❤ map to same code)
    # Color codes (emoji to code mapping)
    '🟥': 63, '🟧': 64, '🟨': 65, '🟩': 66, '🟦': 67, '🟪': 68,  # red, orange, yellow, green, blue, violet
    '⬜': 69, '⬛': 70, '■': 71  # white, black, filled
}


class BoardType(Enum):
    """Vestaboard board type with dimensions."""

    STANDARD = ("standard", 6, 22)  # Standard Vestaboard (6 rows x 22 columns)
    NOTE = ("note", 3, 15)           # Vestaboard Note (3 rows x 15 columns)

    def __init__(self, name: str, rows: int, cols: int):
        self._type_name = name
        self._rows = rows
        self._cols = cols

    @property
    def rows(self) -> int:
        """Number of rows on this board."""
        return self._rows

    @property
    def cols(self) -> int:
        """Number of columns on this board."""
        return self._cols

    @property
    def type_name(self) -> str:
        """String name of this board type."""
        return self._type_name

    @classmethod
    def from_string(cls, value: str) -> 'BoardType':
        """Parse board type from string.

        Args:
            value: Board type string ('standard' or 'note', case-insensitive)

        Returns:
            BoardType enum member

        Raises:
            ValueError: If value is not a valid board type

        Examples:
            >>> BoardType.from_string("standard")
            <BoardType.STANDARD: ('standard', 6, 22)>
            >>> BoardType.from_string("NOTE")
            <BoardType.NOTE: ('note', 3, 15)>
        """
        value_lower = value.lower().strip()

        if value_lower in ("standard", ""):
            return cls.STANDARD
        elif value_lower == "note":
            return cls.NOTE
        else:
            raise ValueError(f"Unknown board_type: '{value}'. Valid options: 'standard' or 'note'")

    def __str__(self) -> str:
        """String representation."""
        return f"{self.type_name} ({self.rows}x{self.cols})"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"BoardType.{self.name}"


# Constants
DEFAULT_PREVIEW_ROWS = 3
QUEUE_PROCESSING_DELAY = 0.1  # seconds between immediate queue processing attempts


def _format_log_suffix(label: str) -> str:
    """Format an optional log message suffix for API type labels.

    Args:
        label: API type label (e.g., "Local API")

    Returns:
        Formatted suffix string or empty string
    """
    return f" - {label}" if label else ""




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
                log_suffix = _format_log_suffix(self._api_label)
                self.logger.info(f"Message queued due to rate limit (queue size: {queue_len}){log_suffix}")

                if not self.processing_queue:
                    self._schedule_queue_processing()

                return True
            except Exception as e:
                log_suffix = _format_log_suffix(self._api_label)
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
            self.queue_timer = threading.Timer(
                time_until_next_send,
                self._process_queue
            )
            self.queue_timer.start()

            log_suffix = _format_log_suffix(self._api_label)
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
            log_suffix = _format_log_suffix(self._api_label)
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
                log_suffix = _format_log_suffix(self._api_label)
                self.logger.warning(f"Discarding {queue_size} queued messages{log_suffix}")
                self.message_queue.clear()


def debug_layout_preview(
    layout: List[List[int]],
    logger,
    max_preview_rows: int = DEFAULT_PREVIEW_ROWS
) -> None:
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


def text_to_layout(text: str, board_type: BoardType) -> List[List[int]]:
    """Convert text string to layout array.

    This is a simplified conversion that centers text on the first row.
    For production use, consider using Vestaboard's text-to-layout service
    or implementing more sophisticated text wrapping.

    Args:
        text: Text string to convert
        board_type: BoardType enum specifying board dimensions

    Returns:
        Layout array matching board dimensions

    Examples:
        >>> # Standard Vestaboard
        >>> text_to_layout("HELLO", BoardType.STANDARD)  # Returns 6x22 array
        >>> # Vestaboard Note
        >>> text_to_layout("HELLO", BoardType.NOTE)  # Returns 3x15 array
    """
    # Create empty layout
    layout = [[0 for _ in range(board_type.cols)] for _ in range(board_type.rows)]

    # Simple centering on first row
    text_upper = text.upper()[:board_type.cols]  # Truncate to fit width
    start_col = max(0, (board_type.cols - len(text_upper)) // 2)

    for i, char in enumerate(text_upper):
        if start_col + i < board_type.cols:
            layout[0][start_col + i] = TEXT_TO_CODE_MAP.get(char, 0)

    return layout


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
        max_queue_size: int = 10
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
        self.headers = {
            "X-Vestaboard-Local-Api-Key": api_key,
            "Content-Type": "application/json"
        }
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
            return self._handle_request_error(e)

    def _handle_request_error(self, error: requests.RequestException) -> bool:
        """Handle request errors with consistent logging.

        Args:
            error: The RequestException that occurred

        Returns:
            False (indicating failure)
        """
        self.logger.error(f"Error writing message (Local API): {error}")

        if hasattr(error, 'response') and error.response is not None:
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


def create_vestaboard_client(
    api_key: Optional[str] = None,
    board_type: BoardType = BoardType.STANDARD,
    use_local_api: bool = False,
    local_host: str = "vestaboard.local",
    local_port: int = 7000,
    max_queue_size: int = 10,
    config: Optional['VestaboardConfig'] = None
) -> BaseVestaboardClient:
    """Factory function to create appropriate Vestaboard client.

    All configuration is explicit - no environment variable reading.
    For environment-based configuration, use AppConfig.from_env() and pass
    config.vestaboard to this function.

    Args:
        api_key: API key (cloud or local), required unless config is provided
        board_type: BoardType enum (default: BoardType.STANDARD)
        use_local_api: If True, use Local API; if False, use Cloud API
        local_host: Hostname for Local API (default: vestaboard.local)
        local_port: Port for Local API (default: 7000)
        max_queue_size: Maximum queue size for rate limiting (default: 10)
        config: VestaboardConfig object (overrides other parameters if provided)

    Returns:
        VestaboardClient or LocalVestaboardClient instance

    Raises:
        ValueError: If required parameters are missing

    Examples:
        >>> # Standard Vestaboard with Cloud API
        >>> client = create_vestaboard_client(api_key="...")

        >>> # Vestaboard Note with Local API
        >>> client = create_vestaboard_client(
        ...     api_key="...",
        ...     board_type=BoardType.NOTE,
        ...     use_local_api=True,
        ...     local_host="192.168.1.100"
        ... )

        >>> # Using config object from environment
        >>> from config import AppConfig
        >>> app_config = AppConfig.from_env()
        >>> client = create_vestaboard_client(config=app_config.vestaboard)
    """
    logger = logging.getLogger(__name__)

    # If config is provided, extract all values from it
    if config is not None:
        # Determine which API key to use based on config
        if config.use_local_api and config.local_api_key:
            api_key = config.local_api_key
        elif config.api_key:
            api_key = config.api_key
        elif config.local_api_key:
            api_key = config.local_api_key
        else:
            raise ValueError("No API key found in VestaboardConfig")

        # Parse board type from config string
        board_type = BoardType.from_string(config.board_type)

        # Get local API settings from config
        use_local_api = config.use_local_api or bool(config.local_api_key and not config.api_key)
        local_host = config.local_host
        local_port = config.local_port
        max_queue_size = config.max_queue_size

    # Validate required parameters
    if not api_key:
        raise ValueError("api_key is required")

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
