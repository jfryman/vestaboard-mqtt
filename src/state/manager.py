"""Save state manager for storing and retrieving Vestaboard states via MQTT."""

import json
import logging
import time
from typing import Any, Dict, List, Optional, TypedDict, TYPE_CHECKING

import paho.mqtt.client as mqtt

if TYPE_CHECKING:
    from ..vestaboard import BaseVestaboardClient
    from ..config import AppConfig


class SaveData(TypedDict):
    """Structure for saved Vestaboard state data."""
    layout: List[List[int]]
    saved_at: int
    original_id: str


class SaveStateManager:
    """Manages save and restore functionality for Vestaboard states.

    Provides persistent storage of Vestaboard display states using MQTT
    retained messages. Supports saving, restoring, and deleting states
    by named slots.
    """

    def __init__(
        self,
        mqtt_client: mqtt.Client,
        vestaboard_client: 'BaseVestaboardClient',
        topic_prefix: str = "vestaboard"
    ):
        """Initialize the save state manager.

        Args:
            mqtt_client: Connected MQTT client
            vestaboard_client: Vestaboard API client
            topic_prefix: Base topic prefix (default: "vestaboard")
        """
        self.mqtt_client = mqtt_client
        self.vestaboard_client = vestaboard_client
        self.save_topic_prefix = f"{topic_prefix.rstrip('/')}/states/"
        self.logger = logging.getLogger(__name__)

    def _get_slot_topic(self, slot: str) -> str:
        """Generate the MQTT topic for a given slot.

        Args:
            slot: The slot name

        Returns:
            Full MQTT topic path for the slot
        """
        return f"{self.save_topic_prefix}{slot}"

    def _publish_retained(self, topic: str, payload: Optional[str], operation: str) -> bool:
        """Publish a retained MQTT message with error handling.

        Args:
            topic: MQTT topic to publish to
            payload: Message payload (None for deletion)
            operation: Description of operation for logging

        Returns:
            True if publish succeeded, False otherwise
        """
        result = self.mqtt_client.publish(topic, payload, qos=1, retain=True)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            return True

        self.logger.error(f"Failed to {operation}: MQTT error code {result.rc}")
        return False

    def _create_save_data(self, current_message: Dict) -> SaveData:
        """Create save data structure from current message.

        Args:
            current_message: Current message from Vestaboard API

        Returns:
            SaveData dictionary with layout and metadata
        """
        return {
            "layout": current_message["currentMessage"]["layout"],
            "saved_at": int(time.time()),
            "original_id": current_message["currentMessage"]["id"]
        }

    def save_current_state(self, slot: str) -> bool:
        """Save the current Vestaboard state to a persistent MQTT message.

        Args:
            slot: The slot name to save to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read current message from Vestaboard
            current_message = self.vestaboard_client.read_current_message()
            if not current_message:
                self.logger.error(f"Failed to read current message for save to slot '{slot}'")
                return False

            # Create and publish save data
            save_data = self._create_save_data(current_message)
            topic = self._get_slot_topic(slot)

            if self._publish_retained(topic, json.dumps(save_data), f"save state to slot '{slot}'"):
                self.logger.info(f"Saved current state to slot '{slot}'")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error saving state to slot '{slot}': {e}")
            return False

    def restore_state(self, slot: str) -> bool:
        """Restore a saved state from MQTT and write it to the Vestaboard.

        Note: This method delegates to the MQTT bridge to avoid
        subscription conflicts with save operations.

        Args:
            slot: The slot name to restore from

        Returns:
            True - The actual restoration is handled by the MQTT bridge
        """
        self.logger.debug(f"Restore request for slot '{slot}' will be handled by MQTT bridge")
        return True

    def _normalize_layout(self, layout_data: Any) -> Optional[List[List[int]]]:
        """Normalize layout data from various formats to a standard list format.

        Handles legacy formats including JSON strings and message wrappers.

        Args:
            layout_data: Layout in various possible formats

        Returns:
            Normalized layout as List[List[int]], or None if invalid
        """
        layout = layout_data

        # Handle JSON string format
        if isinstance(layout, str):
            self.logger.warning("Layout is a string, attempting to parse as JSON")
            try:
                layout = json.loads(layout)
                self.logger.info("Successfully parsed layout string to array")
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse layout string: {e}")
                return None

        # Handle Local API format with "message" wrapper (legacy format)
        if isinstance(layout, dict) and "message" in layout:
            self.logger.warning("Layout is wrapped in 'message' dict, extracting array")
            layout = layout["message"]
            self.logger.info("Successfully extracted layout from message wrapper")

        # Validate final format
        if not isinstance(layout, list):
            self.logger.error(f"Layout is not a list, it's {type(layout)}")
            return None

        return layout

    def restore_from_data(self, save_data: Dict) -> bool:
        """Restore state from save data dictionary.

        Supports multiple legacy layout formats for backward compatibility.

        Args:
            save_data: Dictionary containing layout and metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate save data structure
            if "layout" not in save_data:
                self.logger.error("Invalid save data: missing layout")
                return False

            # Normalize layout from various possible formats
            layout_data = save_data["layout"]
            self.logger.debug(f"Layout type: {type(layout_data)}")
            self.logger.debug(f"Layout preview: {str(layout_data)[:100]}...")

            layout = self._normalize_layout(layout_data)
            if layout is None:
                return False

            # Write to Vestaboard
            if not self.vestaboard_client.write_message(layout):
                self.logger.error("Failed to write restored state to Vestaboard")
                return False

            # Log success
            saved_at = save_data.get("saved_at", 0)
            self.logger.info(f"Restored state from {time.ctime(saved_at)}")
            return True

        except Exception as e:
            self.logger.error(f"Error restoring state: {e}")
            return False

    def delete_saved_state(self, slot: str) -> bool:
        """Delete a saved state by publishing an empty retained message.

        Args:
            slot: The slot name to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            topic = self._get_slot_topic(slot)

            if self._publish_retained(topic, None, f"delete state from slot '{slot}'"):
                self.logger.info(f"Deleted saved state from slot '{slot}'")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error deleting state from slot '{slot}': {e}")
            return False
