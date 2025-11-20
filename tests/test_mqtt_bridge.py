"""Comprehensive tests for VestaboardMQTTBridge."""

import json
import ssl
import time
from unittest.mock import MagicMock, Mock, call, patch

import paho.mqtt.client as mqtt
import pytest

from src.config import AppConfig, LWTConfig, MQTTConfig, TLSConfig
from src.mqtt import VestaboardMQTTBridge
from tests.conftest import create_test_app_config


class TestMQTTBridgeInitialization:
    """Test VestaboardMQTTBridge initialization with different configurations."""

    @patch("src.vestaboard.create_vestaboard_client")
    def test_initialization_with_defaults(self, mock_create_client):
        """Test bridge initializes with default configuration."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        assert bridge.topic_prefix == "vestaboard"
        assert bridge.config.mqtt.qos == 0
        assert bridge.vestaboard_client == mock_client
        assert len(bridge.timer_manager.active_timers) == 0
        mock_create_client.assert_called_once_with(api_key="test_api_key", max_queue_size=10)

    @patch("src.vestaboard.create_vestaboard_client")
    def test_initialization_with_custom_topic_prefix(self, mock_create_client):
        """Test bridge initializes with custom topic prefix."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883, topic_prefix="office-board")
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        assert bridge.topic_prefix == "office-board"

    @patch("src.vestaboard.create_vestaboard_client")
    def test_initialization_strips_trailing_slash(self, mock_create_client):
        """Test that topic prefix strips trailing slashes."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883, topic_prefix="vestaboard/")
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        assert bridge.topic_prefix == "vestaboard"

    @patch("src.vestaboard.create_vestaboard_client")
    def test_initialization_with_custom_qos(self, mock_create_client):
        """Test bridge initializes with custom QoS level."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883, qos=2)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        assert bridge.config.mqtt.qos == 2

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_initialization_with_authentication(self, mock_create_client, mock_mqtt_client):
        """Test bridge sets up MQTT authentication."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(
            host="localhost", port=1883, username="test_user", password="test_pass"
        )
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Verify username_pw_set was called on the MQTT client
        mock_client_instance.username_pw_set.assert_called_once_with("test_user", "test_pass")

    @patch("src.vestaboard.create_vestaboard_client")
    def test_initialization_with_custom_client_id(self, mock_create_client):
        """Test bridge uses custom MQTT client ID."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883, client_id="custom-vestaboard-1")

        with patch("src.mqtt.bridge.mqtt.Client") as mock_mqtt_client:
            config = create_test_app_config(mqtt_config=mqtt_config)
            bridge = VestaboardMQTTBridge(config)
            mock_mqtt_client.assert_called_once_with(
                client_id="custom-vestaboard-1", clean_session=True
            )

    @patch("src.vestaboard.create_vestaboard_client")
    def test_initialization_with_persistent_session(self, mock_create_client):
        """Test bridge uses persistent session when configured."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883, clean_session=False)

        with patch("src.mqtt.bridge.mqtt.Client") as mock_mqtt_client:
            config = create_test_app_config(mqtt_config=mqtt_config)
            bridge = VestaboardMQTTBridge(config)
            mock_mqtt_client.assert_called_once_with(client_id="", clean_session=False)

    @patch("src.vestaboard.create_vestaboard_client")
    def test_initialization_with_max_queue_size(self, mock_create_client):
        """Test bridge passes max_queue_size to Vestaboard client."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config, max_queue_size=20)
        bridge = VestaboardMQTTBridge(config)

        mock_create_client.assert_called_once_with(api_key="test_api_key", max_queue_size=20)


class TestTLSConfiguration:
    """Test TLS/SSL configuration for MQTT connection."""

    @patch("os.path.exists", return_value=True)
    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_tls_configuration_basic(self, mock_create_client, mock_mqtt_client, mock_exists):
        """Test basic TLS configuration."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        tls_config = TLSConfig(enabled=True, ca_certs="/path/to/ca.crt")
        mqtt_config = MQTTConfig(host="localhost", port=8883, tls=tls_config)

        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        mock_client_instance.tls_set.assert_called_once()
        args, kwargs = mock_client_instance.tls_set.call_args
        assert kwargs["ca_certs"] == "/path/to/ca.crt"
        assert kwargs["cert_reqs"] == ssl.CERT_REQUIRED
        assert kwargs["tls_version"] == ssl.PROTOCOL_TLS

    @patch("os.path.exists", return_value=True)
    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_tls_configuration_with_client_certs(
        self, mock_create_client, mock_mqtt_client, mock_exists
    ):
        """Test TLS configuration with client certificates."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        tls_config = TLSConfig(
            enabled=True,
            ca_certs="/path/to/ca.crt",
            certfile="/path/to/client.crt",
            keyfile="/path/to/client.key",
        )
        mqtt_config = MQTTConfig(host="localhost", port=8883, tls=tls_config)

        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        args, kwargs = mock_client_instance.tls_set.call_args
        assert kwargs["certfile"] == "/path/to/client.crt"
        assert kwargs["keyfile"] == "/path/to/client.key"

    @patch("os.path.exists", return_value=True)
    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_tls_insecure_mode(self, mock_create_client, mock_mqtt_client, mock_exists):
        """Test TLS insecure mode (skip certificate verification)."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        tls_config = TLSConfig(enabled=True, ca_certs="/path/to/ca.crt", insecure=True)
        mqtt_config = MQTTConfig(host="localhost", port=8883, tls=tls_config)

        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        mock_client_instance.tls_insecure_set.assert_called_once_with(True)

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_tls_not_configured_when_disabled(self, mock_create_client, mock_mqtt_client):
        """Test TLS is not configured when disabled."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883, tls=None)  # No TLS configuration

        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        mock_client_instance.tls_set.assert_not_called()


class TestLWTConfiguration:
    """Test Last Will and Testament configuration."""

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_lwt_configuration_basic(self, mock_create_client, mock_mqtt_client):
        """Test basic LWT configuration."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        lwt_config = LWTConfig(topic="vestaboard/status")
        mqtt_config = MQTTConfig(host="localhost", port=1883, lwt=lwt_config)

        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        mock_client_instance.will_set.assert_called_once_with(
            "vestaboard/status", "offline", 0, True
        )

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_lwt_configuration_custom(self, mock_create_client, mock_mqtt_client):
        """Test LWT configuration with custom values."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        lwt_config = LWTConfig(
            topic="status/vestaboard", payload="disconnected", qos=2, retain=False
        )
        mqtt_config = MQTTConfig(host="localhost", port=1883, lwt=lwt_config)

        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        mock_client_instance.will_set.assert_called_once_with(
            "status/vestaboard", "disconnected", 2, False
        )

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_lwt_not_configured_when_absent(self, mock_create_client, mock_mqtt_client):
        """Test LWT is not configured when not specified."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883)

        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        mock_client_instance.will_set.assert_not_called()


class TestTopicHandling:
    """Test topic path construction and handling."""

    @patch("src.vestaboard.create_vestaboard_client")
    def test_get_topic_with_default_prefix(self, mock_create_client):
        """Test _get_topic constructs correct paths with default prefix."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        assert bridge.get_topic("message") == "vestaboard/message"
        assert bridge.get_topic("save/slot1") == "vestaboard/save/slot1"
        assert bridge.get_topic("timed-message") == "vestaboard/timed-message"

    @patch("src.vestaboard.create_vestaboard_client")
    def test_get_topic_with_custom_prefix(self, mock_create_client):
        """Test _get_topic constructs correct paths with custom prefix."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883, topic_prefix="office-board")
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        assert bridge.get_topic("message") == "office-board/message"
        assert bridge.get_topic("save/slot1") == "office-board/save/slot1"


class TestMQTTCallbacks:
    """Test MQTT connection and message callbacks."""

    @patch("src.vestaboard.create_vestaboard_client")
    def test_on_connect_success(self, mock_create_client):
        """Test successful MQTT connection callback."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        mock_client = Mock()
        bridge._on_connect(mock_client, None, None, 0)

        # Verify all topics were subscribed
        assert mock_client.subscribe.call_count == 8
        expected_topics = [
            "vestaboard/message",
            "vestaboard/message/+",
            "vestaboard/save/+",
            "vestaboard/restore/+",
            "vestaboard/delete/+",
            "vestaboard/timed-message",
            "vestaboard/cancel-timer/+",
            "vestaboard/list-timers",
        ]
        for topic in expected_topics:
            mock_client.subscribe.assert_any_call(topic, qos=0)

    @patch("src.vestaboard.create_vestaboard_client")
    def test_on_connect_with_custom_qos(self, mock_create_client):
        """Test connection callback uses custom QoS."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883, qos=1)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        mock_client = Mock()
        bridge._on_connect(mock_client, None, None, 0)

        # Verify QoS was used
        for call_args in mock_client.subscribe.call_args_list:
            assert call_args[1]["qos"] == 1

    @patch("src.vestaboard.create_vestaboard_client")
    def test_on_disconnect(self, mock_create_client):
        """Test MQTT disconnect callback."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Should not raise exception
        bridge._on_disconnect(Mock(), None, 0)


class TestMessageHandling:
    """Test handling of different message types."""

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_text_message(self, mock_create_client):
        """Test handling plain text message."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        bridge.handlers.handle_message("HELLO WORLD")

        mock_client.write_message.assert_called_once_with("HELLO WORLD")

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_json_layout_array(self, mock_create_client):
        """Test handling JSON layout array."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        layout = [[1, 2, 3], [4, 5, 6]]
        bridge.handlers.handle_message(json.dumps(layout))

        mock_client.write_message.assert_called_once_with(layout)

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_json_text_object(self, mock_create_client):
        """Test handling JSON object with text field."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        message_obj = {"text": "HELLO"}
        bridge.handlers.handle_message(json.dumps(message_obj))

        mock_client.write_message.assert_called_once_with("HELLO")

    @patch("src.vestaboard.create_vestaboard_client")
    def test_on_message_routes_to_message_handler(self, mock_create_client):
        """Test that on_message routes message topic correctly."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        mock_message = Mock()
        mock_message.topic = "vestaboard/message"
        mock_message.payload = b"TEST"

        bridge._on_message(None, None, mock_message)

        mock_client.write_message.assert_called_once_with("TEST")


class TestSaveRestoreDelete:
    """Test save, restore, and delete operations."""

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_save(self, mock_create_client):
        """Test handling save request."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        with patch.object(bridge.save_state_manager, "save_current_state", return_value=True):
            bridge.handlers.handle_save("test_slot")
            bridge.save_state_manager.save_current_state.assert_called_once_with("test_slot")

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_restore_request(self, mock_create_client):
        """Test handling restore request."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        with patch.object(bridge, "restore_from_slot"):
            bridge.handlers.handle_restore_request("test_slot")
            bridge.restore_from_slot.assert_called_once_with(
                "test_slot", strategy=None, step_interval_ms=None, step_size=None
            )

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_delete(self, mock_create_client):
        """Test handling delete request."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        with patch.object(bridge.save_state_manager, "delete_saved_state", return_value=True):
            bridge.handlers.handle_delete("test_slot")
            bridge.save_state_manager.delete_saved_state.assert_called_once_with("test_slot")

    @patch("src.vestaboard.create_vestaboard_client")
    def test_on_message_routes_save_topic(self, mock_create_client):
        """Test routing of save topic."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        mock_message = Mock()
        mock_message.topic = "vestaboard/save/slot1"
        mock_message.payload = b""

        with patch.object(bridge.handlers, "handle_save"):
            bridge._on_message(None, None, mock_message)
            bridge.handlers.handle_save.assert_called_once_with("slot1")

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_restore_with_animation(self, mock_create_client):
        """Test manual restore with animation via JSON payload."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        payload = json.dumps({"strategy": "column", "step_interval_ms": 1500, "step_size": 3})

        with patch.object(bridge, "restore_from_slot") as mock_restore:
            bridge.handlers.handle_restore_request("my_slot", payload)
            mock_restore.assert_called_once_with(
                "my_slot", strategy="column", step_interval_ms=1500, step_size=3
            )

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_restore_without_animation(self, mock_create_client):
        """Test manual restore without animation (backward compatibility)."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        with patch.object(bridge, "restore_from_slot") as mock_restore:
            bridge.handlers.handle_restore_request("my_slot", "")
            mock_restore.assert_called_once_with(
                "my_slot", strategy=None, step_interval_ms=None, step_size=None
            )

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_restore_invalid_json_payload(self, mock_create_client):
        """Test manual restore with invalid JSON payload (should ignore and continue)."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        with patch.object(bridge, "restore_from_slot") as mock_restore:
            bridge.handlers.handle_restore_request("my_slot", "not valid json")
            # Should still call restore but without animation params
            mock_restore.assert_called_once_with(
                "my_slot", strategy=None, step_interval_ms=None, step_size=None
            )


class TestTimedMessages:
    """Test timed message functionality."""

    @patch("src.vestaboard.create_vestaboard_client")
    @patch("src.mqtt.timers.threading.Timer")
    def test_schedule_timed_message_basic(self, mock_timer, mock_create_client):
        """Test scheduling a basic timed message."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        with patch.object(bridge.save_state_manager, "save_current_state", return_value=True):
            timer_id = bridge.timer_manager.schedule_timed_message("TEST", 30)

            assert timer_id.startswith("timer_")
            assert timer_id in bridge.timer_manager.active_timers
            mock_client.write_message.assert_called_once_with("TEST")
            mock_timer.assert_called_once()

    @patch("src.vestaboard.create_vestaboard_client")
    @patch("src.mqtt.timers.threading.Timer")
    def test_schedule_timed_message_with_restore_slot(self, mock_timer, mock_create_client):
        """Test scheduling timed message with custom restore slot."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        timer_id = bridge.timer_manager.schedule_timed_message(
            "TEST", 30, restore_slot="custom_slot"
        )

        # Should not call save_current_state when restore_slot is provided
        assert timer_id.startswith("timer_")
        mock_client.write_message.assert_called_once_with("TEST")

    @patch("src.vestaboard.create_vestaboard_client")
    def test_cancel_timed_message(self, mock_create_client):
        """Test cancelling a timed message."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Add a mock timer
        mock_timer = Mock()
        bridge.timer_manager.active_timers["timer_123"] = mock_timer

        success = bridge.timer_manager.cancel_timed_message("timer_123")

        assert success is True
        mock_timer.cancel.assert_called_once()
        assert "timer_123" not in bridge.timer_manager.active_timers

    @patch("src.vestaboard.create_vestaboard_client")
    def test_cancel_nonexistent_timer(self, mock_create_client):
        """Test cancelling a non-existent timer."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        success = bridge.timer_manager.cancel_timed_message("nonexistent")

        assert success is False

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_timed_message(self, mock_create_client):
        """Test handling timed message via MQTT."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        payload = json.dumps({"message": "ALERT", "duration_seconds": 60})

        with patch.object(bridge.timer_manager, "schedule_timed_message", return_value="timer_456"):
            bridge.handlers.handle_timed_message(payload)
            bridge.timer_manager.schedule_timed_message.assert_called_once_with(
                message="ALERT",
                duration_seconds=60,
                restore_slot=None,
                strategy=None,
                step_interval_ms=None,
                step_size=None,
                restore_strategy=None,
                restore_step_interval_ms=None,
                restore_step_size=None,
            )

    @patch("src.vestaboard.create_vestaboard_client")
    @patch("src.mqtt.timers.threading.Timer")
    def test_timed_message_with_animation_local_api(self, mock_timer, mock_create_client):
        """Test timed message with animation strategy on Local API."""
        from src.vestaboard.local_client import LocalVestaboardClient

        mock_local_client = Mock(spec=LocalVestaboardClient)
        mock_local_client.write_animated_message.return_value = True
        mock_create_client.return_value = mock_local_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        with patch.object(bridge.save_state_manager, "save_current_state", return_value=True):
            timer_id = bridge.timer_manager.schedule_timed_message(
                message="ALERT",
                duration_seconds=30,
                strategy="column",
            )

            assert timer_id.startswith("timer_")
            mock_local_client.write_animated_message.assert_called_once_with(
                message="ALERT",
                strategy="column",
                step_interval_ms=None,
                step_size=None,
            )

    @patch("src.vestaboard.create_vestaboard_client")
    @patch("src.mqtt.timers.threading.Timer")
    def test_timed_message_with_animation_cloud_api(self, mock_timer, mock_create_client):
        """Test timed message with animation strategy on Cloud API (should warn and use regular)."""
        from src.vestaboard.cloud_client import VestaboardClient

        mock_cloud_client = Mock(spec=VestaboardClient)
        mock_cloud_client.write_message.return_value = True
        mock_create_client.return_value = mock_cloud_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        with patch.object(bridge.save_state_manager, "save_current_state", return_value=True):
            timer_id = bridge.timer_manager.schedule_timed_message(
                message="ALERT",
                duration_seconds=30,
                strategy="column",
            )

            assert timer_id.startswith("timer_")
            mock_cloud_client.write_message.assert_called_once_with("ALERT")
            assert not hasattr(mock_cloud_client, "write_animated_message")

    @patch("src.vestaboard.create_vestaboard_client")
    @patch("src.mqtt.timers.threading.Timer")
    def test_timed_message_with_animation_timing_params(self, mock_timer, mock_create_client):
        """Test timed message with animation timing parameters."""
        from src.vestaboard.local_client import LocalVestaboardClient

        mock_local_client = Mock(spec=LocalVestaboardClient)
        mock_local_client.write_animated_message.return_value = True
        mock_create_client.return_value = mock_local_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        with patch.object(bridge.save_state_manager, "save_current_state", return_value=True):
            timer_id = bridge.timer_manager.schedule_timed_message(
                message="ALERT",
                duration_seconds=30,
                strategy="edges-to-center",
                step_interval_ms=2000,
                step_size=5,
            )

            assert timer_id.startswith("timer_")
            mock_local_client.write_animated_message.assert_called_once_with(
                message="ALERT",
                strategy="edges-to-center",
                step_interval_ms=2000,
                step_size=5,
            )

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_timed_message_with_animation(self, mock_create_client):
        """Test handling timed message with animation via MQTT."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        payload = json.dumps({
            "message": "ALERT",
            "duration_seconds": 60,
            "strategy": "column",
            "step_interval_ms": 1500,
            "step_size": 3,
        })

        with patch.object(bridge.timer_manager, "schedule_timed_message", return_value="timer_789"):
            bridge.handlers.handle_timed_message(payload)
            bridge.timer_manager.schedule_timed_message.assert_called_once_with(
                message="ALERT",
                duration_seconds=60,
                restore_slot=None,
                strategy="column",
                step_interval_ms=1500,
                step_size=3,
                restore_strategy=None,
                restore_step_interval_ms=None,
                restore_step_size=None,
            )

    @patch("src.vestaboard.create_vestaboard_client")
    def test_timed_message_restore_inherits_animation(self, mock_create_client):
        """Test that restore inherits animation params from timed message by default."""
        from src.vestaboard.local_client import LocalVestaboardClient

        mock_local_client = Mock(spec=LocalVestaboardClient)
        mock_local_client.write_animated_message.return_value = True
        mock_local_client.RATE_LIMIT_SECONDS = 1
        mock_create_client.return_value = mock_local_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Create a mock restore callback to capture params
        mock_restore_callback = Mock()

        # Replace the restore_callback in timer_manager
        bridge.timer_manager.restore_callback = mock_restore_callback

        with patch.object(bridge.save_state_manager, "save_current_state", return_value=True):
            # Schedule timed message with animation
            timer_id = bridge.timer_manager.schedule_timed_message(
                message="ALERT",
                duration_seconds=30,
                strategy="column",
                step_interval_ms=1500,
                step_size=3,
            )

            # Get and execute the timer callback
            timer = bridge.timer_manager.active_timers[timer_id]
            timer.function()

            # Verify restore was called with same animation params
            mock_restore_callback.assert_called_once()
            call_args = mock_restore_callback.call_args
            assert call_args[1]["strategy"] == "column"
            assert call_args[1]["step_interval_ms"] == 1500
            assert call_args[1]["step_size"] == 3

    @patch("src.vestaboard.create_vestaboard_client")
    def test_timed_message_restore_custom_animation(self, mock_create_client):
        """Test that restore can use different animation than timed message."""
        from src.vestaboard.local_client import LocalVestaboardClient

        mock_local_client = Mock(spec=LocalVestaboardClient)
        mock_local_client.write_animated_message.return_value = True
        mock_local_client.RATE_LIMIT_SECONDS = 1
        mock_create_client.return_value = mock_local_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Create a mock restore callback to capture params
        mock_restore_callback = Mock()

        # Replace the restore_callback in timer_manager
        bridge.timer_manager.restore_callback = mock_restore_callback

        with patch.object(bridge.save_state_manager, "save_current_state", return_value=True):
            # Schedule with different restore animation
            timer_id = bridge.timer_manager.schedule_timed_message(
                message="ALERT",
                duration_seconds=30,
                strategy="column",
                step_interval_ms=1500,
                step_size=3,
                restore_strategy="reverse-column",
                restore_step_interval_ms=2000,
                restore_step_size=5,
            )

            # Get and execute the timer callback
            timer = bridge.timer_manager.active_timers[timer_id]
            timer.function()

            # Verify restore was called with custom animation params
            mock_restore_callback.assert_called_once()
            call_args = mock_restore_callback.call_args
            assert call_args[1]["strategy"] == "reverse-column"
            assert call_args[1]["step_interval_ms"] == 2000
            assert call_args[1]["step_size"] == 5

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_cancel_timer(self, mock_create_client):
        """Test handling cancel timer request."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        with patch.object(bridge.timer_manager, "cancel_timed_message", return_value=True):
            bridge.handlers.handle_cancel_timer("timer_123")
            bridge.timer_manager.cancel_timed_message.assert_called_once_with("timer_123")

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_list_timers(self, mock_create_client):
        """Test handling list timers request."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Add some mock timers
        mock_timer1 = Mock()
        mock_timer1.is_alive.return_value = True
        mock_timer2 = Mock()
        mock_timer2.is_alive.return_value = True

        bridge.timer_manager.active_timers = {
            "timer_1234567890": mock_timer1,
            "timer_1234567891": mock_timer2,
        }

        bridge.mqtt_client.publish = Mock()
        bridge.handlers.handle_list_timers("")

        # Verify publish was called
        assert bridge.mqtt_client.publish.called
        call_args = bridge.mqtt_client.publish.call_args[0]
        response_data = json.loads(call_args[1])

        assert response_data["total_count"] == 2
        assert len(response_data["active_timers"]) == 2


class TestStopCleanup:
    """Test cleanup on stop."""

    @patch("src.vestaboard.create_vestaboard_client")
    def test_stop_cancels_all_timers(self, mock_create_client):
        """Test that stop() cancels all active timers."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Add mock timers
        mock_timer1 = Mock()
        mock_timer2 = Mock()
        bridge.timer_manager.active_timers = {"timer_1": mock_timer1, "timer_2": mock_timer2}

        bridge.stop()

        mock_timer1.cancel.assert_called_once()
        mock_timer2.cancel.assert_called_once()
        assert len(bridge.timer_manager.active_timers) == 0

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_stop_disconnects_mqtt(self, mock_create_client, mock_mqtt_client):
        """Test that stop() disconnects MQTT client."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        bridge.stop()

        mock_client_instance.disconnect.assert_called_once()
        mock_client_instance.loop_stop.assert_called_once()


class TestAnimatedMessages:
    """Test animated message handling via MQTT."""

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_message_with_strategy_local_api(self, mock_create_client):
        """Test handling message with animation strategy on Local API."""
        from src.vestaboard.local_client import LocalVestaboardClient

        mock_local_client = Mock(spec=LocalVestaboardClient)
        mock_local_client.write_animated_message.return_value = True
        mock_create_client.return_value = mock_local_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        bridge.handlers.handle_message("TEST MESSAGE", strategy="column")

        mock_local_client.write_animated_message.assert_called_once_with(
            message="TEST MESSAGE", strategy="column", step_interval_ms=None, step_size=None
        )

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_message_with_strategy_cloud_api(self, mock_create_client):
        """Test handling message with animation strategy on Cloud API (should warn)."""
        from src.vestaboard.cloud_client import VestaboardClient

        mock_cloud_client = Mock(spec=VestaboardClient)
        mock_cloud_client.write_message.return_value = True
        mock_create_client.return_value = mock_cloud_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        bridge.handlers.handle_message("TEST MESSAGE", strategy="column")

        mock_cloud_client.write_message.assert_called_once_with("TEST MESSAGE")
        assert not hasattr(mock_cloud_client, "write_animated_message")

    @patch("src.vestaboard.create_vestaboard_client")
    def test_handle_message_with_timing_params(self, mock_create_client):
        """Test handling message with animation timing parameters."""
        from src.vestaboard.local_client import LocalVestaboardClient

        mock_local_client = Mock(spec=LocalVestaboardClient)
        mock_local_client.write_animated_message.return_value = True
        mock_create_client.return_value = mock_local_client

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        payload = json.dumps({"text": "HELLO", "step_interval_ms": 2000, "step_size": 3})
        bridge.handlers.handle_message(payload, strategy="random")

        mock_local_client.write_animated_message.assert_called_once_with(
            message="HELLO", strategy="random", step_interval_ms=2000, step_size=3
        )

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_message_routing_with_strategy(self, mock_create_client, mock_mqtt_client):
        """Test routing of message/{strategy} topics."""
        from src.vestaboard.local_client import LocalVestaboardClient

        mock_local_client = Mock(spec=LocalVestaboardClient)
        mock_local_client.write_animated_message.return_value = True
        mock_create_client.return_value = mock_local_client

        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883, topic_prefix="vestaboard")
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Simulate message on vestaboard/message/column topic
        mock_message = Mock()
        mock_message.topic = "vestaboard/message/column"
        mock_message.payload = b"TEST"

        bridge._on_message(mock_client_instance, None, mock_message)

        mock_local_client.write_animated_message.assert_called_once()
        call_args = mock_local_client.write_animated_message.call_args
        assert call_args[1]["strategy"] == "column"

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_message_routing_with_empty_strategy(self, mock_create_client, mock_mqtt_client):
        """Test routing of message/ topic with empty strategy (edge case)."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883, topic_prefix="vestaboard")
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Simulate message on vestaboard/message/ topic (trailing slash, no strategy)
        mock_message = Mock()
        mock_message.topic = "vestaboard/message/"
        mock_message.payload = b"TEST"

        bridge._on_message(mock_client_instance, None, mock_message)

        # Should be handled as regular message, not animated
        mock_client.write_message.assert_called_once_with("TEST")
        # Ensure animated method was NOT called
        assert not hasattr(mock_client, "write_animated_message") or not mock_client.write_animated_message.called
