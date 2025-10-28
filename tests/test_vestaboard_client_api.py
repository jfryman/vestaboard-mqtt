"""Tests for Vestaboard client API interactions."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.vestaboard_client import (
    VestaboardClient,
    LocalVestaboardClient,
    text_to_layout,
    debug_layout_preview
)


class TestAPIErrorHandling:
    """Test API error handling scenarios."""

    @patch('src.vestaboard_client.requests.post')
    def test_write_message_429_rate_limit(self, mock_post):
        """Test handling of 429 rate limit response."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key")
        result = client.write_message("Test")

        assert result is False

    @patch('src.vestaboard_client.requests.post')
    def test_write_message_network_error(self, mock_post):
        """Test handling of network errors."""
        import requests
        mock_post.side_effect = requests.RequestException("Network error")

        client = VestaboardClient(api_key="test_key")
        result = client.write_message("Test")

        assert result is False

    @patch('src.vestaboard_client.requests.post')
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

    @patch('src.vestaboard_client.requests.post')
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

    @patch('src.vestaboard_client.requests.post')
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

    @patch('src.vestaboard_client.requests.get')
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

    @patch('src.vestaboard_client.requests.get')
    def test_read_current_message_error(self, mock_get):
        """Test error handling when reading current message."""
        import requests
        mock_get.side_effect = requests.RequestException("Network error")

        client = VestaboardClient(api_key="test_key")
        result = client.read_current_message()

        assert result is None


class TestLocalAPIClient:
    """Test Local API client specific functionality."""

    @patch('src.vestaboard_client.requests.post')
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

    @patch('src.vestaboard_client.requests.post')
    def test_local_api_write_layout(self, mock_post):
        """Test Local API writing layout array."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = LocalVestaboardClient(api_key="test_key")
        layout = [[0] * 22 for _ in range(6)]
        result = client.write_message(layout)

        assert result is True

    @patch('src.vestaboard_client.requests.get')
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

    @patch('src.vestaboard_client.requests.post')
    def test_local_api_429_error(self, mock_post):
        """Test Local API handling 429 rate limit."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        client = LocalVestaboardClient(api_key="test_key")
        result = client.write_message("Test")

        assert result is False

    @patch('src.vestaboard_client.requests.post')
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
        result = text_to_layout("AB", rows=1, cols=2)
        assert result == [[1, 2]]

    def test_text_to_layout_centering(self):
        """Test text is centered on first row."""
        # 3-char text in 5-col board should start at col 1 (center)
        result = text_to_layout("ABC", rows=2, cols=5)
        # 'A'=1, 'B'=2, 'C'=3
        assert result[0] == [0, 1, 2, 3, 0]  # Centered
        assert result[1] == [0, 0, 0, 0, 0]  # Empty second row

    def test_text_to_layout_padding(self):
        """Test text is padded to fill board."""
        result = text_to_layout("A", rows=2, cols=2)
        assert result == [[1, 0], [0, 0]]

    def test_text_to_layout_truncation(self):
        """Test text is truncated if too long."""
        result = text_to_layout("ABCD", rows=1, cols=2)
        assert result == [[1, 2]]

    def test_text_to_layout_special_chars(self):
        """Test special characters are converted."""
        result = text_to_layout("1!", rows=1, cols=2)
        # '1' = code 27, '!' = code 37
        assert result == [[27, 37]]

    def test_text_to_layout_unknown_char(self):
        """Test unknown characters are converted to spaces."""
        result = text_to_layout("~", rows=1, cols=1)
        # Unknown chars become spaces (code 0)
        assert result == [[0]]

    def test_text_to_layout_lowercase(self):
        """Test lowercase letters are converted to uppercase."""
        result = text_to_layout("abc", rows=1, cols=3)
        # 'A'=1, 'B'=2, 'C'=3
        assert result == [[1, 2, 3]]


class TestDebugLayoutPreview:
    """Test debug_layout_preview utility function."""

    def test_debug_layout_preview(self):
        """Test layout preview logging."""
        from src.logger import setup_logger
        logger = setup_logger("test")

        layout = [[1, 2, 3], [4, 5, 6]]
        # Should not raise exception
        debug_layout_preview(layout, logger)

    def test_debug_layout_preview_empty(self):
        """Test preview with empty layout."""
        from src.logger import setup_logger
        logger = setup_logger("test")

        layout = [[]]
        debug_layout_preview(layout, logger)


class TestClientCleanup:
    """Test client cleanup functionality."""

    @patch('src.vestaboard_client.requests.post')
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

    @patch('src.vestaboard_client.requests.post')
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
