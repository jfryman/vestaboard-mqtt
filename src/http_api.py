"""HTTP API for health and metrics endpoints."""

import time

from fastapi import FastAPI

from .mqtt import VestaboardMQTTBridge


class VestaboardHTTPAPI:
    """HTTP API for Kubernetes health and metrics endpoints."""

    def __init__(self, mqtt_bridge: VestaboardMQTTBridge):
        """Initialize the HTTP API.

        Args:
            mqtt_bridge: The MQTT bridge instance
        """
        self.mqtt_bridge = mqtt_bridge
        self.start_time = time.time()
        self.app = FastAPI(
            title="Vestaboard MQTT Bridge",
            description="Kubernetes health and metrics endpoints for Vestaboard MQTT Bridge",
            version="1.0.0",
        )

        self._setup_routes()

    def _setup_routes(self):
        """Set up FastAPI routes."""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint for Kubernetes liveness probe."""
            return {"status": "healthy", "service": "vestaboard-mqtt-bridge"}

        @self.app.get("/ready")
        async def readiness_check():
            """Readiness check endpoint for Kubernetes readiness probe."""
            # Check if MQTT client is connected
            mqtt_connected = self.mqtt_bridge.mqtt_client.is_connected()

            if mqtt_connected:
                return {"status": "ready", "mqtt_connected": True}
            else:
                return {"status": "not ready", "mqtt_connected": False}

        @self.app.get("/metrics")
        async def metrics():
            """Basic metrics endpoint for monitoring."""
            uptime = time.time() - self.start_time
            active_timer_count = len(self.mqtt_bridge.timer_manager.active_timers)
            mqtt_connected = self.mqtt_bridge.mqtt_client.is_connected()

            return {
                "uptime_seconds": round(uptime, 2),
                "active_timers": active_timer_count,
                "mqtt_connected": mqtt_connected,
                "service": "vestaboard-mqtt-bridge",
                "version": "1.0.0",
            }


def create_app(mqtt_bridge: VestaboardMQTTBridge) -> FastAPI:
    """Create FastAPI application instance.

    Args:
        mqtt_bridge: The MQTT bridge instance

    Returns:
        FastAPI application
    """
    api = VestaboardHTTPAPI(mqtt_bridge)
    return api.app
