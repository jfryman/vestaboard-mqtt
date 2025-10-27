"""Vestaboard API client for reading and writing messages."""

import requests
import json
import time
import threading
import os
from collections import deque
from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod
from .logger import setup_logger


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


class VestaboardClient(BaseVestaboardClient):
    """Client for interacting with the Vestaboard Read/Write API."""
    
    def __init__(self, api_key: str, max_queue_size: int = 10):
        """Initialize the Vestaboard client.
        
        Args:
            api_key: The Read/Write API key from Vestaboard settings
            max_queue_size: Maximum number of messages to queue when rate limited
        """
        self.api_key = api_key
        self.base_url = "https://rw.vestaboard.com/"
        self.headers = {
            "X-Vestaboard-Read-Write-Key": api_key,
            "Content-Type": "application/json"
        }
        self.logger = setup_logger(__name__)
        
        # Rate limiting state
        self.rate_limit_seconds = 15
        self.last_send_time = 0
        self.message_queue = deque(maxlen=max_queue_size)
        self.queue_lock = threading.RLock()
        self.processing_queue = False
        self.queue_timer = None
    
    def read_current_message(self) -> Optional[Dict]:
        """Read the current message from the Vestaboard.
        
        Returns:
            Dictionary containing current message layout and ID, or None if error
        """
        try:
            self.logger.debug("Reading current message from Vestaboard")
            response = requests.get(self.base_url, headers=self.headers)
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
        # Check if we can send immediately
        if self._can_send_now():
            return self._send_message_direct(message)
        else:
            # Queue the message for later sending
            return self._queue_message(message)
    
    def get_current_layout(self) -> Optional[List[List[int]]]:
        """Get the current message layout as a 6x22 array.
        
        Returns:
            6x22 array of character codes, or None if error
        """
        current = self.read_current_message()
        if current and "currentMessage" in current:
            return current["currentMessage"]["layout"]
        return None
    
    def _debug_layout_preview(self, layout: List[List[int]]):
        """Generate a readable preview of the layout array for debugging."""
        try:
            # Vestaboard character mapping (0=blank, 1-26=A-Z, 27-36=0-9, etc.)
            char_map = {
                0: ' ',   # blank
                **{i: chr(ord('A') + i - 1) for i in range(1, 27)},  # A-Z
                **{i: str(i - 27) for i in range(27, 37)},  # 0-9
                37: '!', 38: '@', 39: '#', 40: '$', 41: '(', 42: ')',
                44: '-', 46: '.', 47: '/', 59: ':', 63: '?', 64: '°'
            }
            
            # Convert first few rows to text for preview
            preview_lines = []
            for row_idx, row in enumerate(layout[:3]):  # Show first 3 rows
                line = ''.join(char_map.get(code, f'[{code}]') for code in row)
                preview_lines.append(f"Row {row_idx + 1}: '{line.strip()}'")
            
            if len(layout) > 3:
                preview_lines.append(f"... ({len(layout)} total rows)")
            
            for line in preview_lines:
                self.logger.debug(line)
            
        except Exception as e:
            self.logger.warning(f"Preview generation failed: {e}")
            self.logger.debug(f"Raw layout dimensions: {len(layout)}x{len(layout[0]) if layout else 0}")
    
    def _can_send_now(self) -> bool:
        """Check if we can send a message now based on rate limiting."""
        current_time = time.time()
        return (current_time - self.last_send_time) >= self.rate_limit_seconds
    
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
                self.logger.info(f"Message queued due to rate limit (queue size: {queue_len})")
                
                # Start processing if not already running
                if not self.processing_queue:
                    self._schedule_queue_processing()
                    
                return True
            except Exception as e:
                self.logger.error(f"Failed to queue message: {e}")
                return False
    
    def _schedule_queue_processing(self):
        """Schedule processing of the message queue."""
        with self.queue_lock:
            if self.queue_timer:
                self.queue_timer.cancel()
            
            time_until_next_send = self.rate_limit_seconds - (time.time() - self.last_send_time)
            if time_until_next_send <= 0:
                time_until_next_send = 0.1  # Process almost immediately
            
            self.processing_queue = True
            self.queue_timer = threading.Timer(time_until_next_send, self._process_queue)
            self.queue_timer.start()
            self.logger.debug(f"Scheduled queue processing in {time_until_next_send:.1f} seconds")
    
    def _process_queue(self):
        """Process messages from the queue."""
        with self.queue_lock:
            self.processing_queue = False
            
            if not self.message_queue:
                return
            
            if not self._can_send_now():
                # Still rate limited, reschedule
                self._schedule_queue_processing()
                return
            
            # Send the next message
            message = self.message_queue.popleft()
            queue_len = len(self.message_queue)
            self.logger.info(f"Processing queued message (remaining in queue: {queue_len})")
            
            success = self._send_message_direct(message)
            
            # If there are more messages and we succeeded, schedule next processing
            if self.message_queue and success:
                self._schedule_queue_processing()
    
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
                self.logger.info("Writing layout array to Vestaboard (6x22 matrix)")
                # Convert layout to a readable preview if possible
                self._debug_layout_preview(message)
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )
            
            # Check for rate limiting specifically
            if response.status_code == 429:
                self.logger.warning("Received 429 rate limit response from Vestaboard API")
                return False
            
            response.raise_for_status()
            
            result = response.json()
            message_id = result.get('id', 'unknown')
            self.logger.info(f"Successfully wrote message to Vestaboard (ID: {message_id})")
            
            # Update rate limiting timestamp on successful send
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
                except:
                    self.logger.error(f"HTTP Status: {e.response.status_code}")
            return False
    
    def cleanup(self):
        """Clean up any active timers and resources."""
        with self.queue_lock:
            if self.queue_timer:
                self.queue_timer.cancel()
                self.queue_timer = None
            self.processing_queue = False
            queue_size = len(self.message_queue)
            if queue_size > 0:
                self.logger.warning(f"Discarding {queue_size} queued messages during cleanup")
                self.message_queue.clear()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during cleanup


class LocalVestaboardClient(BaseVestaboardClient):
    """Client for interacting with the Vestaboard Local API."""
    
    def __init__(self, api_key: str, host: str = "vestaboard.local", port: int = 7000, max_queue_size: int = 10):
        """Initialize the Local Vestaboard client.
        
        Args:
            api_key: The Local API key from enablement
            host: Vestaboard device hostname or IP (default: vestaboard.local)
            port: Local API port (default: 7000)
            max_queue_size: Maximum number of messages to queue when rate limited
        """
        self.api_key = api_key
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/local-api/message"
        self.headers = {
            "X-Vestaboard-Local-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        self.logger = setup_logger(__name__)
        
        # Rate limiting state - Local API may have different limits
        self.rate_limit_seconds = 1  # Local API typically has lower rate limits
        self.last_send_time = 0
        self.message_queue = deque(maxlen=max_queue_size)
        self.queue_lock = threading.RLock()
        self.processing_queue = False
        self.queue_timer = None
    
    def read_current_message(self) -> Optional[Dict]:
        """Read the current message from the Vestaboard via Local API.
        
        Returns:
            Dictionary containing current message layout, or None if error
        """
        try:
            self.logger.debug("Reading current message from Vestaboard (Local API)")
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            
            layout = response.json()
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
            message: Either a text string or a 6x22 array of character codes
            
        Returns:
            True if successful or queued, False if failed
        """
        # Convert text messages to layout arrays for Local API
        if isinstance(message, str):
            layout = self._text_to_layout(message)
            if layout is None:
                self.logger.error("Failed to convert text to layout array")
                return False
            message = layout
        
        # Check if we can send immediately
        if self._can_send_now():
            return self._send_message_direct(message)
        else:
            # Queue the message for later sending
            return self._queue_message(message)
    
    def get_current_layout(self) -> Optional[List[List[int]]]:
        """Get the current message layout as a 6x22 array.
        
        Returns:
            6x22 array of character codes, or None if error
        """
        current = self.read_current_message()
        if current and "currentMessage" in current:
            return current["currentMessage"]["layout"]
        return None
    
    def _text_to_layout(self, text: str) -> Optional[List[List[int]]]:
        """Convert text string to 6x22 layout array.
        
        This is a simplified conversion - for production use, you might want
        to use Vestaboard's text-to-layout conversion service or implement
        more sophisticated text wrapping.
        
        Args:
            text: Text string to convert
            
        Returns:
            6x22 layout array or None if conversion fails
        """
        try:
            # Character mapping (simplified - extend as needed)
            char_map = {
                ' ': 0,
                **{chr(ord('A') + i): i + 1 for i in range(26)},  # A-Z -> 1-26
                **{str(i): i + 27 for i in range(10)},  # 0-9 -> 27-36
                '!': 37, '@': 38, '#': 39, '$': 40, '(': 41, ')': 42,
                '-': 44, '.': 46, '/': 47, ':': 59, '?': 63, '°': 64
            }
            
            # Create empty 6x22 layout
            layout = [[0 for _ in range(22)] for _ in range(6)]
            
            # Simple centering on first row
            text = text.upper()[:22]  # Truncate to fit width
            start_col = max(0, (22 - len(text)) // 2)
            
            for i, char in enumerate(text):
                if start_col + i < 22:
                    layout[0][start_col + i] = char_map.get(char, 0)
            
            return layout
            
        except Exception as e:
            self.logger.error(f"Error converting text to layout: {e}")
            return None
    
    def _debug_layout_preview(self, layout: List[List[int]]):
        """Generate a readable preview of the layout array for debugging."""
        try:
            # Vestaboard character mapping (0=blank, 1-26=A-Z, 27-36=0-9, etc.)
            char_map = {
                0: ' ',   # blank
                **{i: chr(ord('A') + i - 1) for i in range(1, 27)},  # A-Z
                **{i: str(i - 27) for i in range(27, 37)},  # 0-9
                37: '!', 38: '@', 39: '#', 40: '$', 41: '(', 42: ')',
                44: '-', 46: '.', 47: '/', 59: ':', 63: '?', 64: '°'
            }
            
            # Convert first few rows to text for preview
            preview_lines = []
            for row_idx, row in enumerate(layout[:3]):  # Show first 3 rows
                line = ''.join(char_map.get(code, f'[{code}]') for code in row)
                preview_lines.append(f"Row {row_idx + 1}: '{line.strip()}'")
            
            if len(layout) > 3:
                preview_lines.append(f"... ({len(layout)} total rows)")
            
            for line in preview_lines:
                self.logger.debug(line)
            
        except Exception as e:
            self.logger.warning(f"Preview generation failed: {e}")
            self.logger.debug(f"Raw layout dimensions: {len(layout)}x{len(layout[0]) if layout else 0}")
    
    def _can_send_now(self) -> bool:
        """Check if we can send a message now based on rate limiting."""
        current_time = time.time()
        return (current_time - self.last_send_time) >= self.rate_limit_seconds
    
    def _queue_message(self, message: List[List[int]]) -> bool:
        """Add a message to the queue.
        
        Args:
            message: Layout array to queue
            
        Returns:
            True if queued successfully, False if queue is full
        """
        with self.queue_lock:
            try:
                self.message_queue.append(message)
                queue_len = len(self.message_queue)
                self.logger.info(f"Message queued due to rate limit (queue size: {queue_len}) - Local API")
                
                # Start processing if not already running
                if not self.processing_queue:
                    self._schedule_queue_processing()
                    
                return True
            except Exception as e:
                self.logger.error(f"Failed to queue message (Local API): {e}")
                return False
    
    def _schedule_queue_processing(self):
        """Schedule processing of the message queue."""
        with self.queue_lock:
            if self.queue_timer:
                self.queue_timer.cancel()
            
            time_until_next_send = self.rate_limit_seconds - (time.time() - self.last_send_time)
            if time_until_next_send <= 0:
                time_until_next_send = 0.1  # Process almost immediately
            
            self.processing_queue = True
            self.queue_timer = threading.Timer(time_until_next_send, self._process_queue)
            self.queue_timer.start()
            self.logger.debug(f"Scheduled queue processing in {time_until_next_send:.1f} seconds (Local API)")
    
    def _process_queue(self):
        """Process messages from the queue."""
        with self.queue_lock:
            self.processing_queue = False
            
            if not self.message_queue:
                return
            
            if not self._can_send_now():
                # Still rate limited, reschedule
                self._schedule_queue_processing()
                return
            
            # Send the next message
            message = self.message_queue.popleft()
            queue_len = len(self.message_queue)
            self.logger.info(f"Processing queued message (remaining in queue: {queue_len}) - Local API")
            
            success = self._send_message_direct(message)
            
            # If there are more messages and we succeeded, schedule next processing
            if self.message_queue and success:
                self._schedule_queue_processing()
    
    def _send_message_direct(self, layout: List[List[int]]) -> bool:
        """Send layout directly to Vestaboard Local API without rate limiting checks.
        
        Args:
            layout: 6x22 array of character codes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Writing layout array to Vestaboard (Local API - 6x22 matrix)")
            self._debug_layout_preview(layout)
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=layout
            )
            
            # Check for rate limiting specifically
            if response.status_code == 429:
                self.logger.warning("Received 429 rate limit response from Vestaboard Local API")
                return False
            
            response.raise_for_status()
            
            self.logger.info("Successfully wrote message to Vestaboard (Local API)")
            
            # Update rate limiting timestamp on successful send
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
                except:
                    self.logger.error(f"HTTP Status: {e.response.status_code}")
            return False
    
    def cleanup(self):
        """Clean up any active timers and resources."""
        with self.queue_lock:
            if self.queue_timer:
                self.queue_timer.cancel()
                self.queue_timer = None
            self.processing_queue = False
            queue_size = len(self.message_queue)
            if queue_size > 0:
                self.logger.warning(f"Discarding {queue_size} queued messages during cleanup (Local API)")
                self.message_queue.clear()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during cleanup


def create_vestaboard_client(api_key: str = None, use_local_api: bool = None, 
                           local_host: str = None, local_port: int = None, 
                           max_queue_size: int = 10) -> BaseVestaboardClient:
    """Factory function to create appropriate Vestaboard client.
    
    Args:
        api_key: API key (cloud or local)
        use_local_api: If True, use Local API; if False, use Cloud API; if None, auto-detect from env
        local_host: Hostname for Local API (default: vestaboard.local)
        local_port: Port for Local API (default: 7000)
        max_queue_size: Maximum queue size for rate limiting
        
    Returns:
        VestaboardClient or LocalVestaboardClient instance
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Get configuration from environment if not provided
    if api_key is None:
        # Try local API key first, then cloud API key
        api_key = os.getenv("VESTABOARD_LOCAL_API_KEY") or os.getenv("VESTABOARD_API_KEY")
        if not api_key:
            raise ValueError("No API key provided via parameter or environment variables")
    
    if use_local_api is None:
        # Auto-detect: if VESTABOARD_LOCAL_API_KEY is set or USE_LOCAL_API is true, use local
        use_local_api = bool(os.getenv("VESTABOARD_LOCAL_API_KEY")) or \
                       os.getenv("USE_LOCAL_API", "").lower() in ("true", "1", "yes")
    
    if local_host is None:
        local_host = os.getenv("VESTABOARD_LOCAL_HOST", "vestaboard.local")
    
    if local_port is None:
        local_port = int(os.getenv("VESTABOARD_LOCAL_PORT", "7000"))
    
    if use_local_api:
        logger = setup_logger(__name__)
        logger.info(f"Creating Local API client for {local_host}:{local_port}")
        return LocalVestaboardClient(
            api_key=api_key,
            host=local_host,
            port=local_port,
            max_queue_size=max_queue_size
        )
    else:
        logger = setup_logger(__name__)
        logger.info("Creating Cloud API client")
        return VestaboardClient(
            api_key=api_key,
            max_queue_size=max_queue_size
        )