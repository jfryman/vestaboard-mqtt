"""MQTT bridge for Vestaboard with save states and timed messages."""

import json
import ssl
import threading
import time
from typing import Dict, Optional, Union, List
import paho.mqtt.client as mqtt
from .vestaboard_client import create_vestaboard_client
from .save_state_manager import SaveStateManager
from .logger import setup_logger


class VestaboardMQTTBridge:
    """MQTT bridge for Vestaboard with save/restore functionality."""

    def __init__(self, vestaboard_api_key: str = None, mqtt_config: Dict = None, max_queue_size: int = 10):
        """Initialize the MQTT bridge.

        Args:
            vestaboard_api_key: Vestaboard API key (cloud or local), or None to auto-detect from env
            mqtt_config: MQTT broker configuration including:
                - host: MQTT broker hostname
                - port: MQTT broker port
                - username: MQTT username (optional)
                - password: MQTT password (optional)
                - topic_prefix: Topic prefix for all topics (default: "vestaboard")
                - client_id: MQTT client ID (optional, auto-generated if not provided)
                - clean_session: Clean session flag (default: True)
                - keepalive: Keep-alive interval in seconds (default: 60)
                - qos: Default QoS level (0, 1, or 2, default: 0)
                - tls: TLS/SSL configuration dict (optional):
                    - enabled: Enable TLS/SSL (default: False)
                    - ca_certs: Path to CA certificate file
                    - certfile: Path to client certificate file (optional)
                    - keyfile: Path to client key file (optional)
                    - cert_reqs: Certificate verification mode (default: ssl.CERT_REQUIRED)
                    - tls_version: TLS version (default: ssl.PROTOCOL_TLS)
                    - ciphers: Allowed ciphers (optional)
                    - insecure: Skip certificate verification (default: False)
                - lwt: Last Will and Testament configuration dict (optional):
                    - topic: LWT topic
                    - payload: LWT payload
                    - qos: LWT QoS level (default: 0)
                    - retain: LWT retain flag (default: True)
            max_queue_size: Maximum number of messages to queue when rate limited
        """
        self.vestaboard_client = create_vestaboard_client(
            api_key=vestaboard_api_key,
            max_queue_size=max_queue_size
        )
        self.mqtt_config = mqtt_config or {}
        self.topic_prefix = self.mqtt_config.get("topic_prefix", "vestaboard").rstrip("/")
        self.qos = self.mqtt_config.get("qos", 0)

        # Initialize MQTT client with optional client ID and clean session
        client_id = self.mqtt_config.get("client_id", "")
        clean_session = self.mqtt_config.get("clean_session", True)
        self.mqtt_client = mqtt.Client(client_id=client_id, clean_session=clean_session)

        self.save_state_manager = SaveStateManager(self.mqtt_client, self.vestaboard_client, self.topic_prefix)
        self.logger = setup_logger(__name__)

        # Track timed messages
        self.active_timers: Dict[str, threading.Timer] = {}

        # Set up MQTT callbacks
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect

        # Set up authentication if provided
        if self.mqtt_config.get("username") and self.mqtt_config.get("password"):
            self.mqtt_client.username_pw_set(
                self.mqtt_config["username"],
                self.mqtt_config["password"]
            )

        # Set up TLS/SSL if enabled
        tls_config = self.mqtt_config.get("tls", {})
        if tls_config.get("enabled", False):
            self._configure_tls(tls_config)

        # Set up Last Will and Testament if configured
        lwt_config = self.mqtt_config.get("lwt")
        if lwt_config:
            self._configure_lwt(lwt_config)

    def _configure_tls(self, tls_config: Dict):
        """Configure TLS/SSL for MQTT connection.

        Args:
            tls_config: TLS configuration dictionary
        """
        ca_certs = tls_config.get("ca_certs")
        certfile = tls_config.get("certfile")
        keyfile = tls_config.get("keyfile")
        cert_reqs = tls_config.get("cert_reqs", ssl.CERT_REQUIRED)
        tls_version = tls_config.get("tls_version", ssl.PROTOCOL_TLS)
        ciphers = tls_config.get("ciphers")

        try:
            self.mqtt_client.tls_set(
                ca_certs=ca_certs,
                certfile=certfile,
                keyfile=keyfile,
                cert_reqs=cert_reqs,
                tls_version=tls_version,
                ciphers=ciphers
            )
            self.logger.info("TLS/SSL configured successfully")

            # Disable certificate verification if insecure flag is set
            if tls_config.get("insecure", False):
                self.mqtt_client.tls_insecure_set(True)
                self.logger.warning("TLS certificate verification DISABLED - insecure mode active")

        except Exception as e:
            self.logger.error(f"Failed to configure TLS/SSL: {e}")
            raise

    def _configure_lwt(self, lwt_config: Dict):
        """Configure Last Will and Testament for MQTT connection.

        Args:
            lwt_config: LWT configuration dictionary
        """
        topic = lwt_config.get("topic")
        if not topic:
            self.logger.error("LWT topic not specified")
            return

        payload = lwt_config.get("payload", "offline")
        qos = lwt_config.get("qos", 0)
        retain = lwt_config.get("retain", True)

        try:
            self.mqtt_client.will_set(topic, payload, qos, retain)
            self.logger.info(f"Last Will and Testament configured: {topic}")
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
        """Callback for when MQTT client connects."""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            # Subscribe to all relevant topics
            topic_suffixes = [
                "message",
                "save/+",
                "restore/+",
                "delete/+",
                "timed-message",
                "cancel-timer/+",
                "list-timers"
            ]
            for suffix in topic_suffixes:
                topic = self._get_topic(suffix)
                client.subscribe(topic, qos=self.qos)
                self.logger.debug(f"Subscribed to {topic} with QoS {self.qos}")
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when MQTT client disconnects."""
        self.logger.warning(f"Disconnected from MQTT broker: {rc}")
    
    def _on_message(self, client, userdata, message):
        """Handle incoming MQTT messages."""
        topic = message.topic
        payload = message.payload.decode('utf-8')

        self.logger.debug(f"Received message on {topic}: {payload[:100]}...")

        try:
            # Strip the prefix to get the suffix
            if not topic.startswith(self.topic_prefix + "/"):
                self.logger.warning(f"Received message on unexpected topic: {topic}")
                return

            suffix = topic[len(self.topic_prefix) + 1:]

            if suffix == "message":
                self._handle_message(payload)
            elif suffix.startswith("save/"):
                slot = suffix.split("/")[-1]
                self._handle_save(slot)
            elif suffix.startswith("restore/"):
                slot = suffix.split("/")[-1]
                self._handle_restore_request(slot)
            elif suffix.startswith("delete/"):
                slot = suffix.split("/")[-1]
                self._handle_delete(slot)
            elif suffix == "timed-message":
                self._handle_timed_message(payload)
            elif suffix.startswith("cancel-timer/"):
                timer_id = suffix.split("/")[-1]
                self._handle_cancel_timer(timer_id)
            elif suffix == "list-timers":
                self._handle_list_timers(payload)
        except Exception as e:
            self.logger.error(f"Error handling message on {topic}: {e}")
    
    def _handle_message(self, payload: str):
        """Handle regular message to display on Vestaboard."""
        try:
            # Try to parse as JSON first (for layout arrays)
            try:
                message_data = json.loads(payload)
                if isinstance(message_data, list):
                    # It's a layout array
                    success = self.vestaboard_client.write_message(message_data)
                elif isinstance(message_data, dict) and "text" in message_data:
                    # It's a text message object
                    success = self.vestaboard_client.write_message(message_data["text"])
                else:
                    # Treat as plain text
                    success = self.vestaboard_client.write_message(str(message_data))
            except json.JSONDecodeError:
                # Not JSON, treat as plain text
                success = self.vestaboard_client.write_message(payload)
            
            if success:
                self.logger.info("Message sent to Vestaboard successfully")
            else:
                self.logger.error("Failed to send message to Vestaboard")
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    def _handle_save(self, slot: str):
        """Handle save current state request."""
        success = self.save_state_manager.save_current_state(slot)
        if success:
            self.logger.info(f"Saved current state to slot '{slot}'")
        else:
            self.logger.error(f"Failed to save state to slot '{slot}'")
    
    def _handle_restore_request(self, slot: str):
        """Handle restore state request."""
        self.logger.info(f"Requested restore from slot '{slot}'")
        self._restore_from_slot(slot)
    
    def _restore_from_slot(self, slot: str):
        """Internal method to restore from a slot (used by both manual and timed restores)."""
        state_topic = self._get_topic(f"states/{slot}")

        def on_restore_message(client, userdata, message):
            if message.topic == state_topic:
                try:
                    if message.payload:
                        payload_str = message.payload.decode('utf-8')
                        self.logger.debug(f"Received save data payload (first 100 chars): {payload_str[:100]}...")
                        save_data = json.loads(payload_str)
                        self.logger.debug(f"Parsed save data keys: {list(save_data.keys())}")
                        success = self.save_state_manager.restore_from_data(save_data)
                        if success:
                            self.logger.info(f"Restored state from slot '{slot}'")
                        else:
                            self.logger.error(f"Failed to restore state from slot '{slot}'")
                    else:
                        self.logger.warning(f"No saved state found in slot '{slot}'")
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid save data for slot '{slot}': {e}")
                except Exception as e:
                    self.logger.error(f"Error restoring from slot '{slot}': {e}")
                finally:
                    # Unsubscribe after handling the message
                    client.unsubscribe(state_topic)
                    # Remove the temporary message handler
                    client.message_callback_remove(state_topic)
        
        # Set up temporary message callback for this specific topic
        self.mqtt_client.message_callback_add(state_topic, on_restore_message)
        # Subscribe to get the retained message
        self.mqtt_client.subscribe(state_topic)
    
    def _handle_delete(self, slot: str):
        """Handle delete saved state request."""
        success = self.save_state_manager.delete_saved_state(slot)
        if success:
            self.logger.info(f"Deleted saved state from slot '{slot}'")
        else:
            self.logger.error(f"Failed to delete state from slot '{slot}'")
    
    def _handle_timed_message(self, payload: str):
        """Handle timed message request via MQTT."""
        try:
            # Parse timed message request
            data = json.loads(payload)
            message = data.get("message", "")
            duration_seconds = data.get("duration_seconds", 60)
            restore_slot = data.get("restore_slot")
            
            if not message:
                self.logger.error("Timed message request missing 'message' field")
                return
            
            timer_id = self.schedule_timed_message(message, duration_seconds, restore_slot)
            
            # Optionally publish timer ID back to a response topic
            response_topic = data.get("response_topic")
            if response_topic:
                response = {
                    "timer_id": timer_id,
                    "message": message,
                    "duration_seconds": duration_seconds,
                    "restore_slot": restore_slot
                }
                self.mqtt_client.publish(response_topic, json.dumps(response))
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid timed message JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error handling timed message: {e}")
    
    def _handle_cancel_timer(self, timer_id: str):
        """Handle cancel timer request via MQTT."""
        success = self.cancel_timed_message(timer_id)
        self.logger.info(f"Timer {timer_id} cancellation: {'successful' if success else 'failed'}")
    
    def _handle_list_timers(self, payload: str):
        """Handle list active timers request via MQTT."""
        try:
            # Parse request to get optional response topic
            response_topic = self._get_topic("timers-response")  # default response topic

            if payload.strip():
                try:
                    data = json.loads(payload)
                    # Allow custom response topic override
                    response_topic = data.get("response_topic", response_topic)
                except json.JSONDecodeError:
                    # If not valid JSON, treat as response topic string
                    response_topic = payload.strip()
            
            # Build timer info list
            timer_info = []
            current_time = time.time()
            
            for timer_id, timer in self.active_timers.items():
                # Calculate remaining time (approximate)
                # Note: Timer objects don't expose remaining time directly
                # This is a limitation of threading.Timer
                timer_info.append({
                    "timer_id": timer_id,
                    "active": timer.is_alive(),
                    "created_at": timer_id.split("_")[-1] if "_" in timer_id else "unknown"
                })
            
            response = {
                "active_timers": timer_info,
                "total_count": len(timer_info),
                "timestamp": int(current_time)
            }
            
            # Publish response
            self.mqtt_client.publish(response_topic, json.dumps(response, indent=2))
            self.logger.info(f"Published timer list to {response_topic} ({len(timer_info)} active timers)")
            
        except Exception as e:
            self.logger.error(f"Error handling list timers request: {e}")
    
    def schedule_timed_message(self, message: str, duration_seconds: int,
                             restore_slot: Optional[str] = None) -> str:
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
            self.logger.info(f"Timer {timer_id} expired, restoring from slot {restore_slot}")

            # For Cloud API, ensure we respect the rate limit before restoring
            # Check if we need to wait for rate limit to clear
            if hasattr(self.vestaboard_client, 'RATE_LIMIT_SECONDS'):
                rate_limit = self.vestaboard_client.RATE_LIMIT_SECONDS
                time_since_write = time.time() - write_time
                remaining_wait = rate_limit - time_since_write

                if remaining_wait > 0:
                    self.logger.info(f"Waiting {remaining_wait:.1f}s for Cloud API rate limit before restore")
                    time.sleep(remaining_wait + 0.5)  # Add 0.5s buffer

            self._restore_from_slot(restore_slot)
            # Clean up timer tracking
            if timer_id in self.active_timers:
                del self.active_timers[timer_id]

        timer = threading.Timer(duration_seconds, restore_previous)
        self.active_timers[timer_id] = timer
        timer.start()

        self.logger.info(f"Scheduled timed message for {duration_seconds} seconds (ID: {timer_id})")
        return timer_id
    
    
    
    def cancel_timed_message(self, timer_id: str) -> bool:
        """Cancel a scheduled timed message.
        
        Args:
            timer_id: ID of timer to cancel
            
        Returns:
            True if cancelled, False if not found
        """
        if timer_id in self.active_timers:
            self.active_timers[timer_id].cancel()
            del self.active_timers[timer_id]
            self.logger.info(f"Cancelled timer {timer_id}")
            return True
        return False
    
    def start(self):
        """Start the MQTT bridge."""
        try:
            keepalive = self.mqtt_config.get("keepalive", 60)
            self.logger.info(f"Connecting to MQTT broker at {self.mqtt_config['host']}:{self.mqtt_config['port']} "
                           f"with topic prefix '{self.topic_prefix}'")
            self.mqtt_client.connect(
                self.mqtt_config["host"],
                self.mqtt_config["port"],
                keepalive
            )
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            self.logger.info("Shutting down MQTT bridge...")
            self.stop()
        except Exception as e:
            self.logger.error(f"Error starting MQTT bridge: {e}")
    
    def stop(self):
        """Stop the MQTT bridge and clean up."""
        # Cancel all active timers
        for timer_id, timer in self.active_timers.items():
            timer.cancel()
            self.logger.debug(f"Cancelled timer {timer_id}")
        self.active_timers.clear()
        
        # Disconnect from MQTT
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()
        self.logger.info("MQTT bridge stopped")