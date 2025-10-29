"""MQTT bridge for Vestaboard with save states and timed messages."""

import json
import ssl
import threading
import time
from typing import Optional, Dict, Any
import paho.mqtt.client as mqtt
from .config import AppConfig, TLSConfig, LWTConfig
from .vestaboard_client import create_vestaboard_client
from .save_state_manager import SaveStateManager
from .logger import setup_logger


# Topic suffix constants
class Topics:
    """MQTT topic suffixes."""
    MESSAGE = "message"
    SAVE = "save/+"
    RESTORE = "restore/+"
    DELETE = "delete/+"
    TIMED_MESSAGE = "timed-message"
    CANCEL_TIMER = "cancel-timer/+"
    LIST_TIMERS = "list-timers"
    TIMERS_RESPONSE = "timers-response"
    STATES = "states"


class VestaboardMQTTBridge:
    """MQTT bridge for Vestaboard with save/restore functionality."""

    def __init__(self, config: AppConfig):
        """Initialize the MQTT bridge.

        Args:
            config: Application configuration object (use AppConfig.from_env())
        """
        self.config = config
        self.topic_prefix = config.mqtt.topic_prefix.rstrip("/")
        self.logger = setup_logger(__name__)

        # Initialize Vestaboard client
        self.vestaboard_client = create_vestaboard_client(
            api_key=config.vestaboard_api_key,
            max_queue_size=config.max_queue_size
        )

        # Initialize MQTT client
        self.mqtt_client = self._create_mqtt_client()

        # Initialize save state manager
        self.save_state_manager = SaveStateManager(
            self.mqtt_client,
            self.vestaboard_client,
            self.topic_prefix
        )

        # Track timed messages
        self.active_timers: Dict[str, threading.Timer] = {}

    def _create_mqtt_client(self) -> mqtt.Client:
        """Create and configure MQTT client.

        Returns:
            Configured MQTT client instance
        """
        client = mqtt.Client(
            client_id=self.config.mqtt.client_id or "",
            clean_session=self.config.mqtt.clean_session
        )

        # Set up callbacks
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect

        # Configure authentication
        if self.config.mqtt.username and self.config.mqtt.password:
            client.username_pw_set(
                self.config.mqtt.username,
                self.config.mqtt.password
            )

        # Configure TLS/SSL
        if self.config.mqtt.tls:
            self._configure_tls(client, self.config.mqtt.tls)

        # Configure Last Will and Testament
        if self.config.mqtt.lwt:
            self._configure_lwt(client, self.config.mqtt.lwt)

        return client

    def _configure_tls(self, client: mqtt.Client, tls_config: TLSConfig) -> None:
        """Configure TLS/SSL for MQTT connection.

        Args:
            client: MQTT client instance
            tls_config: TLS configuration object

        Raises:
            Exception: If TLS configuration fails
        """
        try:
            client.tls_set(
                ca_certs=tls_config.ca_certs,
                certfile=tls_config.certfile,
                keyfile=tls_config.keyfile,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
                ciphers=None
            )
            self.logger.info("TLS/SSL configured successfully")

            if tls_config.insecure:
                client.tls_insecure_set(True)
                self.logger.warning(
                    "TLS certificate verification DISABLED - insecure mode active"
                )
        except Exception as e:
            self.logger.error(f"Failed to configure TLS/SSL: {e}")
            raise

    def _configure_lwt(self, client: mqtt.Client, lwt_config: LWTConfig) -> None:
        """Configure Last Will and Testament for MQTT connection.

        Args:
            client: MQTT client instance
            lwt_config: LWT configuration object

        Raises:
            Exception: If LWT configuration fails
        """
        try:
            client.will_set(
                lwt_config.topic,
                lwt_config.payload,
                lwt_config.qos,
                lwt_config.retain
            )
            self.logger.info(f"Last Will and Testament configured: {lwt_config.topic}")
        except Exception as e:
            self.logger.error(f"Failed to configure LWT: {e}")
            raise

    def _get_topic(self, suffix: str) -> str:
        """Get full topic path with configured prefix.

        Args:
            suffix: Topic suffix (e.g., "message", "save/+")

        Returns:
            Full topic path with prefix
        """
        return f"{self.topic_prefix}/{suffix}"

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when MQTT client connects.

        Args:
            client: MQTT client instance
            userdata: User data set in client
            flags: Connection flags
            rc: Connection result code
        """
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            self._subscribe_to_topics(client)
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {rc}")

    def _subscribe_to_topics(self, client: mqtt.Client) -> None:
        """Subscribe to all relevant MQTT topics.

        Args:
            client: MQTT client instance
        """
        topic_suffixes = [
            Topics.MESSAGE,
            Topics.SAVE,
            Topics.RESTORE,
            Topics.DELETE,
            Topics.TIMED_MESSAGE,
            Topics.CANCEL_TIMER,
            Topics.LIST_TIMERS,
        ]
        qos = self.config.mqtt.qos

        for suffix in topic_suffixes:
            topic = self._get_topic(suffix)
            client.subscribe(topic, qos=qos)
            self.logger.debug(f"Subscribed to {topic} with QoS {qos}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when MQTT client disconnects.

        Args:
            client: MQTT client instance
            userdata: User data set in client
            rc: Disconnection result code
        """
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")
        else:
            self.logger.info("Disconnected from MQTT broker")

    def _on_message(self, client, userdata, message):
        """Handle incoming MQTT messages.

        Args:
            client: MQTT client instance
            userdata: User data set in client
            message: MQTT message
        """
        topic = message.topic
        payload = message.payload.decode("utf-8")

        self.logger.debug(f"Received message on {topic}: {payload[:100]}...")

        try:
            suffix = self._extract_topic_suffix(topic)
            if suffix is None:
                return

            self._route_message(suffix, payload)
        except Exception as e:
            self.logger.error(f"Error handling message on {topic}: {e}", exc_info=True)

    def _extract_topic_suffix(self, topic: str) -> Optional[str]:
        """Extract the suffix from a full topic path.

        Args:
            topic: Full MQTT topic path

        Returns:
            Topic suffix without prefix, or None if invalid
        """
        prefix_with_slash = f"{self.topic_prefix}/"
        if not topic.startswith(prefix_with_slash):
            self.logger.warning(f"Received message on unexpected topic: {topic}")
            return None
        return topic[len(prefix_with_slash):]

    def _route_message(self, suffix: str, payload: str) -> None:
        """Route message to appropriate handler based on topic suffix.

        Args:
            suffix: Topic suffix without prefix
            payload: Message payload
        """
        # Direct match handlers
        if suffix == Topics.MESSAGE.replace("/+", ""):
            self._handle_message(payload)
        elif suffix == Topics.TIMED_MESSAGE.replace("/+", ""):
            self._handle_timed_message(payload)
        elif suffix == Topics.LIST_TIMERS.replace("/+", ""):
            self._handle_list_timers(payload)
        # Pattern match handlers (with wildcards)
        elif suffix.startswith("save/"):
            slot = suffix.split("/", 1)[1]
            self._handle_save(slot)
        elif suffix.startswith("restore/"):
            slot = suffix.split("/", 1)[1]
            self._handle_restore_request(slot)
        elif suffix.startswith("delete/"):
            slot = suffix.split("/", 1)[1]
            self._handle_delete(slot)
        elif suffix.startswith("cancel-timer/"):
            timer_id = suffix.split("/", 1)[1]
            self._handle_cancel_timer(timer_id)
        else:
            self.logger.warning(f"Unknown topic suffix: {suffix}")
    
    def _handle_message(self, payload: str) -> None:
        """Handle regular message to display on Vestaboard.

        Args:
            payload: Message payload (text, JSON layout array, or JSON object)
        """
        try:
            message_content = self._parse_message_payload(payload)
            success = self.vestaboard_client.write_message(message_content)

            if success:
                self.logger.info("Message sent to Vestaboard successfully")
            else:
                self.logger.error("Failed to send message to Vestaboard")
        except Exception as e:
            self.logger.error(f"Error handling message: {e}", exc_info=True)

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
    
    def _handle_save(self, slot: str) -> None:
        """Handle save current state request.

        Args:
            slot: Save slot name
        """
        success = self.save_state_manager.save_current_state(slot)
        if success:
            self.logger.info(f"Saved current state to slot '{slot}'")
        else:
            self.logger.error(f"Failed to save state to slot '{slot}'")

    def _handle_restore_request(self, slot: str) -> None:
        """Handle restore state request.

        Args:
            slot: Save slot name to restore from
        """
        self.logger.info(f"Requested restore from slot '{slot}'")
        self._restore_from_slot(slot)
    
    def _restore_from_slot(self, slot: str) -> None:
        """Internal method to restore from a slot (used by both manual and timed restores).

        Args:
            slot: Save slot name to restore from
        """
        state_topic = self._get_topic(f"{Topics.STATES}/{slot}")

        def on_restore_message(client, userdata, message):
            """Callback to handle restore message."""
            if message.topic != state_topic:
                return

            try:
                if not message.payload:
                    self.logger.warning(f"No saved state found in slot '{slot}'")
                    return

                payload_str = message.payload.decode("utf-8")
                self.logger.debug(
                    f"Received save data payload (first 100 chars): {payload_str[:100]}..."
                )

                save_data = json.loads(payload_str)
                self.logger.debug(f"Parsed save data keys: {list(save_data.keys())}")

                success = self.save_state_manager.restore_from_data(save_data)
                if success:
                    self.logger.info(f"Restored state from slot '{slot}'")
                else:
                    self.logger.error(f"Failed to restore state from slot '{slot}'")

            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid save data for slot '{slot}': {e}")
            except Exception as e:
                self.logger.error(
                    f"Error restoring from slot '{slot}': {e}", exc_info=True
                )
            finally:
                # Cleanup: unsubscribe and remove callback
                client.unsubscribe(state_topic)
                client.message_callback_remove(state_topic)

        # Set up temporary message callback for this specific topic
        self.mqtt_client.message_callback_add(state_topic, on_restore_message)
        # Subscribe to get the retained message
        self.mqtt_client.subscribe(state_topic)

    def _handle_delete(self, slot: str) -> None:
        """Handle delete saved state request.

        Args:
            slot: Save slot name to delete
        """
        success = self.save_state_manager.delete_saved_state(slot)
        if success:
            self.logger.info(f"Deleted saved state from slot '{slot}'")
        else:
            self.logger.error(f"Failed to delete state from slot '{slot}'")
    
    def _handle_timed_message(self, payload: str) -> None:
        """Handle timed message request via MQTT.

        Args:
            payload: JSON payload with message, duration, and optional restore_slot
        """
        try:
            data = json.loads(payload)
            message = data.get("message", "")
            duration_seconds = data.get("duration_seconds", 60)
            restore_slot = data.get("restore_slot")

            if not message:
                self.logger.error("Timed message request missing 'message' field")
                return

            timer_id = self.schedule_timed_message(
                message, duration_seconds, restore_slot
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
        self.mqtt_client.publish(topic, json.dumps(response))
        self.logger.debug(f"Published timer response to {topic}")

    def _handle_cancel_timer(self, timer_id: str) -> None:
        """Handle cancel timer request via MQTT.

        Args:
            timer_id: Timer ID to cancel
        """
        success = self.cancel_timed_message(timer_id)
        status = "successful" if success else "failed"
        self.logger.info(f"Timer {timer_id} cancellation: {status}")
    
    def _handle_list_timers(self, payload: str) -> None:
        """Handle list active timers request via MQTT.

        Args:
            payload: Optional JSON with response_topic, or plain topic string
        """
        try:
            response_topic = self._parse_list_timers_payload(payload)
            timer_info = self._build_timer_info_list()

            response = {
                "active_timers": timer_info,
                "total_count": len(timer_info),
                "timestamp": int(time.time()),
            }

            self.mqtt_client.publish(response_topic, json.dumps(response, indent=2))
            self.logger.info(
                f"Published timer list to {response_topic} ({len(timer_info)} active timers)"
            )

        except Exception as e:
            self.logger.error(f"Error handling list timers request: {e}", exc_info=True)

    def _parse_list_timers_payload(self, payload: str) -> str:
        """Parse list timers payload to extract response topic.

        Args:
            payload: Payload string (JSON or plain topic)

        Returns:
            Response topic path
        """
        default_topic = self._get_topic(Topics.TIMERS_RESPONSE)

        if not payload.strip():
            return default_topic

        try:
            data = json.loads(payload)
            return data.get("response_topic", default_topic)
        except json.JSONDecodeError:
            # If not valid JSON, treat as response topic string
            return payload.strip()

    def _build_timer_info_list(self) -> list[Dict[str, Any]]:
        """Build list of active timer information.

        Returns:
            List of timer info dictionaries
        """
        timer_info = []
        for timer_id, timer in self.active_timers.items():
            # Note: Timer objects don't expose remaining time directly
            # This is a limitation of threading.Timer
            created_at = timer_id.split("_")[-1] if "_" in timer_id else "unknown"
            timer_info.append({
                "timer_id": timer_id,
                "active": timer.is_alive(),
                "created_at": created_at,
            })
        return timer_info
    
    def schedule_timed_message(
        self,
        message: str,
        duration_seconds: int,
        restore_slot: Optional[str] = None,
    ) -> str:
        """Schedule a timed message with optional auto-restore.

        Args:
            message: Message to display
            duration_seconds: How long to display the message
            restore_slot: Optional slot to restore from after timer expires

        Returns:
            Timer ID for cancellation
        """
        timer_id = f"timer_{int(time.time())}"

        # Save current state if no restore slot specified
        if restore_slot is None:
            restore_slot = f"temp_{timer_id}"
            self.save_state_manager.save_current_state(restore_slot)

        # Display the timed message
        success = self.vestaboard_client.write_message(message)
        if not success:
            self.logger.error("Failed to display timed message")
            return timer_id

        # Record when we wrote the timed message for rate limit tracking
        write_time = time.time()

        # Schedule restoration
        def restore_previous():
            """Restore callback executed after timer expires."""
            self.logger.info(
                f"Timer {timer_id} expired, restoring from slot {restore_slot}"
            )

            # Respect rate limits before restoring
            self._wait_for_rate_limit(write_time)

            self._restore_from_slot(restore_slot)

            # Clean up timer tracking
            self.active_timers.pop(timer_id, None)

        timer = threading.Timer(duration_seconds, restore_previous)
        self.active_timers[timer_id] = timer
        timer.start()

        self.logger.info(
            f"Scheduled timed message for {duration_seconds} seconds (ID: {timer_id})"
        )
        return timer_id

    def _wait_for_rate_limit(self, write_time: float) -> None:
        """Wait for rate limit to clear if necessary.

        Args:
            write_time: Timestamp of the last write operation
        """
        if not hasattr(self.vestaboard_client, "RATE_LIMIT_SECONDS"):
            return

        rate_limit = self.vestaboard_client.RATE_LIMIT_SECONDS
        time_since_write = time.time() - write_time
        remaining_wait = rate_limit - time_since_write

        if remaining_wait > 0:
            self.logger.info(
                f"Waiting {remaining_wait:.1f}s for Cloud API rate limit before restore"
            )
            time.sleep(remaining_wait + 0.5)  # Add 0.5s buffer

    def cancel_timed_message(self, timer_id: str) -> bool:
        """Cancel a scheduled timed message.

        Args:
            timer_id: ID of timer to cancel

        Returns:
            True if cancelled, False if not found
        """
        timer = self.active_timers.pop(timer_id, None)
        if timer is not None:
            timer.cancel()
            self.logger.info(f"Cancelled timer {timer_id}")
            return True
        return False

    def start(self) -> None:
        """Start the MQTT bridge."""
        try:
            self.logger.info(
                f"Connecting to MQTT broker at {self.config.mqtt.host}:"
                f"{self.config.mqtt.port} with topic prefix '{self.topic_prefix}'"
            )
            self.mqtt_client.connect(
                self.config.mqtt.host,
                self.config.mqtt.port,
                self.config.mqtt.keepalive,
            )
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            self.logger.info("Shutting down MQTT bridge...")
            self.stop()
        except Exception as e:
            self.logger.error(f"Error starting MQTT bridge: {e}", exc_info=True)
            raise

    def stop(self) -> None:
        """Stop the MQTT bridge and clean up."""
        # Cancel all active timers
        for timer_id, timer in list(self.active_timers.items()):
            timer.cancel()
            self.logger.debug(f"Cancelled timer {timer_id}")
        self.active_timers.clear()

        # Disconnect from MQTT
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()
        self.logger.info("MQTT bridge stopped")