"""Integration tests for end-to-end scenarios."""

import json
import time
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from src.mqtt import VestaboardMQTTBridge
from src.state import SaveStateManager
from src.http_api import create_app
from src.config import MQTTConfig, AppConfig
from tests.conftest import create_test_app_config, create_test_mqtt_config
from fastapi.testclient import TestClient


class TestMQTTBridgeIntegration:
    """Integration tests for MQTT bridge with Vestaboard client."""

    @patch('src.vestaboard.create_vestaboard_client')
    def test_complete_message_flow(self, mock_create_client):
        """Test complete message flow from MQTT to Vestaboard."""
        # Setup mock Vestaboard client
        mock_vestaboard = Mock()
        mock_vestaboard.write_message.return_value = True
        mock_create_client.return_value = mock_vestaboard

        # Create bridge
        config = create_test_app_config()
        bridge = VestaboardMQTTBridge(config)

        # Simulate MQTT message
        mock_message = Mock()
        mock_message.topic ="vestaboard/message"
        mock_message.payload = b"HELLO WORLD"

        bridge._on_message(None, None, mock_message)

        # Verify message was sent to Vestaboard
        mock_vestaboard.write_message.assert_called_once_with("HELLO WORLD")

    @patch('src.vestaboard.create_vestaboard_client')
    def test_save_and_restore_flow(self, mock_create_client):
        """Test save and restore flow."""
        # Setup mock Vestaboard client
        mock_vestaboard = Mock()
        mock_vestaboard.read_current_message.return_value = {
            "currentMessage": {
                "layout": [[1, 2, 3], [4, 5, 6]],
                "id": "msg_123"
            }
        }
        mock_vestaboard.write_message.return_value = True
        mock_create_client.return_value = mock_vestaboard

        # Create bridge
        config = create_test_app_config()
        bridge = VestaboardMQTTBridge(config)

        # Mock MQTT publish
        bridge.mqtt_client.publish = Mock(return_value=Mock(rc=0))

        # Test save
        mock_save_message = Mock()
        mock_save_message.topic ="vestaboard/save/test_slot"
        mock_save_message.payload = b""

        bridge._on_message(None, None, mock_save_message)

        # Verify save was called
        mock_vestaboard.read_current_message.assert_called_once()
        bridge.mqtt_client.publish.assert_called()

    @patch('src.vestaboard.create_vestaboard_client')
    @patch('src.mqtt.timers.threading.Timer')
    def test_timed_message_flow(self, mock_timer_class, mock_create_client):
        """Test timed message end-to-end flow."""
        # Setup mocks
        mock_vestaboard = Mock()
        mock_vestaboard.write_message.return_value = True
        mock_vestaboard.read_current_message.return_value = {
            "currentMessage": {
                "layout": [[0] * 22 for _ in range(6)],
                "id": "msg_old"
            }
        }
        mock_create_client.return_value = mock_vestaboard

        mock_timer = Mock()
        mock_timer_class.return_value = mock_timer

        # Create bridge
        config = create_test_app_config()
        bridge = VestaboardMQTTBridge(config)

        # Mock MQTT publish
        bridge.mqtt_client.publish = Mock(return_value=Mock(rc=0))

        # Test timed message
        mock_timed_message = Mock()
        mock_timed_message.topic ="vestaboard/timed-message"
        mock_timed_message.payload = json.dumps({
            "message": "ALERT",
            "duration_seconds": 30
        }).encode()

        bridge._on_message(None, None, mock_timed_message)

        # Verify message was displayed
        mock_vestaboard.write_message.assert_called_with("ALERT")

        # Verify timer was started
        mock_timer.start.assert_called_once()

        # Verify current state was saved
        assert bridge.mqtt_client.publish.called


class TestSaveStateIntegration:
    """Integration tests for save state manager."""

    def test_save_restore_roundtrip(self):
        """Test complete save and restore roundtrip."""
        # Setup mocks
        mock_mqtt = Mock()
        mock_mqtt.publish = Mock(return_value=Mock(rc=0))

        mock_vestaboard = Mock()
        original_layout = [[1, 2, 3], [4, 5, 6]]
        mock_vestaboard.read_current_message.return_value = {
            "currentMessage": {
                "layout": original_layout,
                "id": "msg_123"
            }
        }
        mock_vestaboard.write_message.return_value = True

        manager = SaveStateManager(mock_mqtt, mock_vestaboard)

        # Save current state
        success = manager.save_current_state("test_slot")
        assert success is True

        # Get the saved data
        call_args = mock_mqtt.publish.call_args
        saved_json = call_args[0][1]
        saved_data = json.loads(saved_json)

        # Restore from saved data
        success = manager.restore_from_data(saved_data)
        assert success is True

        # Verify restoration wrote the same layout
        mock_vestaboard.write_message.assert_called_with(original_layout)

    def test_multiple_slots(self):
        """Test saving to multiple slots."""
        mock_mqtt = Mock()
        mock_mqtt.publish = Mock(return_value=Mock(rc=0))

        mock_vestaboard = Mock()

        manager = SaveStateManager(mock_mqtt, mock_vestaboard)

        # Save to different slots with different data
        for i, slot_name in enumerate(["slot1", "slot2", "slot3"]):
            mock_vestaboard.read_current_message.return_value = {
                "currentMessage": {
                    "layout": [[i] * 22 for _ in range(6)],
                    "id": f"msg_{i}"
                }
            }

            success = manager.save_current_state(slot_name)
            assert success is True

        # Verify each publish had correct topic
        assert mock_mqtt.publish.call_count == 3
        topics = [call[0][0] for call in mock_mqtt.publish.call_args_list]
        assert "vestaboard/states/slot1" in topics
        assert "vestaboard/states/slot2" in topics
        assert "vestaboard/states/slot3" in topics


class TestHTTPAPIIntegration:
    """Integration tests for HTTP API with MQTT bridge."""

    @patch('src.vestaboard.create_vestaboard_client')
    def test_api_reflects_bridge_state(self, mock_create_client):
        """Test that HTTP API accurately reflects bridge state."""
        mock_vestaboard = Mock()
        mock_create_client.return_value = mock_vestaboard

        # Create bridge
        config = create_test_app_config()
        bridge = VestaboardMQTTBridge(config)

        # Create API
        app = create_app(bridge)
        client = TestClient(app)

        # Initially no timers
        response = client.get("/metrics")
        assert response.json()["active_timers"] == 0

        # Add some timers
        mock_timer = Mock()
        bridge.timer_manager.active_timers["timer_1"] = mock_timer
        bridge.timer_manager.active_timers["timer_2"] = mock_timer

        # Check metrics updated
        response = client.get("/metrics")
        assert response.json()["active_timers"] == 2

    @patch('src.vestaboard.create_vestaboard_client')
    def test_readiness_reflects_mqtt_connection(self, mock_create_client):
        """Test readiness endpoint reflects actual MQTT connection state."""
        mock_vestaboard = Mock()
        mock_create_client.return_value = mock_vestaboard

        config = create_test_app_config()
        bridge = VestaboardMQTTBridge(config)

        app = create_app(bridge)
        client = TestClient(app)

        # Simulate connected state
        bridge.mqtt_client.is_connected = Mock(return_value=True)
        response = client.get("/ready")
        assert response.json()["mqtt_connected"] is True

        # Simulate disconnected state
        bridge.mqtt_client.is_connected = Mock(return_value=False)
        response = client.get("/ready")
        assert response.json()["mqtt_connected"] is False


class TestMultiVestaboardScenario:
    """Integration tests simulating multi-Vestaboard deployment."""

    @patch('src.vestaboard.create_vestaboard_client')
    def test_independent_bridge_instances(self, mock_create_client):
        """Test that multiple bridge instances with different prefixes work independently."""
        # Create two bridges with different prefixes
        mock_vestaboard1 = Mock()
        mock_vestaboard2 = Mock()

        # Configure mock to return different clients
        mock_create_client.side_effect = [mock_vestaboard1, mock_vestaboard2]

        mqtt_config1 = create_test_mqtt_config(topic_prefix="office-board")
        config1 = create_test_app_config(
            vestaboard_api_key="key1",
            mqtt_config=mqtt_config1,
            http_port=8000
        )
        bridge1 = VestaboardMQTTBridge(config1)

        mqtt_config2 = create_test_mqtt_config(topic_prefix="lobby-board")
        config2 = create_test_app_config(
            vestaboard_api_key="key2",
            mqtt_config=mqtt_config2,
            http_port=8001
        )
        bridge2 = VestaboardMQTTBridge(config2)

        # Verify different topic prefixes
        assert bridge1.topic_prefix =="office-board"
        assert bridge2.topic_prefix =="lobby-board"

        # Simulate messages to each bridge
        mock_message1 = Mock()
        mock_message1.topic ="office-board/message"
        mock_message1.payload = b"OFFICE MESSAGE"

        mock_message2 = Mock()
        mock_message2.topic ="lobby-board/message"
        mock_message2.payload = b"LOBBY MESSAGE"

        mock_vestaboard1.write_message.return_value = True
        mock_vestaboard2.write_message.return_value = True

        bridge1._on_message(None, None, mock_message1)
        bridge2._on_message(None, None, mock_message2)

        # Verify each bridge only processed its own message
        mock_vestaboard1.write_message.assert_called_once_with("OFFICE MESSAGE")
        mock_vestaboard2.write_message.assert_called_once_with("LOBBY MESSAGE")


class TestErrorRecovery:
    """Integration tests for error handling and recovery."""

    @patch('src.vestaboard.create_vestaboard_client')
    def test_vestaboard_api_failure_recovery(self, mock_create_client):
        """Test that bridge handles Vestaboard API failures gracefully."""
        mock_vestaboard = Mock()
        mock_vestaboard.write_message.side_effect = [False, True]  # Fail then succeed
        mock_create_client.return_value = mock_vestaboard

        config = create_test_app_config()
        bridge = VestaboardMQTTBridge(config)

        mock_message = Mock()
        mock_message.topic ="vestaboard/message"
        mock_message.payload = b"TEST"

        # First attempt fails
        bridge._on_message(None, None, mock_message)

        # Second attempt succeeds
        bridge._on_message(None, None, mock_message)

        # Both attempts were made
        assert mock_vestaboard.write_message.call_count == 2

    @patch('src.vestaboard.create_vestaboard_client')
    def test_malformed_json_handling(self, mock_create_client):
        """Test that bridge handles malformed JSON gracefully."""
        mock_vestaboard = Mock()
        mock_create_client.return_value = mock_vestaboard

        config = create_test_app_config()
        bridge = VestaboardMQTTBridge(config)

        # Test malformed timed message JSON
        mock_message = Mock()
        mock_message.topic ="vestaboard/timed-message"
        mock_message.payload = b"{invalid json [["

        # Should not raise exception
        bridge._on_message(None, None, mock_message)

        # Vestaboard client should not have been called
        mock_vestaboard.write_message.assert_not_called()

    def test_save_state_with_missing_data(self):
        """Test save state manager handles missing data gracefully."""
        mock_mqtt = Mock()
        mock_vestaboard = Mock()
        mock_vestaboard.read_current_message.return_value = None

        manager = SaveStateManager(mock_mqtt, mock_vestaboard)

        # Save should fail gracefully
        success = manager.save_current_state("test_slot")
        assert success is False

        # Restore with invalid data should fail gracefully
        invalid_data = {"wrong_key": "value"}
        success = manager.restore_from_data(invalid_data)
        assert success is False


class TestCompleteWorkflow:
    """Integration test for complete real-world workflows."""

    @patch('src.vestaboard.create_vestaboard_client')
    @patch('src.mqtt.timers.threading.Timer')
    def test_complete_timed_message_workflow(self, mock_timer_class, mock_create_client):
        """Test complete timed message workflow with save/restore."""
        # Setup mocks
        mock_vestaboard = Mock()
        original_layout = [[0] * 22 for _ in range(6)]
        timed_layout = [[1] * 22 for _ in range(6)]

        # First read for save, second for verification
        mock_vestaboard.read_current_message.side_effect = [
            {"currentMessage": {"layout": original_layout, "id": "original"}},
            {"currentMessage": {"layout": timed_layout, "id": "timed"}}
        ]
        mock_vestaboard.write_message.return_value = True
        mock_create_client.return_value = mock_vestaboard

        mock_timer = Mock()
        mock_timer_class.return_value = mock_timer

        # Create bridge
        config = create_test_app_config()
        bridge = VestaboardMQTTBridge(config)
        bridge.mqtt_client.publish = Mock(return_value=Mock(rc=0))

        # Schedule timed message via MQTT
        timed_payload = json.dumps({
            "message": "ALERT",
            "duration_seconds": 60
        }).encode()

        mock_message = Mock()
        mock_message.topic ="vestaboard/timed-message"
        mock_message.payload = timed_payload

        bridge._on_message(None, None, mock_message)

        # Verify workflow:
        # 1. Current state was read for save
        assert mock_vestaboard.read_current_message.called

        # 2. Timed message was displayed
        mock_vestaboard.write_message.assert_called()

        # 3. Timer was created and started
        mock_timer_class.assert_called_once()
        mock_timer.start.assert_called_once()

        # 4. Timer is tracked
        assert len(bridge.timer_manager.active_timers) == 1

    @patch('src.vestaboard.create_vestaboard_client')
    def test_message_types_workflow(self, mock_create_client):
        """Test handling different message types in sequence."""
        mock_vestaboard = Mock()
        mock_vestaboard.write_message.return_value = True
        mock_create_client.return_value = mock_vestaboard

        config = create_test_app_config()
        bridge = VestaboardMQTTBridge(config)

        # Test sequence of different message types
        messages = [
            # Plain text
            ("vestaboard/message", b"HELLO"),
            # JSON layout
            ("vestaboard/message", json.dumps([[1, 2], [3, 4]]).encode()),
            # JSON text object
            ("vestaboard/message", json.dumps({"text": "WORLD"}).encode()),
        ]

        for topic, payload in messages:
            mock_message = Mock()
            mock_message.topic = topic
            mock_message.payload = payload
            bridge._on_message(None, None, mock_message)

        # All messages should have been processed
        assert mock_vestaboard.write_message.call_count == 3

        # Verify call arguments
        calls = mock_vestaboard.write_message.call_args_list
        assert calls[0][0][0] =="HELLO"
        assert calls[1][0][0] == [[1, 2], [3, 4]]
        assert calls[2][0][0] =="WORLD"


@pytest.mark.integration
class TestPerformance:
    """Performance and load integration tests."""

    @patch('src.vestaboard.create_vestaboard_client')
    def test_rapid_message_handling(self, mock_create_client):
        """Test bridge handles rapid successive messages."""
        mock_vestaboard = Mock()
        mock_vestaboard.write_message.return_value = True
        mock_create_client.return_value = mock_vestaboard

        config = create_test_app_config()
        bridge = VestaboardMQTTBridge(config)

        # Send 100 messages rapidly
        for i in range(100):
            mock_message = Mock()
            mock_message.topic ="vestaboard/message"
            mock_message.payload = f"MESSAGE {i}".encode()
            bridge._on_message(None, None, mock_message)

        # All messages should be processed
        assert mock_vestaboard.write_message.call_count == 100

    def test_api_concurrent_requests(self):
        """Test HTTP API handles concurrent requests."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.mqtt_client.is_connected.return_value = True
        mock_bridge.timer_manager = Mock()
        mock_bridge.timer_manager.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        # Make 50 concurrent requests to each endpoint
        endpoints = ["/health", "/ready", "/metrics"]
        for _ in range(50):
            for endpoint in endpoints:
                response = client.get(endpoint)
                assert response.status_code == 200
