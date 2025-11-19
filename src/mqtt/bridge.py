"""MQTT bridge for Vestaboard with save states and timed messages."""

import json
import logging
import ssl
from typing import TYPE_CHECKING, Optional

import paho.mqtt.client as mqtt

from .handlers import MessageHandlers
from .timers import TimerManager
from .topics import Topics

if TYPE_CHECKING:
    from ..config import AppConfig, LWTConfig, TLSConfig


class VestaboardMQTTBridge:
    """MQTT bridge for Vestaboard with save/restore functionality."""

    def __init__(self, config: "AppConfig"):
        """Initialize the MQTT bridge.

        Args:
            config: Application configuration object (use AppConfig.from_env())
        """
        from ..state import SaveStateManager
        from ..vestaboard import create_vestaboard_client

        self.config = config
        self.topic_prefix = config.mqtt.topic_prefix.rstrip("/")
        self.logger = logging.getLogger(__name__)

        # Initialize Vestaboard client
        self.vestaboard_client = create_vestaboard_client(
            api_key=config.vestaboard.api_key, max_queue_size=config.effective_max_queue_size
        )

        # Initialize MQTT client
        self.mqtt_client = self._create_mqtt_client()

        # Initialize save state manager
        self.save_state_manager = SaveStateManager(
            self.mqtt_client, self.vestaboard_client, self.topic_prefix
        )

        # Initialize timer manager
        self.timer_manager = TimerManager(
            self.vestaboard_client, self.save_state_manager, self.restore_from_slot
        )

        # Initialize message handlers
        self.handlers = MessageHandlers(self)

    def _create_mqtt_client(self) -> mqtt.Client:
        """Create and configure MQTT client.

        Returns:
            Configured MQTT client instance
        """
        client = mqtt.Client(
            client_id=self.config.mqtt.client_id or "", clean_session=self.config.mqtt.clean_session
        )

        # Set up callbacks
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect

        # Configure authentication
        if self.config.mqtt.username and self.config.mqtt.password:
            client.username_pw_set(self.config.mqtt.username, self.config.mqtt.password)

        # Configure TLS/SSL
        if self.config.mqtt.tls:
            self._configure_tls(client, self.config.mqtt.tls)

        # Configure Last Will and Testament
        if self.config.mqtt.lwt:
            self._configure_lwt(client, self.config.mqtt.lwt)

        return client

    def _configure_tls(self, client: mqtt.Client, tls_config: "TLSConfig") -> None:
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
                ciphers=None,
            )
            self.logger.info("TLS/SSL configured successfully")

            if tls_config.insecure:
                client.tls_insecure_set(True)
                self.logger.warning("TLS certificate verification DISABLED - insecure mode active")
        except Exception as e:
            self.logger.error(f"Failed to configure TLS/SSL: {e}")
            raise

    def _configure_lwt(self, client: mqtt.Client, lwt_config: "LWTConfig") -> None:
        """Configure Last Will and Testament for MQTT connection.

        Args:
            client: MQTT client instance
            lwt_config: LWT configuration object

        Raises:
            Exception: If LWT configuration fails
        """
        try:
            client.will_set(lwt_config.topic, lwt_config.payload, lwt_config.qos, lwt_config.retain)
            self.logger.info(f"Last Will and Testament configured: {lwt_config.topic}")
        except Exception as e:
            self.logger.error(f"Failed to configure LWT: {e}")
            raise

    def get_topic(self, suffix: str) -> str:
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
            Topics.MESSAGE_WITH_STRATEGY,
            Topics.SAVE,
            Topics.RESTORE,
            Topics.DELETE,
            Topics.TIMED_MESSAGE,
            Topics.CANCEL_TIMER,
            Topics.LIST_TIMERS,
        ]
        qos = self.config.mqtt.qos

        for suffix in topic_suffixes:
            topic = self.get_topic(suffix)
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
        return topic[len(prefix_with_slash) :]

    def _route_message(self, suffix: str, payload: str) -> None:
        """Route message to appropriate handler based on topic suffix.

        Args:
            suffix: Topic suffix without prefix
            payload: Message payload
        """
        # Direct match handlers
        if suffix == Topics.MESSAGE.replace("/+", ""):
            self.handlers.handle_message(payload)
        elif suffix == Topics.TIMED_MESSAGE.replace("/+", ""):
            self.handlers.handle_timed_message(payload)
        elif suffix == Topics.LIST_TIMERS.replace("/+", ""):
            self.handlers.handle_list_timers(payload)
        # Pattern match handlers (with wildcards)
        elif suffix.startswith("message/"):
            strategy = suffix.split("/", 1)[1]
            if not strategy:
                self.logger.warning("Received message with empty strategy - treating as regular message")
                self.handlers.handle_message(payload)
            else:
                self.handlers.handle_message(payload, strategy=strategy)
        elif suffix.startswith("save/"):
            slot = suffix.split("/", 1)[1]
            self.handlers.handle_save(slot)
        elif suffix.startswith("restore/"):
            slot = suffix.split("/", 1)[1]
            self.handlers.handle_restore_request(slot)
        elif suffix.startswith("delete/"):
            slot = suffix.split("/", 1)[1]
            self.handlers.handle_delete(slot)
        elif suffix.startswith("cancel-timer/"):
            timer_id = suffix.split("/", 1)[1]
            self.handlers.handle_cancel_timer(timer_id)
        else:
            self.logger.warning(f"Unknown topic suffix: {suffix}")

    def restore_from_slot(self, slot: str) -> None:
        """Internal method to restore from a slot (used by both manual and timed restores).

        Args:
            slot: Save slot name to restore from
        """
        state_topic = self.get_topic(f"{Topics.STATES}/{slot}")

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
                self.logger.error(f"Error restoring from slot '{slot}': {e}", exc_info=True)
            finally:
                # Cleanup: unsubscribe and remove callback
                client.unsubscribe(state_topic)
                client.message_callback_remove(state_topic)

        # Set up temporary message callback for this specific topic
        self.mqtt_client.message_callback_add(state_topic, on_restore_message)
        # Subscribe to get the retained message
        self.mqtt_client.subscribe(state_topic)

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
        self.timer_manager.cleanup_all_timers()

        # Disconnect from MQTT
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()
        self.logger.info("MQTT bridge stopped")
