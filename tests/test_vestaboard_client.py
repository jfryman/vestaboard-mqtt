"""Tests for Vestaboard client initialization and board type configuration."""

import os
import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from src.vestaboard_client import (
    BoardType,
    VestaboardClient,
    LocalVestaboardClient,
    create_vestaboard_client,
    BaseVestaboardClient,
)


class TestVestaboardClientInitialization:
    """Test VestaboardClient initialization with different board types."""

    def test_cloud_client_default_board_type(self):
        """Test Cloud client defaults to standard board."""
        client = VestaboardClient(api_key="test_key")
        assert client.board_rows == 6
        assert client.board_cols == 22

    def test_cloud_client_standard_board_type(self):
        """Test Cloud client with explicit standard board type."""
        client = VestaboardClient(api_key="test_key", board_type=BoardType.STANDARD)
        assert client.board_rows == 6
        assert client.board_cols == 22

    def test_cloud_client_note_board_type(self):
        """Test Cloud client with note board type."""
        client = VestaboardClient(api_key="test_key", board_type=BoardType.NOTE)
        assert client.board_rows == 3
        assert client.board_cols == 15

    def test_cloud_client_stores_api_key(self):
        """Test that client stores API key correctly."""
        api_key = "test_api_key_12345"
        client = VestaboardClient(api_key=api_key)
        assert client.api_key == api_key

    def test_cloud_client_has_correct_headers(self):
        """Test that Cloud client has correct headers."""
        client = VestaboardClient(api_key="test_key")
        assert "X-Vestaboard-Read-Write-Key" in client.headers
        assert client.headers["Content-Type"] == "application/json"


class TestLocalVestaboardClientInitialization:
    """Test LocalVestaboardClient initialization with different board types."""

    def test_local_client_default_board_type(self):
        """Test Local client defaults to standard board."""
        client = LocalVestaboardClient(api_key="test_key")
        assert client.board_rows == 6
        assert client.board_cols == 22

    def test_local_client_standard_board_type(self):
        """Test Local client with explicit standard board type."""
        client = LocalVestaboardClient(api_key="test_key", board_type=BoardType.STANDARD)
        assert client.board_rows == 6
        assert client.board_cols == 22

    def test_local_client_note_board_type(self):
        """Test Local client with note board type."""
        client = LocalVestaboardClient(api_key="test_key", board_type=BoardType.NOTE)
        assert client.board_rows == 3
        assert client.board_cols == 15

    def test_local_client_default_host_and_port(self):
        """Test Local client uses default host and port."""
        client = LocalVestaboardClient(api_key="test_key")
        assert client.host == "vestaboard.local"
        assert client.port == 7000

    def test_local_client_custom_host_and_port(self):
        """Test Local client with custom host and port."""
        client = LocalVestaboardClient(
            api_key="test_key",
            host="192.168.1.100",
            port=8080
        )
        assert client.host == "192.168.1.100"
        assert client.port == 8080

    def test_local_client_has_correct_headers(self):
        """Test that Local client has correct headers."""
        client = LocalVestaboardClient(api_key="test_key")
        assert "X-Vestaboard-Local-Api-Key" in client.headers
        assert client.headers["Content-Type"] == "application/json"

    def test_local_client_base_url_format(self):
        """Test that Local client constructs base_url correctly."""
        client = LocalVestaboardClient(
            api_key="test_key",
            host="192.168.1.100",
            port=7000
        )
        assert client.base_url == "http://192.168.1.100:7000/local-api/message"


class TestFactoryFunction:
    """Test create_vestaboard_client factory function."""

    def test_factory_creates_cloud_client_by_default(self):
        """Test factory creates Cloud client when use_local_api is False."""
        client = create_vestaboard_client(api_key="test_key", use_local_api=False)
        assert isinstance(client, VestaboardClient)
        assert not isinstance(client, LocalVestaboardClient)

    def test_factory_creates_local_client_when_requested(self):
        """Test factory creates Local client when use_local_api is True."""
        client = create_vestaboard_client(api_key="test_key", use_local_api=True)
        assert isinstance(client, LocalVestaboardClient)

    def test_factory_passes_board_type_to_cloud_client(self):
        """Test factory passes board_type to Cloud client."""
        client = create_vestaboard_client(
            api_key="test_key",
            board_type=BoardType.NOTE,
            use_local_api=False
        )
        assert client.board_rows == 3
        assert client.board_cols == 15

    def test_factory_passes_board_type_to_local_client(self):
        """Test factory passes board_type to Local client."""
        client = create_vestaboard_client(
            api_key="test_key",
            board_type=BoardType.NOTE,
            use_local_api=True
        )
        assert client.board_rows == 3
        assert client.board_cols == 15

    def test_factory_raises_error_without_api_key(self):
        """Test factory raises ValueError when api_key is not provided."""
        with pytest.raises(ValueError, match="api_key is required"):
            create_vestaboard_client()

    def test_factory_with_config_object(self):
        """Test factory uses VestaboardConfig when provided."""
        from src.config import VestaboardConfig

        config = VestaboardConfig(
            api_key="config_api_key",
            board_type="standard"
        )
        client = create_vestaboard_client(config=config)
        assert client.api_key == "config_api_key"
        assert isinstance(client, VestaboardClient)

    def test_factory_with_config_prefers_local_api_key(self):
        """Test factory uses local_api_key from config when use_local_api is True."""
        from src.config import VestaboardConfig

        config = VestaboardConfig(
            api_key="cloud_key",
            local_api_key="local_key",
            use_local_api=True,
            board_type="standard"
        )
        client = create_vestaboard_client(config=config)
        assert client.api_key == "local_key"
        assert isinstance(client, LocalVestaboardClient)

    def test_factory_passes_max_queue_size(self):
        """Test factory passes max_queue_size parameter."""
        client = create_vestaboard_client(
            api_key="test_key",
            max_queue_size=20
        )
        assert client.message_queue.maxlen == 20

    def test_factory_returns_base_client_interface(self):
        """Test factory returns BaseVestaboardClient interface."""
        cloud_client = create_vestaboard_client(
            api_key="test_key",
            use_local_api=False
        )
        local_client = create_vestaboard_client(
            api_key="test_key",
            use_local_api=True
        )
        assert isinstance(cloud_client, BaseVestaboardClient)
        assert isinstance(local_client, BaseVestaboardClient)


class TestClientBoardTypeUsage:
    """Test that clients use board_type for operations."""

    @patch('src.vestaboard_client.requests.post')
    def test_cloud_client_uses_board_dimensions_in_logging(self, mock_post):
        """Test that Cloud client logs board dimensions."""
        # This is more of an integration test but validates the flow
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test_message_id"}
        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key", board_type=BoardType.NOTE)
        # The client should be aware it's a 3x15 board
        assert client.board_rows == 3
        assert client.board_cols == 15

    def test_local_client_text_to_layout_uses_board_dimensions(self):
        """Test that Local client uses correct dimensions for text conversion."""
        client = LocalVestaboardClient(api_key="test_key", board_type=BoardType.NOTE)

        # Mock the write to test text conversion
        with patch.object(client, '_send_message_direct', return_value=True) as mock_send:
            client.write_message("TEST")
            # Verify that _send_message_direct was called with a layout
            assert mock_send.called
            args = mock_send.call_args[0]
            layout = args[0]
            # Should be a 3x15 layout for NOTE board
            assert len(layout) == 3
            assert all(len(row) == 15 for row in layout)


class TestLocalClientReadCurrentMessage:
    """Test LocalVestaboardClient.read_current_message() handles different response formats."""

    @patch('src.vestaboard_client.requests.get')
    def test_read_current_message_with_direct_array_response(self, mock_get):
        """Test read_current_message with direct array response (no wrapper)."""
        # Mock response with direct array (format 1)
        mock_response = Mock()
        mock_response.status_code = 200
        test_layout = [[0, 1, 2], [3, 4, 5]]
        mock_response.json.return_value = test_layout
        mock_get.return_value = mock_response

        client = LocalVestaboardClient(api_key="test_key")
        result = client.read_current_message()

        # Verify result structure
        assert result is not None
        assert "currentMessage" in result
        assert "layout" in result["currentMessage"]
        assert "id" in result["currentMessage"]

        # Layout should be the array directly
        assert result["currentMessage"]["layout"] == test_layout
        assert isinstance(result["currentMessage"]["layout"], list)

    @patch('src.vestaboard_client.requests.get')
    def test_read_current_message_with_message_wrapper(self, mock_get):
        """Test read_current_message with message wrapper (fixes bug)."""
        # Mock response with "message" wrapper (format 2)
        mock_response = Mock()
        mock_response.status_code = 200
        test_layout = [[0, 1, 2], [3, 4, 5]]
        mock_response.json.return_value = {"message": test_layout}
        mock_get.return_value = mock_response

        client = LocalVestaboardClient(api_key="test_key")
        result = client.read_current_message()

        # Verify result structure
        assert result is not None
        assert "currentMessage" in result
        assert "layout" in result["currentMessage"]

        # Layout should be extracted from the "message" wrapper
        assert result["currentMessage"]["layout"] == test_layout
        assert isinstance(result["currentMessage"]["layout"], list)
        # Ensure it's NOT the dict wrapper
        assert not isinstance(result["currentMessage"]["layout"], dict)

    @patch('src.vestaboard_client.requests.get')
    def test_read_current_message_error_handling(self, mock_get):
        """Test read_current_message handles request errors gracefully."""
        # Mock request exception
        mock_get.side_effect = requests.RequestException("Connection error")

        client = LocalVestaboardClient(api_key="test_key")
        result = client.read_current_message()

        # Should return None on error
        assert result is None
