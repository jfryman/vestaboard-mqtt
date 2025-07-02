"""Vestaboard API client for reading and writing messages."""

import requests
import json
import time
import threading
from collections import deque
from typing import Dict, List, Optional, Union
from .logger import setup_logger


class VestaboardClient:
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