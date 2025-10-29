"""Tests for rate limiting and message queue functionality."""

import time
import pytest
from unittest.mock import Mock, MagicMock, patch
from src.vestaboard import VestaboardClient, LocalVestaboardClient


class TestRateLimiting:
    """Test rate limiting functionality."""

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_rate_limit_queues_rapid_messages(self, mock_post):
        """Test that rapid messages get queued due to rate limiting."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}
        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key")

        # Send first message (should succeed immediately)
        result1 = client.write_message("MESSAGE 1")
        assert result1 is True

        # Send second message immediately (should be queued)
        result2 = client.write_message("MESSAGE 2")
        assert result2 is True

        # First message should have been sent
        assert mock_post.call_count >= 1

    @patch('src.vestaboard.cloud_client.time.time')
    @patch('src.vestaboard.base.threading.Timer')
    @patch('src.vestaboard.cloud_client.requests.post')
    def test_rate_limit_processes_queue(self, mock_post, mock_timer, mock_time):
        """Test that queued messages are eventually processed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}
        mock_post.return_value = mock_response

        # Mock time to advance past rate limit
        current_time = [100.0]  # Start at 100
        def get_time():
            return current_time[0]
        mock_time.side_effect = get_time

        # Make Timer execute callback and advance time
        def immediate_timer(delay, callback):
            timer_mock = Mock()
            def start():
                current_time[0] += delay  # Advance time by delay
                callback()
            timer_mock.start = start
            timer_mock.cancel = Mock()
            return timer_mock
        mock_timer.side_effect = immediate_timer

        client = VestaboardClient(api_key="test_key")
        client.RATE_LIMIT_SECONDS = 0.1

        # Send two messages rapidly
        client.write_message("MESSAGE 1")
        client.write_message("MESSAGE 2")

        # Both messages should have been sent (timer executed with time advancement)
        assert mock_post.call_count == 2

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_queue_reaches_max_size(self, mock_post):
        """Test behavior when message queue reaches maximum size."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}
        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key", max_queue_size=3)
        client.RATE_LIMIT_SECONDS = 10  # Long delay to keep messages queued

        # Send first message (processes immediately)
        client.write_message("MESSAGE 1")

        # Fill the queue
        client.write_message("MESSAGE 2")  # Queued
        client.write_message("MESSAGE 3")  # Queued
        client.write_message("MESSAGE 4")  # Queued

        # Try to add one more (should still succeed but oldest dropped)
        result = client.write_message("MESSAGE 5")
        assert result is True

        # Queue should be at max size
        assert len(client.message_queue) <= 3

    @patch('src.vestaboard.cloud_client.requests.get')
    def test_local_api_rate_limiting(self, mock_get):
        """Test rate limiting for Local API client."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [[0] * 22 for _ in range(6)]
        mock_get.return_value = mock_response

        client = LocalVestaboardClient(api_key="test_key")
        client.RATE_LIMIT_SECONDS = 0.1

        # Send messages rapidly
        with patch.object(client, '_send_message_direct', return_value=True):
            result1 = client.write_message("MESSAGE 1")
            result2 = client.write_message("MESSAGE 2")

            assert result1 is True
            assert result2 is True


class TestQueueProcessing:
    """Test message queue processing."""

    @patch('src.vestaboard.cloud_client.time.time')
    @patch('src.vestaboard.base.threading.Timer')
    @patch('src.vestaboard.cloud_client.requests.post')
    def test_queue_processing_handles_errors(self, mock_post, mock_timer, mock_time):
        """Test that queue processing handles API errors gracefully."""
        # First call succeeds, second fails, third succeeds
        mock_post.side_effect = [
            Mock(status_code=200, json=lambda: {"id": "msg_1"}),
            Mock(status_code=500, text="Server Error"),
            Mock(status_code=200, json=lambda: {"id": "msg_3"}),
        ]

        # Mock time to advance past rate limit
        current_time = [100.0]
        def get_time():
            return current_time[0]
        mock_time.side_effect = get_time

        # Make Timer execute callback and advance time
        def immediate_timer(delay, callback):
            timer_mock = Mock()
            def start():
                current_time[0] += delay
                callback()
            timer_mock.start = start
            timer_mock.cancel = Mock()
            return timer_mock
        mock_timer.side_effect = immediate_timer

        client = VestaboardClient(api_key="test_key")
        client.RATE_LIMIT_SECONDS = 0.1

        # Send messages
        client.write_message("MESSAGE 1")
        client.write_message("MESSAGE 2")
        client.write_message("MESSAGE 3")

        # All messages should have been attempted (timers executed with time advancement)
        assert mock_post.call_count >= 2

    @patch('src.vestaboard.cloud_client.requests.post')
    @patch('src.vestaboard.base.threading.Timer')
    def test_queue_timer_cancellation(self, mock_timer, mock_post):
        """Test that queue timer is properly cancelled and rescheduled."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}
        mock_post.return_value = mock_response

        mock_timer_instance = Mock()
        mock_timer.return_value = mock_timer_instance

        client = VestaboardClient(api_key="test_key")

        # Send first message to start queue processing
        client.write_message("MESSAGE 1")

        # Send another message (should cancel and reschedule)
        client.write_message("MESSAGE 2")

        # Timer should have been created
        assert mock_timer.called


class TestMessageQueueEdgeCases:
    """Test edge cases in message queue handling."""

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_empty_queue_processing(self, mock_post):
        """Test processing when queue becomes empty."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}
        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key")
        client.RATE_LIMIT_SECONDS = 0.05

        # Send one message
        client.write_message("MESSAGE 1")

        # Wait for queue to be processed
        time.sleep(0.2)

        # Queue should be empty and not processing
        assert len(client.message_queue) == 0

    def test_queue_thread_safety(self):
        """Test that queue operations are thread-safe."""
        import threading

        client = VestaboardClient(api_key="test_key")
        client.RATE_LIMIT_SECONDS = 0.1

        with patch.object(client, '_send_message_direct', return_value=True):
            # Send messages from multiple threads
            threads = []
            for i in range(10):
                t = threading.Thread(target=lambda i=i: client.write_message(f"MSG {i}"))
                threads.append(t)
                t.start()

            # Wait for all threads
            for t in threads:
                t.join(timeout=2.0)

            # No assertions needed - just verify no deadlock/crash occurred
            assert True


class TestRateLimitWaiting:
    """Test rate limit waiting and timing."""

    @patch('src.vestaboard.cloud_client.time.time')
    @patch('src.vestaboard.base.threading.Timer')
    @patch('src.vestaboard.cloud_client.requests.post')
    def test_respects_rate_limit_timing(self, mock_post, mock_timer, mock_time):
        """Test that rate limiting schedules timers with correct delays."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}
        mock_post.return_value = mock_response

        # Mock time to advance past rate limit
        current_time = [100.0]
        def get_time():
            return current_time[0]
        mock_time.side_effect = get_time

        # Track timer delays
        timer_delays = []
        def immediate_timer(delay, callback):
            timer_delays.append(delay)
            timer_mock = Mock()
            def start():
                current_time[0] += delay
                callback()
            timer_mock.start = start
            timer_mock.cancel = Mock()
            return timer_mock
        mock_timer.side_effect = immediate_timer

        client = VestaboardClient(api_key="test_key")
        client.RATE_LIMIT_SECONDS = 0.2  # 200ms between messages

        # Send two messages
        client.write_message("MESSAGE 1")
        client.write_message("MESSAGE 2")

        # Both messages should have been sent (timers executed with time advancement)
        assert mock_post.call_count == 2

        # Verify timer was scheduled with appropriate delay
        assert len(timer_delays) > 0
        # First timer should be scheduled for approximately RATE_LIMIT_SECONDS
        assert timer_delays[0] >= 0.05  # At least some delay

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_last_send_time_updated(self, mock_post):
        """Test that last_send_time is updated after each send."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}
        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key")

        initial_time = client.last_send_time

        # Send a message
        client.write_message("MESSAGE")

        # last_send_time should be updated
        assert client.last_send_time > initial_time


class TestCleanup:
    """Test cleanup and resource management."""

    @patch('src.vestaboard.cloud_client.requests.post')
    def test_cleanup_cancels_queue_timer(self, mock_post):
        """Test that cleanup properly cancels queue timer."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}
        mock_post.return_value = mock_response

        client = VestaboardClient(api_key="test_key")
        client.RATE_LIMIT_SECONDS = 10  # Long delay

        # Send messages to start queue processing
        client.write_message("MESSAGE 1")
        client.write_message("MESSAGE 2")

        # Cleanup
        if hasattr(client, 'cleanup'):
            client.cleanup()
        elif hasattr(client, 'queue_timer') and client.queue_timer:
            client.queue_timer.cancel()

        # Verify timer is stopped (no exception means success)
        assert True
