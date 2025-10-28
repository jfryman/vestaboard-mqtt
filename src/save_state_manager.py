"""Save state manager for storing and retrieving Vestaboard states via MQTT."""

import json
import time
from typing import Dict, List, Optional
import paho.mqtt.client as mqtt
from .vestaboard_client import BaseVestaboardClient
from .logger import setup_logger


class SaveStateManager:
    """Manages save and restore functionality for Vestaboard states."""

    def __init__(self, mqtt_client: mqtt.Client, vestaboard_client: BaseVestaboardClient, topic_prefix: str = "vestaboard"):
        """Initialize the save state manager.

        Args:
            mqtt_client: Connected MQTT client
            vestaboard_client: Vestaboard API client
            topic_prefix: Base topic prefix (default: "vestaboard")
        """
        self.mqtt_client = mqtt_client
        self.vestaboard_client = vestaboard_client
        self.save_topic_prefix = f"{topic_prefix.rstrip('/')}/states/"
        self.logger = setup_logger(__name__)
    
    def save_current_state(self, slot: str) -> bool:
        """Save the current Vestaboard state to a persistent MQTT message.
        
        Args:
            slot: The slot name to save to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            current_message = self.vestaboard_client.read_current_message()
            if not current_message:
                self.logger.error(f"Failed to read current message for save to slot '{slot}'")
                return False
            
            # Create save state data
            save_data = {
                "layout": current_message["currentMessage"]["layout"],
                "saved_at": int(time.time()),
                "original_id": current_message["currentMessage"]["id"]
            }
            
            # Publish as retained message for persistence
            topic = f"{self.save_topic_prefix}{slot}"
            result = self.mqtt_client.publish(
                topic,
                json.dumps(save_data),
                qos=1,
                retain=True
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Saved current state to slot '{slot}'")
                return True
            else:
                self.logger.error(f"Failed to save state to slot '{slot}': {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving state to slot '{slot}': {e}")
            return False
    
    def restore_state(self, slot: str) -> bool:
        """Restore a saved state from MQTT and write it to the Vestaboard.
        
        This method is now handled by the MQTT bridge directly to avoid
        subscription conflicts with save operations.
        
        Args:
            slot: The slot name to restore from
            
        Returns:
            True - The actual restoration is handled by the MQTT bridge
        """
        # The MQTT bridge handles the temporary subscription and restoration
        self.logger.debug(f"Restore request for slot '{slot}' will be handled by MQTT bridge")
        return True
    
    def restore_from_data(self, save_data: Dict) -> bool:
        """Restore state from save data dictionary.
        
        Args:
            save_data: Dictionary containing layout and metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if "layout" not in save_data:
                self.logger.error("Invalid save data: missing layout")
                return False
            
            layout = save_data["layout"]
            self.logger.debug(f"Layout type: {type(layout)}")
            self.logger.debug(f"Layout preview: {str(layout)[:100]}...")
            
            # Ensure layout is a proper array, not a string
            if isinstance(layout, str):
                self.logger.warning("Layout is a string, attempting to parse as JSON")
                try:
                    layout = json.loads(layout)
                    self.logger.info("Successfully parsed layout string to array")
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse layout string: {e}")
                    return False
            
            if not isinstance(layout, list):
                self.logger.error(f"Layout is not a list, it's {type(layout)}")
                return False
            
            success = self.vestaboard_client.write_message(layout)
            
            if success:
                saved_at = save_data.get("saved_at", 0)
                self.logger.info(f"Restored state from {time.ctime(saved_at)}")
                return True
            else:
                self.logger.error("Failed to write restored state to Vestaboard")
                return False
                
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
            topic = f"{self.save_topic_prefix}{slot}"
            # Publish empty retained message to delete the retained state
            result = self.mqtt_client.publish(
                topic,
                None,  # Empty payload
                qos=1,
                retain=True
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Deleted saved state from slot '{slot}'")
                return True
            else:
                self.logger.error(f"Failed to delete state from slot '{slot}': {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting state from slot '{slot}': {e}")
            return False
    
    def list_saved_states(self) -> List[str]:
        """List available saved state slots.
        
        Note: This would require keeping track of published slots
        or using MQTT broker features to list retained topics.
        """
        # This is a placeholder - implementation would depend on MQTT broker capabilities
        pass