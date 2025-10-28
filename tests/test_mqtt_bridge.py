"""Comprehensive tests for VestaboardMQTTBridge."""

import json
import ssl
import time
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import paho.mqtt.client as mqtt
from src.mqtt_bridge import VestaboardMQTTBridge
from src.config import MQTTConfig, TLSConfig, LWTConfig


class TestMQTTBridgeInitialization:
    """Test VestaboardMQTTBridge initialization with different configurations."""

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_initialization_with_defaults(self, mock_create_client):
        """Test bridge initializes with default configuration."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        assert bridge.topic_prefix =="vestaboard"
        assert bridge.qos == 0
        assert bridge.vestaboard_client == mock_client
        assert len(bridge.active_timers) == 0
        mock_create_client.assert_called_once_with(api_key="test_key", max_queue_size=10)

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_initialization_with_custom_topic_prefix(self, mock_create_client):
        """Test bridge initializes with custom topic prefix."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(
            host="localhost",
            port= 1883,
            topic_prefix="office-board"
        )
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        assert bridge.topic_prefix =="office-board"

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_initialization_strips_trailing_slash(self, mock_create_client):
        """Test that topic prefix strips trailing slashes."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(
            host="localhost",
            port= 1883,
            topic_prefix="vestaboard/"
        )
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        assert bridge.topic_prefix =="vestaboard"

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_initialization_with_custom_qos(self, mock_create_client):
        """Test bridge initializes with custom QoS level."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(
            host="localhost",
            port= 1883,
            qos= 2
        )
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        assert bridge.qos == 2

    @patch('src.mqtt_bridge.mqtt.Client')
    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_initialization_with_authentication(self, mock_create_client, mock_mqtt_client):
        """Test bridge sets up MQTT authentication."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(
            host="localhost",
            port= 1883,
            username="test_user",
            password="test_pass"
        )
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        # Verify username_pw_set was called on the MQTT client
        mock_client_instance.username_pw_set.assert_called_once_with("test_user", "test_pass")

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_initialization_with_custom_client_id(self, mock_create_client):
        """Test bridge uses custom MQTT client ID."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(
            host="localhost",
            port= 1883,
            client_id="custom-vestaboard-1"
        )

        with patch('src.mqtt_bridge.mqtt.Client') as mock_mqtt_client:
            bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)
            mock_mqtt_client.assert_called_once_with(client_id="custom-vestaboard-1", clean_session=True)

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_initialization_with_persistent_session(self, mock_create_client):
        """Test bridge uses persistent session when configured."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(
            host="localhost",
            port= 1883,
            clean_session= False
        )

        with patch('src.mqtt_bridge.mqtt.Client') as mock_mqtt_client:
            bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)
            mock_mqtt_client.assert_called_once_with(client_id="", clean_session=False)

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_initialization_with_max_queue_size(self, mock_create_client):
        """Test bridge passes max_queue_size to Vestaboard client."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(
            vestaboard_api_key="test_key",
            mqtt_config=mqtt_config,
            max_queue_size=20
        )

        mock_create_client.assert_called_once_with(api_key="test_key", max_queue_size=20)


class TestTLSConfiguration:
    """Test TLS/SSL configuration for MQTT connection."""

    @patch('os.path.exists', return_value=True)
    @patch('src.mqtt_bridge.mqtt.Client')
    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_tls_configuration_basic(self, mock_create_client, mock_mqtt_client, mock_exists):
        """Test basic TLS configuration."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        tls_config = TLSConfig(
            enabled=True,
            ca_certs="/path/to/ca.crt"
        )
        mqtt_config = MQTTConfig(
            host="localhost",
            port=8883,
            tls=tls_config
        )

        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        mock_client_instance.tls_set.assert_called_once()
        args, kwargs = mock_client_instance.tls_set.call_args
        assert kwargs['ca_certs'] == "/path/to/ca.crt"
        assert kwargs['cert_reqs'] == ssl.CERT_REQUIRED
        assert kwargs['tls_version'] == ssl.PROTOCOL_TLS

    @patch('os.path.exists', return_value=True)
    @patch('src.mqtt_bridge.mqtt.Client')
    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_tls_configuration_with_client_certs(self, mock_create_client, mock_mqtt_client, mock_exists):
        """Test TLS configuration with client certificates."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        tls_config = TLSConfig(
            enabled=True,
            ca_certs="/path/to/ca.crt",
            certfile="/path/to/client.crt",
            keyfile="/path/to/client.key"
        )
        mqtt_config = MQTTConfig(
            host="localhost",
            port=8883,
            tls=tls_config
        )

        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        args, kwargs = mock_client_instance.tls_set.call_args
        assert kwargs['certfile'] == "/path/to/client.crt"
        assert kwargs['keyfile'] == "/path/to/client.key"

    @patch('os.path.exists', return_value=True)
    @patch('src.mqtt_bridge.mqtt.Client')
    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_tls_insecure_mode(self, mock_create_client, mock_mqtt_client, mock_exists):
        """Test TLS insecure mode (skip certificate verification)."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        tls_config = TLSConfig(
            enabled=True,
            ca_certs="/path/to/ca.crt",
            insecure=True
        )
        mqtt_config = MQTTConfig(
            host="localhost",
            port=8883,
            tls=tls_config
        )

        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        mock_client_instance.tls_insecure_set.assert_called_once_with(True)

    @patch('src.mqtt_bridge.mqtt.Client')
    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_tls_not_configured_when_disabled(self, mock_create_client, mock_mqtt_client):
        """Test TLS is not configured when disabled."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(
            host="localhost",
            port=1883,
            tls=None  # No TLS configuration
        )

        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        mock_client_instance.tls_set.assert_not_called()


class TestLWTConfiguration:
    """Test Last Will and Testament configuration."""

    @patch('src.mqtt_bridge.mqtt.Client')
    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_lwt_configuration_basic(self, mock_create_client, mock_mqtt_client):
        """Test basic LWT configuration."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        lwt_config = LWTConfig(topic="vestaboard/status")
        mqtt_config = MQTTConfig(
            host="localhost",
            port=1883,
            lwt=lwt_config
        )

        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        mock_client_instance.will_set.assert_called_once_with(
            "vestaboard/status",
            "offline",
            0,
            True
        )

    @patch('src.mqtt_bridge.mqtt.Client')
    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_lwt_configuration_custom(self, mock_create_client, mock_mqtt_client):
        """Test LWT configuration with custom values."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        lwt_config = LWTConfig(
            topic="status/vestaboard",
            payload="disconnected",
            qos=2,
            retain=False
        )
        mqtt_config = MQTTConfig(
            host="localhost",
            port=1883,
            lwt=lwt_config
        )

        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        mock_client_instance.will_set.assert_called_once_with(
            "status/vestaboard",
            "disconnected",
            2,
            False
        )

    @patch('src.mqtt_bridge.mqtt.Client')
    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_lwt_not_configured_when_absent(self, mock_create_client, mock_mqtt_client):
        """Test LWT is not configured when not specified."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(
            host="localhost",
            port= 1883
        )

        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        mock_client_instance.will_set.assert_not_called()


class TestTopicHandling:
    """Test topic path construction and handling."""

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_get_topic_with_default_prefix(self, mock_create_client):
        """Test _get_topic constructs correct paths with default prefix."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        assert bridge._get_topic("message") =="vestaboard/message"
        assert bridge._get_topic("save/slot1") =="vestaboard/save/slot1"
        assert bridge._get_topic("timed-message") =="vestaboard/timed-message"

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_get_topic_with_custom_prefix(self, mock_create_client):
        """Test _get_topic constructs correct paths with custom prefix."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(
            host="localhost",
            port= 1883,
            topic_prefix="office-board"
        )
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        assert bridge._get_topic("message") =="office-board/message"
        assert bridge._get_topic("save/slot1") =="office-board/save/slot1"


class TestMQTTCallbacks:
    """Test MQTT connection and message callbacks."""

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_on_connect_success(self, mock_create_client):
        """Test successful MQTT connection callback."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        mock_client = Mock()
        bridge._on_connect(mock_client, None, None, 0)

        # Verify all topics were subscribed
        assert mock_client.subscribe.call_count == 7
        expected_topics = [
            "vestaboard/message",
            "vestaboard/save/+",
            "vestaboard/restore/+",
            "vestaboard/delete/+",
            "vestaboard/timed-message",
            "vestaboard/cancel-timer/+",
            "vestaboard/list-timers"
        ]
        for topic in expected_topics:
            mock_client.subscribe.assert_any_call(topic, qos=0)

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_on_connect_with_custom_qos(self, mock_create_client):
        """Test connection callback uses custom QoS."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(
            host="localhost",
            port= 1883,
            qos= 1
        )
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        mock_client = Mock()
        bridge._on_connect(mock_client, None, None, 0)

        # Verify QoS was used
        for call_args in mock_client.subscribe.call_args_list:
            assert call_args[1]['qos'] == 1

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_on_disconnect(self, mock_create_client):
        """Test MQTT disconnect callback."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        # Should not raise exception
        bridge._on_disconnect(Mock(), None, 0)


class TestMessageHandling:
    """Test handling of different message types."""

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_handle_text_message(self, mock_create_client):
        """Test handling plain text message."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        bridge._handle_message("HELLO WORLD")

        mock_client.write_message.assert_called_once_with("HELLO WORLD")

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_handle_json_layout_array(self, mock_create_client):
        """Test handling JSON layout array."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        layout = [[1, 2, 3], [4, 5, 6]]
        bridge._handle_message(json.dumps(layout))

        mock_client.write_message.assert_called_once_with(layout)

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_handle_json_text_object(self, mock_create_client):
        """Test handling JSON object with text field."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        message_obj = {"text": "HELLO"}
        bridge._handle_message(json.dumps(message_obj))

        mock_client.write_message.assert_called_once_with("HELLO")

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_on_message_routes_to_message_handler(self, mock_create_client):
        """Test that on_message routes message topic correctly."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        mock_message = Mock()
        mock_message.topic ="vestaboard/message"
        mock_message.payload = b"TEST"

        bridge._on_message(None, None, mock_message)

        mock_client.write_message.assert_called_once_with("TEST")


class TestSaveRestoreDelete:
    """Test save, restore, and delete operations."""

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_handle_save(self, mock_create_client):
        """Test handling save request."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        with patch.object(bridge.save_state_manager, 'save_current_state', return_value=True):
            bridge._handle_save("test_slot")
            bridge.save_state_manager.save_current_state.assert_called_once_with("test_slot")

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_handle_restore_request(self, mock_create_client):
        """Test handling restore request."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        with patch.object(bridge, '_restore_from_slot'):
            bridge._handle_restore_request("test_slot")
            bridge._restore_from_slot.assert_called_once_with("test_slot")

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_handle_delete(self, mock_create_client):
        """Test handling delete request."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        with patch.object(bridge.save_state_manager, 'delete_saved_state', return_value=True):
            bridge._handle_delete("test_slot")
            bridge.save_state_manager.delete_saved_state.assert_called_once_with("test_slot")

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_on_message_routes_save_topic(self, mock_create_client):
        """Test routing of save topic."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        mock_message = Mock()
        mock_message.topic ="vestaboard/save/slot1"
        mock_message.payload = b""

        with patch.object(bridge, '_handle_save'):
            bridge._on_message(None, None, mock_message)
            bridge._handle_save.assert_called_once_with("slot1")


class TestTimedMessages:
    """Test timed message functionality."""

    @patch('src.mqtt_bridge.create_vestaboard_client')
    @patch('src.mqtt_bridge.threading.Timer')
    def test_schedule_timed_message_basic(self, mock_timer, mock_create_client):
        """Test scheduling a basic timed message."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        with patch.object(bridge.save_state_manager, 'save_current_state', return_value=True):
            timer_id = bridge.schedule_timed_message("TEST", 30)

            assert timer_id.startswith("timer_")
            assert timer_id in bridge.active_timers
            mock_client.write_message.assert_called_once_with("TEST")
            mock_timer.assert_called_once()

    @patch('src.mqtt_bridge.create_vestaboard_client')
    @patch('src.mqtt_bridge.threading.Timer')
    def test_schedule_timed_message_with_restore_slot(self, mock_timer, mock_create_client):
        """Test scheduling timed message with custom restore slot."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        timer_id = bridge.schedule_timed_message("TEST", 30, restore_slot="custom_slot")

        # Should not call save_current_state when restore_slot is provided
        assert timer_id.startswith("timer_")
        mock_client.write_message.assert_called_once_with("TEST")

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_cancel_timed_message(self, mock_create_client):
        """Test cancelling a timed message."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        # Add a mock timer
        mock_timer = Mock()
        bridge.active_timers["timer_123"] = mock_timer

        success = bridge.cancel_timed_message("timer_123")

        assert success is True
        mock_timer.cancel.assert_called_once()
        assert "timer_123" not in bridge.active_timers

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_cancel_nonexistent_timer(self, mock_create_client):
        """Test cancelling a non-existent timer."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        success = bridge.cancel_timed_message("nonexistent")

        assert success is False

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_handle_timed_message(self, mock_create_client):
        """Test handling timed message via MQTT."""
        mock_client = Mock()
        mock_client.write_message.return_value = True
        mock_create_client.return_value = mock_client

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        payload = json.dumps({
            "message": "ALERT",
            "duration_seconds": 60
        })

        with patch.object(bridge, 'schedule_timed_message', return_value="timer_456"):
            bridge._handle_timed_message(payload)
            bridge.schedule_timed_message.assert_called_once_with("ALERT", 60, None)

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_handle_cancel_timer(self, mock_create_client):
        """Test handling cancel timer request."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        with patch.object(bridge, 'cancel_timed_message', return_value=True):
            bridge._handle_cancel_timer("timer_123")
            bridge.cancel_timed_message.assert_called_once_with("timer_123")

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_handle_list_timers(self, mock_create_client):
        """Test handling list timers request."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        # Add some mock timers
        mock_timer1 = Mock()
        mock_timer1.is_alive.return_value = True
        mock_timer2 = Mock()
        mock_timer2.is_alive.return_value = True

        bridge.active_timers = {
            "timer_1234567890": mock_timer1,
            "timer_1234567891": mock_timer2
        }

        bridge.mqtt_client.publish = Mock()
        bridge._handle_list_timers("")

        # Verify publish was called
        assert bridge.mqtt_client.publish.called
        call_args = bridge.mqtt_client.publish.call_args[0]
        response_data = json.loads(call_args[1])

        assert response_data["total_count"] == 2
        assert len(response_data["active_timers"]) == 2


class TestStopCleanup:
    """Test cleanup on stop."""

    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_stop_cancels_all_timers(self, mock_create_client):
        """Test that stop() cancels all active timers."""
        mock_create_client.return_value = Mock()

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        # Add mock timers
        mock_timer1 = Mock()
        mock_timer2 = Mock()
        bridge.active_timers = {
            "timer_1": mock_timer1,
            "timer_2": mock_timer2
        }

        bridge.stop()

        mock_timer1.cancel.assert_called_once()
        mock_timer2.cancel.assert_called_once()
        assert len(bridge.active_timers) == 0

    @patch('src.mqtt_bridge.mqtt.Client')
    @patch('src.mqtt_bridge.create_vestaboard_client')
    def test_stop_disconnects_mqtt(self, mock_create_client, mock_mqtt_client):
        """Test that stop() disconnects MQTT client."""
        mock_create_client.return_value = Mock()
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance

        mqtt_config = MQTTConfig(host="localhost", port= 1883)
        bridge = VestaboardMQTTBridge(vestaboard_api_key="test_key", mqtt_config=mqtt_config)

        bridge.stop()

        mock_client_instance.disconnect.assert_called_once()
        mock_client_instance.loop_stop.assert_called_once()
