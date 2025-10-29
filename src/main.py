"""Main application entry point."""

import logging
import threading
import uvicorn
from .config import AppConfig
from .mqtt_bridge import VestaboardMQTTBridge
from .http_api import create_app
from .logger import configure_logging


def main():
    """Main application entry point."""
    try:
        # Load configuration from environment first
        config = AppConfig.from_env()

        # Configure logging globally (once)
        configure_logging(config)

        # Get logger for this module
        logger = logging.getLogger(__name__)
        logger.info("Configuration loaded successfully")

        # Initialize MQTT bridge with configuration
        mqtt_bridge = VestaboardMQTTBridge(config)

        # Create HTTP API
        app = create_app(mqtt_bridge)

        # Start MQTT bridge in separate thread
        mqtt_thread = threading.Thread(target=mqtt_bridge.start, daemon=True)
        mqtt_thread.start()
        logger.info("MQTT bridge started")

        # Start HTTP API server
        logger.info(f"Starting HTTP API server on port {config.http_port}")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=config.http_port,
            log_level="info"
        )

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error starting application: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()