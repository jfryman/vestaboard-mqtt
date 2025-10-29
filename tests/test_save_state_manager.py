"""Comprehensive tests for SaveStateManager."""

import json
import time
import pytest
from unittest.mock import Mock, MagicMock, patch
import paho.mqtt.client as mqtt
from src.state import SaveStateManager


class TestSaveStateManagerInitialization:
    """Test SaveStateManager initialization."""

    def test_initialization_default_prefix(self):
        """Test manager initializes with default topic prefix."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        assert manager.mqtt_client == mock_mqtt_client
        assert manager.vestaboard_client == mock_vestaboard_client
        assert manager.save_topic_prefix == "vestaboard/states/"

    def test_initialization_custom_prefix(self):
        """Test manager initializes with custom topic prefix."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client, topic_prefix="office-board")

        assert manager.save_topic_prefix == "office-board/states/"

    def test_initialization_strips_trailing_slash(self):
        """Test that topic prefix strips trailing slashes."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client, topic_prefix="vestaboard/")

        assert manager.save_topic_prefix == "vestaboard/states/"


class TestSaveCurrentState:
    """Test save_current_state functionality."""

    def test_save_current_state_success(self):
        """Test successful state save."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        # Mock the current message
        current_message = {
            "currentMessage": {
                "layout": [[1, 2, 3], [4, 5, 6]],
                "id": "msg_123"
            }
        }
        mock_vestaboard_client.read_current_message.return_value = current_message

        # Mock MQTT publish success
        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        mock_mqtt_client.publish.return_value = mock_result

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        success = manager.save_current_state("test_slot")

        assert success is True
        mock_vestaboard_client.read_current_message.assert_called_once()
        mock_mqtt_client.publish.assert_called_once()

        # Check publish arguments
        call_args = mock_mqtt_client.publish.call_args
        assert call_args[0][0] == "vestaboard/states/test_slot"
        assert call_args[1]['qos'] == 1
        assert call_args[1]['retain'] is True

        # Verify payload structure
        payload = json.loads(call_args[0][1])
        assert payload["layout"] == [[1, 2, 3], [4, 5, 6]]
        assert payload["original_id"] == "msg_123"
        assert "saved_at" in payload
        assert isinstance(payload["saved_at"], int)

    def test_save_current_state_read_failure(self):
        """Test save fails when reading current message fails."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()
        mock_vestaboard_client.read_current_message.return_value = None

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        success = manager.save_current_state("test_slot")

        assert success is False
        mock_mqtt_client.publish.assert_not_called()

    def test_save_current_state_publish_failure(self):
        """Test save fails when MQTT publish fails."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        current_message = {
            "currentMessage": {
                "layout": [[1, 2, 3]],
                "id": "msg_123"
            }
        }
        mock_vestaboard_client.read_current_message.return_value = current_message

        # Mock MQTT publish failure
        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_NO_CONN
        mock_mqtt_client.publish.return_value = mock_result

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        success = manager.save_current_state("test_slot")

        assert success is False

    def test_save_current_state_exception_handling(self):
        """Test save handles exceptions gracefully."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()
        mock_vestaboard_client.read_current_message.side_effect = Exception("API error")

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        success = manager.save_current_state("test_slot")

        assert success is False

    def test_save_current_state_with_custom_prefix(self):
        """Test save uses custom topic prefix."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        current_message = {
            "currentMessage": {
                "layout": [[1, 2, 3]],
                "id": "msg_123"
            }
        }
        mock_vestaboard_client.read_current_message.return_value = current_message

        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        mock_mqtt_client.publish.return_value = mock_result

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client, topic_prefix="office-board")

        success = manager.save_current_state("test_slot")

        assert success is True
        call_args = mock_mqtt_client.publish.call_args
        assert call_args[0][0] == "office-board/states/test_slot"


class TestRestoreFromData:
    """Test restore_from_data functionality."""

    def test_restore_from_data_success(self):
        """Test successful restore from save data."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()
        mock_vestaboard_client.write_message.return_value = True

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        save_data = {
            "layout": [[1, 2, 3], [4, 5, 6]],
            "saved_at": int(time.time()),
            "original_id": "msg_123"
        }

        success = manager.restore_from_data(save_data)

        assert success is True
        mock_vestaboard_client.write_message.assert_called_once_with([[1, 2, 3], [4, 5, 6]])

    def test_restore_from_data_missing_layout(self):
        """Test restore fails when layout is missing."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        save_data = {
            "saved_at": int(time.time()),
            "original_id": "msg_123"
        }

        success = manager.restore_from_data(save_data)

        assert success is False
        mock_vestaboard_client.write_message.assert_not_called()

    def test_restore_from_data_layout_is_string(self):
        """Test restore handles layout as JSON string."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()
        mock_vestaboard_client.write_message.return_value = True

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        save_data = {
            "layout": '[[1, 2, 3], [4, 5, 6]]',
            "saved_at": int(time.time())
        }

        success = manager.restore_from_data(save_data)

        assert success is True
        mock_vestaboard_client.write_message.assert_called_once_with([[1, 2, 3], [4, 5, 6]])

    def test_restore_from_data_layout_with_message_wrapper(self):
        """Test restore handles Local API format with message wrapper."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()
        mock_vestaboard_client.write_message.return_value = True

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        save_data = {
            "layout": {"message": [[1, 2, 3], [4, 5, 6]]},
            "saved_at": int(time.time())
        }

        success = manager.restore_from_data(save_data)

        assert success is True
        mock_vestaboard_client.write_message.assert_called_once_with([[1, 2, 3], [4, 5, 6]])

    def test_restore_from_data_invalid_layout_type(self):
        """Test restore fails with invalid layout type."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        save_data = {
            "layout": 12345,  # Invalid type
            "saved_at": int(time.time())
        }

        success = manager.restore_from_data(save_data)

        assert success is False
        mock_vestaboard_client.write_message.assert_not_called()

    def test_restore_from_data_write_failure(self):
        """Test restore fails when write_message fails."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()
        mock_vestaboard_client.write_message.return_value = False

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        save_data = {
            "layout": [[1, 2, 3]],
            "saved_at": int(time.time())
        }

        success = manager.restore_from_data(save_data)

        assert success is False

    def test_restore_from_data_exception_handling(self):
        """Test restore handles exceptions gracefully."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()
        mock_vestaboard_client.write_message.side_effect = Exception("Write error")

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        save_data = {
            "layout": [[1, 2, 3]],
            "saved_at": int(time.time())
        }

        success = manager.restore_from_data(save_data)

        assert success is False

    def test_restore_from_data_invalid_json_string(self):
        """Test restore handles invalid JSON string layout."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        save_data = {
            "layout": "invalid json [[[",
            "saved_at": int(time.time())
        }

        success = manager.restore_from_data(save_data)

        assert success is False


class TestDeleteSavedState:
    """Test delete_saved_state functionality."""

    def test_delete_saved_state_success(self):
        """Test successful state deletion."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        mock_mqtt_client.publish.return_value = mock_result

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        success = manager.delete_saved_state("test_slot")

        assert success is True
        mock_mqtt_client.publish.assert_called_once()

        # Verify delete publishes empty retained message
        call_args = mock_mqtt_client.publish.call_args
        assert call_args[0][0] == "vestaboard/states/test_slot"
        assert call_args[0][1] is None  # Empty payload
        assert call_args[1]['qos'] == 1
        assert call_args[1]['retain'] is True

    def test_delete_saved_state_publish_failure(self):
        """Test delete fails when MQTT publish fails."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_NO_CONN
        mock_mqtt_client.publish.return_value = mock_result

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        success = manager.delete_saved_state("test_slot")

        assert success is False

    def test_delete_saved_state_exception_handling(self):
        """Test delete handles exceptions gracefully."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()
        mock_mqtt_client.publish.side_effect = Exception("Connection error")

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        success = manager.delete_saved_state("test_slot")

        assert success is False

    def test_delete_saved_state_with_custom_prefix(self):
        """Test delete uses custom topic prefix."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        mock_mqtt_client.publish.return_value = mock_result

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client, topic_prefix="office-board")

        success = manager.delete_saved_state("test_slot")

        assert success is True
        call_args = mock_mqtt_client.publish.call_args
        assert call_args[0][0] == "office-board/states/test_slot"


class TestRestoreState:
    """Test restore_state method (MQTT bridge integration)."""

    def test_restore_state_returns_true(self):
        """Test restore_state returns True (handled by bridge)."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        # This method delegates to MQTT bridge
        success = manager.restore_state("test_slot")

        assert success is True


@pytest.mark.parametrize("layout_data,expected_layout", [
    # Normal list layout
    ([[1, 2, 3], [4, 5, 6]], [[1, 2, 3], [4, 5, 6]]),
    # JSON string layout
    ('[[1, 2], [3, 4]]', [[1, 2], [3, 4]]),
    # Message wrapper format
    ({"message": [[1, 2, 3]]}, [[1, 2, 3]]),
])
def test_restore_from_data_parametrized(layout_data, expected_layout):
    """Parametrized test for various layout formats."""
    mock_mqtt_client = Mock()
    mock_vestaboard_client = Mock()
    mock_vestaboard_client.write_message.return_value = True

    manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

    save_data = {
        "layout": layout_data,
        "saved_at": int(time.time())
    }

    success = manager.restore_from_data(save_data)

    assert success is True
    mock_vestaboard_client.write_message.assert_called_once_with(expected_layout)


class TestSaveDataFormat:
    """Test save data JSON format and structure."""

    def test_save_data_contains_required_fields(self):
        """Test that saved data contains all required fields."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        current_message = {
            "currentMessage": {
                "layout": [[1, 2, 3]],
                "id": "msg_123"
            }
        }
        mock_vestaboard_client.read_current_message.return_value = current_message

        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        mock_mqtt_client.publish.return_value = mock_result

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)

        before_time = int(time.time())
        manager.save_current_state("test_slot")
        after_time = int(time.time())

        call_args = mock_mqtt_client.publish.call_args
        payload = json.loads(call_args[0][1])

        # Check all required fields
        assert "layout" in payload
        assert "saved_at" in payload
        assert "original_id" in payload

        # Check values
        assert payload["layout"] == [[1, 2, 3]]
        assert payload["original_id"] == "msg_123"
        assert before_time <= payload["saved_at"] <= after_time

    def test_save_data_is_valid_json(self):
        """Test that saved data is valid JSON."""
        mock_mqtt_client = Mock()
        mock_vestaboard_client = Mock()

        current_message = {
            "currentMessage": {
                "layout": [[1, 2, 3]],
                "id": "msg_123"
            }
        }
        mock_vestaboard_client.read_current_message.return_value = current_message

        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        mock_mqtt_client.publish.return_value = mock_result

        manager = SaveStateManager(mock_mqtt_client, mock_vestaboard_client)
        manager.save_current_state("test_slot")

        call_args = mock_mqtt_client.publish.call_args
        payload_str = call_args[0][1]

        # Should not raise exception
        payload = json.loads(payload_str)
        assert isinstance(payload, dict)
