"""Comprehensive tests for HTTP API endpoints."""

import time
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock, patch
from src.http_api import VestaboardHTTPAPI, create_app


class TestVestaboardHTTPAPIInitialization:
    """Test VestaboardHTTPAPI initialization."""

    def test_initialization(self):
        """Test HTTP API initializes correctly."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.active_timers = {}

        api = VestaboardHTTPAPI(mock_bridge)

        assert api.mqtt_bridge == mock_bridge
        assert api.app is not None
        assert isinstance(api.start_time, float)

    def test_create_app_factory(self):
        """Test create_app factory function."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)

        assert app is not None
        assert hasattr(app, 'title')


class TestHealthEndpoint:
    """Test /health endpoint for liveness probe."""

    def test_health_endpoint_returns_healthy(self):
        """Test health endpoint returns healthy status."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "vestaboard-mqtt-bridge"

    def test_health_endpoint_always_succeeds(self):
        """Test health endpoint succeeds even when MQTT disconnected."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.mqtt_client.is_connected.return_value = False
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        response = client.get("/health")

        # Health check should still succeed
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestReadyEndpoint:
    """Test /ready endpoint for readiness probe."""

    def test_ready_endpoint_when_connected(self):
        """Test ready endpoint returns ready when MQTT connected."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.mqtt_client.is_connected.return_value = True
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["mqtt_connected"] is True

    def test_ready_endpoint_when_disconnected(self):
        """Test ready endpoint returns not ready when MQTT disconnected."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.mqtt_client.is_connected.return_value = False
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not ready"
        assert data["mqtt_connected"] is False


class TestMetricsEndpoint:
    """Test /metrics endpoint for monitoring."""

    def test_metrics_endpoint_basic(self):
        """Test metrics endpoint returns basic metrics."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.mqtt_client.is_connected.return_value = True
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()

        # Check all required fields
        assert "uptime_seconds" in data
        assert "active_timers" in data
        assert "mqtt_connected" in data
        assert "service" in data
        assert "version" in data

        assert data["service"] == "vestaboard-mqtt-bridge"
        assert data["version"] == "1.0.0"
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0

    def test_metrics_endpoint_with_active_timers(self):
        """Test metrics endpoint reports active timer count."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.mqtt_client.is_connected.return_value = True
        mock_bridge.active_timers = {
            "timer_1": Mock(),
            "timer_2": Mock(),
            "timer_3": Mock()
        }

        app = create_app(mock_bridge)
        client = TestClient(app)

        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["active_timers"] == 3

    def test_metrics_endpoint_when_disconnected(self):
        """Test metrics endpoint when MQTT disconnected."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.mqtt_client.is_connected.return_value = False
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["mqtt_connected"] is False

    def test_metrics_endpoint_uptime_increases(self):
        """Test metrics endpoint uptime increases over time."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.mqtt_client.is_connected.return_value = True
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        # First call
        response1 = client.get("/metrics")
        uptime1 = response1.json()["uptime_seconds"]

        # Wait a bit
        time.sleep(0.1)

        # Second call
        response2 = client.get("/metrics")
        uptime2 = response2.json()["uptime_seconds"]

        # Uptime should have increased
        assert uptime2 > uptime1


class TestEndpointIntegration:
    """Test multiple endpoints together."""

    def test_all_endpoints_accessible(self):
        """Test that all endpoints are accessible."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.mqtt_client.is_connected.return_value = True
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        # Test all endpoints
        health_response = client.get("/health")
        ready_response = client.get("/ready")
        metrics_response = client.get("/metrics")

        assert health_response.status_code == 200
        assert ready_response.status_code == 200
        assert metrics_response.status_code == 200

    def test_nonexistent_endpoint_returns_404(self):
        """Test accessing non-existent endpoint returns 404."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        response = client.get("/nonexistent")

        assert response.status_code == 404


class TestAPIMetadata:
    """Test FastAPI metadata and configuration."""

    def test_api_has_correct_metadata(self):
        """Test API has correct title and description."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.active_timers = {}

        api = VestaboardHTTPAPI(mock_bridge)

        assert api.app.title == "Vestaboard MQTT Bridge"
        assert "Kubernetes health and metrics" in api.app.description
        assert api.app.version == "1.0.0"

    def test_openapi_schema_accessible(self):
        """Test OpenAPI schema is accessible."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "Vestaboard MQTT Bridge"


class TestKubernetesProbes:
    """Test Kubernetes probe compatibility."""

    def test_liveness_probe_format(self):
        """Test health endpoint format suitable for liveness probe."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        response = client.get("/health")

        # Kubernetes expects 200 status code
        assert response.status_code == 200
        # Should return JSON
        assert response.headers["content-type"] == "application/json"

    def test_readiness_probe_reflects_mqtt_state(self):
        """Test readiness probe accurately reflects MQTT connection state."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        # Test when connected
        mock_bridge.mqtt_client.is_connected.return_value = True
        response = client.get("/ready")
        assert response.json()["mqtt_connected"] is True

        # Test when disconnected
        mock_bridge.mqtt_client.is_connected.return_value = False
        response = client.get("/ready")
        assert response.json()["mqtt_connected"] is False


class TestConcurrentRequests:
    """Test API handles concurrent requests."""

    def test_multiple_concurrent_health_checks(self):
        """Test multiple health checks can run concurrently."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.mqtt_client.is_connected.return_value = True
        mock_bridge.active_timers = {}

        app = create_app(mock_bridge)
        client = TestClient(app)

        # Make multiple requests
        responses = [client.get("/health") for _ in range(10)]

        # All should succeed
        assert all(r.status_code == 200 for r in responses)
        assert all(r.json()["status"] == "healthy" for r in responses)

    def test_mixed_endpoint_requests(self):
        """Test different endpoints can be called in sequence."""
        mock_bridge = Mock()
        mock_bridge.mqtt_client = Mock()
        mock_bridge.mqtt_client.is_connected.return_value = True
        mock_bridge.active_timers = {"timer_1": Mock()}

        app = create_app(mock_bridge)
        client = TestClient(app)

        # Make requests to different endpoints
        health = client.get("/health")
        ready = client.get("/ready")
        metrics = client.get("/metrics")

        assert health.status_code == 200
        assert ready.status_code == 200
        assert metrics.status_code == 200

        # Verify different data in each
        assert "status" in health.json()
        assert "mqtt_connected" in ready.json()
        assert "uptime_seconds" in metrics.json()


@pytest.mark.parametrize("endpoint,expected_keys", [
    ("/health", ["status", "service"]),
    ("/ready", ["status", "mqtt_connected"]),
    ("/metrics", ["uptime_seconds", "active_timers", "mqtt_connected", "service", "version"]),
])
def test_endpoint_response_structure(endpoint, expected_keys):
    """Parametrized test for endpoint response structure."""
    mock_bridge = Mock()
    mock_bridge.mqtt_client = Mock()
    mock_bridge.mqtt_client.is_connected.return_value = True
    mock_bridge.active_timers = {}

    app = create_app(mock_bridge)
    client = TestClient(app)

    response = client.get(endpoint)

    assert response.status_code == 200
    data = response.json()

    for key in expected_keys:
        assert key in data
