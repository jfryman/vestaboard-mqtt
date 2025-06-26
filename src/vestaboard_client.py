"""Vestaboard API client for reading and writing messages."""

import requests
import json
from typing import Dict, List, Optional, Union
from .logger import setup_logger


class VestaboardClient:
    """Client for interacting with the Vestaboard Read/Write API."""
    
    def __init__(self, api_key: str):
        """Initialize the Vestaboard client.
        
        Args:
            api_key: The Read/Write API key from Vestaboard settings
        """
        self.api_key = api_key
        self.base_url = "https://rw.vestaboard.com/"
        self.headers = {
            "X-Vestaboard-Read-Write-Key": api_key,
            "Content-Type": "application/json"
        }
        self.logger = setup_logger(__name__)
    
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
        """Write a message to the Vestaboard.
        
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
            response.raise_for_status()
            
            result = response.json()
            message_id = result.get('id', 'unknown')
            self.logger.info(f"Successfully wrote message to Vestaboard (ID: {message_id})")
            return True
        except requests.RequestException as e:
            self.logger.error(f"Error writing message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    self.logger.error(f"API Error Details: {error_detail}")
                except:
                    self.logger.error(f"HTTP Status: {e.response.status_code}")
            return False
    
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