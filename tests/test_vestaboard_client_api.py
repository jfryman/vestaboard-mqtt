"""Tests for Vestaboard client API interactions."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.vestaboard import (
    VestaboardClient,
    LocalVestaboardClient,
    BoardType,
    text_to_layout,
    debug_layout_preview
)


class TestAPIErrorHandling:
    """Test API error handling scenarios."""

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_write_message_429_rate_limit(self, mock_post):
        """Test handling of 429 rate limit response."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key")
        result = client.write_message("Test")

        assert result is False

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_write_message_network_error(self, mock_post):
        """Test handling of network errors."""
        import requests
        mock_post.side_effect = requests.RequestException("Network error")

        client = VestaboardClient(api_key="test_key")
        result = client.write_message("Test")

        assert result is False

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_write_message_http_error_with_json(self, mock_post):
        """Test handling of HTTP errors with JSON error details."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid message"}
        mock_response.raise_for_status.side_effect = requests.HTTPError()

        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key")
        result = client.write_message("Test")

        assert result is False

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_write_message_http_error_without_json(self, mock_post):
        """Test handling of HTTP errors without JSON response."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("Not JSON")

        error = requests.HTTPError()
        error.response = mock_response
        mock_response.raise_for_status.side_effect = error

        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key")
        result = client.write_message("Test")

        assert result is False

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_write_layout_array(self, mock_post):
        """Test writing layout array instead of text."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}
        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key")
        layout = [[0] * 22 for _ in range(6)]
        result = client.write_message(layout)

        assert result is True
        # Verify payload format
        call_args = mock_post.call_args
        assert 'json' in call_args.kwargs


class TestReadCurrentMessage:
    """Test reading current message from Vestaboard."""

    @patch('src.vestaboard.cloud_client.requests.get')
    def test_read_current_message_success(self, mock_get):
        """Test successfully reading current message."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "currentMessage": {
                "id": "msg_123",
                "layout": [[0] * 22 for _ in range(6)]
            }
        }
        mock_get.return_value = mock_response

        client = VestaboardClient(api_key="test_key")
        result = client.read_current_message()

        assert result is not None
        assert "currentMessage" in result
        assert result["currentMessage"]["id"] == "msg_123"

    @patch('src.vestaboard.cloud_client.requests.get')
    def test_read_current_message_error(self, mock_get):
        """Test error handling when reading current message."""
        import requests
        mock_get.side_effect = requests.RequestException("Network error")

        client = VestaboardClient(api_key="test_key")
        result = client.read_current_message()

        assert result is None


class TestLocalAPIClient:
    """Test Local API client specific functionality."""

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_local_api_write_text(self, mock_post):
        """Test Local API writing text message."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = LocalVestaboardClient(api_key="test_key")
        result = client.write_message("Hello")

        assert result is True
        # Verify Local API endpoint was used
        call_args = mock_post.call_args
        assert 'vestaboard.local' in call_args.args[0] or 'vestaboard.local' in str(call_args)

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_local_api_write_layout(self, mock_post):
        """Test Local API writing layout array."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = LocalVestaboardClient(api_key="test_key")
        layout = [[0] * 22 for _ in range(6)]
        result = client.write_message(layout)

        assert result is True

    @patch('src.vestaboard.cloud_client.requests.get')
    def test_local_api_read_message(self, mock_get):
        """Test Local API reading current message."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [[0] * 22 for _ in range(6)]
        mock_get.return_value = mock_response

        client = LocalVestaboardClient(api_key="test_key")
        result = client.read_current_message()

        assert result is not None
        assert "currentMessage" in result
        assert "layout" in result["currentMessage"]
        layout = result["currentMessage"]["layout"]
        assert len(layout) == 6
        assert len(layout[0]) == 22

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_local_api_429_error(self, mock_post):
        """Test Local API handling 429 rate limit."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        client = LocalVestaboardClient(api_key="test_key")
        result = client.write_message("Test")

        assert result is False

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_local_api_network_error(self, mock_post):
        """Test Local API handling network errors."""
        import requests
        mock_post.side_effect = requests.RequestException("Connection refused")

        client = LocalVestaboardClient(api_key="test_key")
        result = client.write_message("Test")

        assert result is False


class TestTextToLayout:
    """Test text_to_layout utility function."""

    def test_text_to_layout_basic(self):
        """Test basic text conversion to layout."""
        result = text_to_layout("AB", BoardType.NOTE)  # 3x15
        # Should be centered on first row of NOTE board (3x15)
        assert len(result) == 3
        assert len(result[0]) == 15
        # 'A'=1, 'B'=2, centered in 15 cols
        assert 1 in result[0]
        assert 2 in result[0]

    def test_text_to_layout_centering(self):
        """Test text is centered on first row."""
        # Short text on NOTE board should be centered
        result = text_to_layout("ABC", BoardType.NOTE)  # 3x15
        # 'A'=1, 'B'=2, 'C'=3
        assert len(result) == 3
        assert len(result[0]) == 15
        first_row = result[0]
        # Text should be centered
        assert 1 in first_row
        assert 2 in first_row
        assert 3 in first_row
        # Second and third rows should be empty
        assert all(code == 0 for code in result[1])
        assert all(code == 0 for code in result[2])

    def test_text_to_layout_padding(self):
        """Test text is padded to fill board."""
        result = text_to_layout("A", BoardType.NOTE)  # 3x15
        assert len(result) == 3
        assert len(result[0]) == 15
        # First row should have 'A' (code 1) somewhere
        assert 1 in result[0]

    def test_text_to_layout_truncation(self):
        """Test text is truncated if too long."""
        # Text longer than NOTE board width (15) should be truncated
        long_text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # 26 chars, but NOTE is 15 wide
        result = text_to_layout(long_text, BoardType.NOTE)
        assert len(result) == 3
        assert len(result[0]) == 15
        # Should have at most 15 non-zero codes in first row
        non_zero_count = sum(1 for code in result[0] if code != 0)
        assert non_zero_count <= 15

    def test_text_to_layout_special_chars(self):
        """Test special characters are converted."""
        result = text_to_layout("1!", BoardType.NOTE)
        # '1' = code 27, '!' = code 37
        assert len(result) == 3
        assert len(result[0]) == 15
        assert 27 in result[0]
        assert 37 in result[0]

    def test_text_to_layout_unknown_char(self):
        """Test unknown characters are converted to spaces."""
        result = text_to_layout("~", BoardType.NOTE)
        # Unknown chars become spaces (code 0)
        assert len(result) == 3
        assert len(result[0]) == 15
        # All codes should be 0 (no mapping for ~)
        assert all(code == 0 for code in result[0])

    def test_text_to_layout_lowercase(self):
        """Test lowercase letters are converted to uppercase."""
        result = text_to_layout("abc", BoardType.NOTE)
        # 'A'=1, 'B'=2, 'C'=3
        assert len(result) == 3
        assert len(result[0]) == 15
        assert 1 in result[0]
        assert 2 in result[0]
        assert 3 in result[0]


class TestDebugLayoutPreview:
    """Test debug_layout_preview utility function."""

    def test_debug_layout_preview(self):
        """Test layout preview logging."""
        import logging
        logger = logging.getLogger("test")

        layout = [[1, 2, 3], [4, 5, 6]]
        # Should not raise exception
        debug_layout_preview(layout, logger)

    def test_debug_layout_preview_empty(self):
        """Test preview with empty layout."""
        import logging
        logger = logging.getLogger("test")

        layout = [[]]
        debug_layout_preview(layout, logger)


class TestClientCleanup:
    """Test client cleanup functionality."""

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_cleanup_cancels_timer(self, mock_post):
        """Test cleanup cancels active queue timer."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_1"}
        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key")
        client.RATE_LIMIT_SECONDS = 10  # Long delay

        # Send two messages to start queue processing
        client.write_message("MESSAGE 1")
        client.write_message("MESSAGE 2")

        # Cleanup should cancel timer
        client.cleanup()

        # Queue should be empty after cleanup
        assert len(client.message_queue) == 0

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_destructor_calls_cleanup(self, mock_post):
        """Test that __del__ calls cleanup."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_1"}
        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key")
        client.write_message("MESSAGE")

        # Manually call destructor
        client.__del__()

        # Should not raise exception
        assert True
