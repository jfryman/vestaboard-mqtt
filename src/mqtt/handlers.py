"""Message handlers for MQTT bridge."""

import json
import logging
import time
from typing import TYPE_CHECKING, Any, Optional

from ..vestaboard.local_client import LocalVestaboardClient
from .topics import Topics

if TYPE_CHECKING:
    import paho.mqtt.client as mqtt

    from .bridge import VestaboardMQTTBridge


class MessageHandlers:
    """Handles incoming MQTT messages for Vestaboard bridge."""

    def __init__(self, bridge: "VestaboardMQTTBridge"):
        """Initialize message handlers.

        Args:
            bridge: Parent MQTT bridge instance
        """
        self.bridge = bridge
        self.logger = logging.getLogger(__name__)

    def handle_message(self, payload: str, strategy: Optional[str] = None) -> None:
        """Handle message to display on Vestaboard.

        Args:
            payload: Message payload (text, JSON layout array, or JSON object with optional
                     step_interval_ms and step_size parameters)
            strategy: Optional animation strategy for Local API
        """
        try:
            message_content, step_interval_ms, step_size = self._parse_message_with_params(payload)

            # Determine if animation is requested and supported
            use_animation = strategy and isinstance(
                self.bridge.vestaboard_client, LocalVestaboardClient
            )

            # Send the message
            if use_animation:
                success = self.bridge.vestaboard_client.write_animated_message(
                    message=message_content,
                    strategy=strategy,
                    step_interval_ms=step_interval_ms,
                    step_size=step_size,
                )
                message_type = f"animated message (strategy={strategy})"
            else:
                if strategy:
                    self.logger.warning(
                        f"Animation strategy '{strategy}' ignored - only supported with Local API"
                    )
                success = self.bridge.vestaboard_client.write_message(message_content)
                message_type = "message"

            # Log the result
            self._log_send_result(success, message_type)

        except Exception as e:
            self.logger.error(f"Error handling message: {e}", exc_info=True)

    def handle_save(self, slot: str) -> None:
        """Handle save current state request.

        Args:
            slot: Save slot name
        """
        success = self.bridge.save_state_manager.save_current_state(slot)
        if success:
            self.logger.info(f"Saved current state to slot '{slot}'")
        else:
            self.logger.error(f"Failed to save state to slot '{slot}'")

    def handle_restore_request(self, slot: str, payload: str = "") -> None:
        """Handle restore state request with optional animation.

        Args:
            slot: Save slot name to restore from
            payload: Optional JSON payload with animation params (strategy, step_interval_ms, step_size)
        """
        strategy = None
        step_interval_ms = None
        step_size = None

        # Parse optional animation parameters from payload
        if payload and payload.strip():
            try:
                data = json.loads(payload)
                strategy = data.get("strategy")
                step_interval_ms = data.get("step_interval_ms")
                step_size = data.get("step_size")
            except json.JSONDecodeError:
                self.logger.warning(f"Invalid JSON in restore payload, ignoring: {payload[:100]}")
            except Exception as e:
                self.logger.warning(f"Error parsing restore payload: {e}")

        self.logger.info(f"Requested restore from slot '{slot}'")
        self.bridge.restore_from_slot(
            slot, strategy=strategy, step_interval_ms=step_interval_ms, step_size=step_size
        )

    def handle_delete(self, slot: str) -> None:
        """Handle delete saved state request.

        Args:
            slot: Save slot name to delete
        """
        success = self.bridge.save_state_manager.delete_saved_state(slot)
        if success:
            self.logger.info(f"Deleted saved state from slot '{slot}'")
        else:
            self.logger.error(f"Failed to delete state from slot '{slot}'")

    def handle_timed_message(self, payload: str) -> None:
        """Handle timed message request via MQTT.

        Args:
            payload: JSON payload with message, duration, optional restore_slot, and animation params
        """
        try:
            data = json.loads(payload)
            message = data.get("message", "")
            duration_seconds = data.get("duration_seconds", 60)
            restore_slot = data.get("restore_slot")
            strategy = data.get("strategy")
            step_interval_ms = data.get("step_interval_ms")
            step_size = data.get("step_size")
            restore_strategy = data.get("restore_strategy")
            restore_step_interval_ms = data.get("restore_step_interval_ms")
            restore_step_size = data.get("restore_step_size")

            if not message:
                self.logger.error("Timed message request missing 'message' field")
                return

            timer_id = self.bridge.timer_manager.schedule_timed_message(
                message=message,
                duration_seconds=duration_seconds,
                restore_slot=restore_slot,
                strategy=strategy,
                step_interval_ms=step_interval_ms,
                step_size=step_size,
                restore_strategy=restore_strategy,
                restore_step_interval_ms=restore_step_interval_ms,
                restore_step_size=restore_step_size,
            )

            # Optionally publish timer ID back to a response topic
            response_topic = data.get("response_topic")
            if response_topic:
                self._publish_timer_response(
                    response_topic, timer_id, message, duration_seconds, restore_slot
                )

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid timed message JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error handling timed message: {e}", exc_info=True)

    def handle_cancel_timer(self, timer_id: str) -> None:
        """Handle cancel timer request via MQTT.

        Args:
            timer_id: Timer ID to cancel
        """
        success = self.bridge.timer_manager.cancel_timed_message(timer_id)
        status = "successful" if success else "failed"
        self.logger.info(f"Timer {timer_id} cancellation: {status}")

    def handle_list_timers(self, payload: str) -> None:
        """Handle list active timers request via MQTT.

        Args:
            payload: Optional JSON with response_topic, or plain topic string
        """
        try:
            response_topic = self._parse_list_timers_payload(payload)
            timer_info = self.bridge.timer_manager.get_timer_info_list()

            response = {
                "active_timers": timer_info,
                "total_count": len(timer_info),
                "timestamp": int(time.time()),
            }

            self.bridge.mqtt_client.publish(response_topic, json.dumps(response, indent=2))
            self.logger.info(
                f"Published timer list to {response_topic} ({len(timer_info)} active timers)"
            )

        except Exception as e:
            self.logger.error(f"Error handling list timers request: {e}", exc_info=True)

    def _parse_message_payload(self, payload: str) -> Any:
        """Parse message payload into appropriate format.

        Args:
            payload: Raw message payload

        Returns:
            Parsed message content (text string or layout array)
        """
        try:
            message_data = json.loads(payload)
            if isinstance(message_data, list):
                # Layout array
                return message_data
            elif isinstance(message_data, dict) and "text" in message_data:
                # Text message object
                return message_data["text"]
            else:
                # Unknown JSON format, convert to string
                return str(message_data)
        except json.JSONDecodeError:
            # Plain text message
            return payload

    def _parse_message_with_params(self, payload: str) -> tuple[Any, Optional[int], Optional[int]]:
        """Parse message payload and extract optional animation parameters.

        Args:
            payload: Raw message payload

        Returns:
            Tuple of (message_content, step_interval_ms, step_size)
        """
        # Try to parse as JSON
        try:
            message_data = json.loads(payload)
        except json.JSONDecodeError:
            # Plain text message - no animation parameters
            return payload, None, None

        # Extract animation parameters if dict
        step_interval_ms = None
        step_size = None
        if isinstance(message_data, dict):
            step_interval_ms = message_data.get("step_interval_ms")
            step_size = message_data.get("step_size")

        # Determine message content based on type
        if isinstance(message_data, list):
            message_content = message_data
        elif isinstance(message_data, dict) and "text" in message_data:
            message_content = message_data["text"]
        elif isinstance(message_data, dict):
            message_content = str(message_data)
        else:
            message_content = str(message_data)

        return message_content, step_interval_ms, step_size

    def _parse_list_timers_payload(self, payload: str) -> str:
        """Parse list timers payload to extract response topic.

        Args:
            payload: Payload string (JSON or plain topic)

        Returns:
            Response topic path
        """
        default_topic = self.bridge.get_topic(Topics.TIMERS_RESPONSE)

        if not payload.strip():
            return default_topic

        try:
            data = json.loads(payload)
            return data.get("response_topic", default_topic)
        except json.JSONDecodeError:
            # If not valid JSON, treat as response topic string
            return payload.strip()

    def _publish_timer_response(
        self,
        topic: str,
        timer_id: str,
        message: str,
        duration_seconds: int,
        restore_slot: Optional[str],
    ) -> None:
        """Publish timer creation response.

        Args:
            topic: Response topic
            timer_id: Created timer ID
            message: Timed message content
            duration_seconds: Timer duration
            restore_slot: Restore slot name (if any)
        """
        response = {
            "timer_id": timer_id,
            "message": message,
            "duration_seconds": duration_seconds,
            "restore_slot": restore_slot,
        }
        self.bridge.mqtt_client.publish(topic, json.dumps(response))
        self.logger.debug(f"Published timer response to {topic}")

    def _log_send_result(self, success: bool, message_type: str) -> None:
        """Log the result of sending a message.

        Args:
            success: Whether the message was sent successfully
            message_type: Description of the message type for logging
        """
        if success:
            self.logger.info(f"Successfully sent {message_type}")
        else:
            self.logger.error(f"Failed to send {message_type}")
