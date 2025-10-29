"""Tests for MQTT bridge error handling and edge cases."""

import json
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from src.config import AppConfig, MQTTConfig
from src.mqtt import VestaboardMQTTBridge
from tests.conftest import create_test_app_config


class TestMQTTConnectionErrors:
    """Test MQTT connection error handling."""

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_mqtt_connection_failure(self, mock_create_client, mock_mqtt_client):
        """Test handling of MQTT connection failures."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        # Simulate connection failure
        mock_client_instance.connect.side_effect = Exception("Connection refused")

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # start() logs the error but doesn't re-raise
        try:
            bridge.start()
        except Exception:
            pass  # Expected to be caught and logged

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_mqtt_disconnect_handling(self, mock_create_client, mock_mqtt_client):
        """Test MQTT disconnect callback."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Call disconnect callback
        bridge._on_disconnect(mock_client_instance, None, 0)
        # Should log disconnect but not crash


class TestTimedMessageEdgeCases:
    """Test timed message edge cases."""

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_timed_message_missing_fields(self, mock_create_client, mock_mqtt_client):
        """Test timed message with missing required fields."""
        mock_vestaboard = Mock()
        mock_create_client.return_value = mock_vestaboard
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Message missing duration_seconds
        payload = json.dumps({"message": "Test"})
        msg = Mock()
        msg.payload = payload.encode()
        msg.topic = "vestaboard/timed-message"

        bridge.handlers.handle_timed_message(msg)
        # Should handle gracefully without crashing

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_timed_message_invalid_json(self, mock_create_client, mock_mqtt_client):
        """Test timed message with invalid JSON."""
        mock_vestaboard = Mock()
        mock_create_client.return_value = mock_vestaboard
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        msg = Mock()
        msg.payload = b"not valid json"
        msg.topic = "vestaboard/timed-message"

        bridge.handlers.handle_timed_message(msg)
        # Should handle gracefully without crashing

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_cancel_nonexistent_timer(self, mock_create_client, mock_mqtt_client):
        """Test canceling a timer that doesn't exist."""
        mock_vestaboard = Mock()
        mock_create_client.return_value = mock_vestaboard
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        msg = Mock()
        msg.payload = b"nonexistent_timer_id"
        msg.topic = "vestaboard/cancel-timer/nonexistent_timer_id"

        bridge.handlers.handle_cancel_timer(msg)
        # Should handle gracefully without crashing


class TestMessageHandlingEdgeCases:
    """Test message handling edge cases."""

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_write_message_failure(self, mock_create_client, mock_mqtt_client):
        """Test handling of vestaboard write failures."""
        mock_vestaboard = Mock()
        mock_vestaboard.write_message.return_value = False
        mock_create_client.return_value = mock_vestaboard
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        msg = Mock()
        msg.payload = b"Test message"
        msg.topic = "vestaboard/message"

        bridge._on_message(mock_client_instance, None, msg)
        # Should handle failure gracefully
        assert mock_vestaboard.write_message.called

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_message_with_json_array(self, mock_create_client, mock_mqtt_client):
        """Test message with JSON array payload."""
        mock_vestaboard = Mock()
        mock_vestaboard.write_message.return_value = True
        mock_create_client.return_value = mock_vestaboard
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Send JSON array
        layout = [[0] * 22 for _ in range(6)]
        msg = Mock()
        msg.payload = json.dumps(layout).encode()
        msg.topic = "vestaboard/message"

        bridge._on_message(mock_client_instance, None, msg)
        # Should parse as JSON and send
        mock_vestaboard.write_message.assert_called_with(layout)

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_message_invalid_json_treated_as_text(self, mock_create_client, mock_mqtt_client):
        """Test that invalid JSON is treated as text message."""
        mock_vestaboard = Mock()
        mock_vestaboard.write_message.return_value = True
        mock_create_client.return_value = mock_vestaboard
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        msg = Mock()
        msg.payload = b"{not valid json"
        msg.topic = "vestaboard/message"

        bridge._on_message(mock_client_instance, None, msg)
        # Should send as text
        mock_vestaboard.write_message.assert_called_with("{not valid json")


class TestRestoreFromSlot:
    """Test restore from slot functionality."""

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_restore_from_slot_sets_up_callback(self, mock_create_client, mock_mqtt_client):
        """Test that restore from slot sets up MQTT callback."""
        mock_vestaboard = Mock()
        mock_create_client.return_value = mock_vestaboard
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Should set up callback and subscribe without crashing
        bridge.restore_from_slot("test_slot")

        # Verify callback was added and subscribe was called
        assert mock_client_instance.message_callback_add.called
        assert mock_client_instance.subscribe.called


class TestSaveAndDeleteSlots:
    """Test save and delete slot functionality."""

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_save_current_state_failure(self, mock_create_client, mock_mqtt_client):
        """Test handling of save state failures."""
        mock_vestaboard = Mock()
        mock_vestaboard.read_current_message.return_value = None
        mock_create_client.return_value = mock_vestaboard
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)
        bridge.state_manager = Mock()

        msg = Mock()
        msg.payload = b""
        msg.topic = "vestaboard/save/test_slot"

        bridge._on_message(mock_client_instance, None, msg)
        # Should handle failure gracefully

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_delete_slot(self, mock_create_client, mock_mqtt_client):
        """Test deleting a saved slot."""
        mock_vestaboard = Mock()
        mock_create_client.return_value = mock_vestaboard
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883, topic_prefix="vestaboard")
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)
        bridge.save_state_manager = Mock()
        bridge.save_state_manager.delete_saved_state.return_value = True

        # Test _handle_delete directly
        bridge.handlers.handle_delete("test_slot")
        bridge.save_state_manager.delete_saved_state.assert_called_with("test_slot")


class TestListTimers:
    """Test list timers functionality."""

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_list_timers_empty(self, mock_create_client, mock_mqtt_client):
        """Test listing timers when none are active."""
        mock_vestaboard = Mock()
        mock_create_client.return_value = mock_vestaboard
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883, topic_prefix="test")
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Call _handle_list_timers directly
        bridge.handlers.handle_list_timers("")
        # Should publish empty list
        assert mock_client_instance.publish.called
        # Verify payload contains empty list
        call_args = mock_client_instance.publish.call_args
        payload = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs["payload"]
        assert "[]" in payload or payload == "[]"

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_list_timers_with_active_timers(self, mock_create_client, mock_mqtt_client):
        """Test listing timers when some are active."""
        mock_vestaboard = Mock()
        mock_create_client.return_value = mock_vestaboard
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883, topic_prefix="test")
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Add a mock timer (active_timers stores Timer objects directly)
        mock_timer = Mock()
        mock_timer.is_alive.return_value = True  # Timer needs is_alive() method
        bridge.timer_manager.active_timers["timer_123"] = mock_timer

        # Call _handle_list_timers directly
        bridge.handlers.handle_list_timers("")
        # Should publish timer info
        assert mock_client_instance.publish.called
        # Verify payload contains timer info
        call_args = mock_client_instance.publish.call_args
        if len(call_args[0]) > 1:
            payload = str(call_args[0][1])
        else:
            payload = str(call_args.kwargs.get("payload", ""))
        assert "timer_123" in payload


class TestTimerCancellation:
    """Test timer cancellation functionality."""

    @patch("src.mqtt.bridge.mqtt.Client")
    @patch("src.vestaboard.create_vestaboard_client")
    def test_cancel_timer_success(self, mock_create_client, mock_mqtt_client):
        """Test successful timer cancellation."""
        mock_vestaboard = Mock()
        mock_create_client.return_value = mock_vestaboard
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port=1883)
        config = create_test_app_config(mqtt_config=mqtt_config)
        bridge = VestaboardMQTTBridge(config)

        # Add a mock timer (active_timers stores Timer objects directly)
        mock_timer = Mock()
        bridge.timer_manager.active_timers["timer_123"] = mock_timer

        # Cancel the timer directly
        bridge.handlers.handle_cancel_timer("timer_123")

        # Timer should be cancelled
        mock_timer.cancel.assert_called_once()
        # Timer should be removed from active_timers
        assert "timer_123" not in bridge.timer_manager.active_timers
