"""Main application entry point."""

import os
import threading
import uvicorn
from dotenv import load_dotenv
from .mqtt_bridge import VestaboardMQTTBridge
from .http_api import create_app
from .logger import setup_logger


def load_config():
    """Load configuration from environment variables."""
    load_dotenv()
    
    config = {
        "vestaboard_api_key": os.getenv("VESTABOARD_API_KEY"),
        "mqtt": {
            "host": os.getenv("MQTT_BROKER_HOST", "localhost"),
            "port": int(os.getenv("MQTT_BROKER_PORT", "1883")),
            "username": os.getenv("MQTT_USERNAME"),
            "password": os.getenv("MQTT_PASSWORD")
        },
        "http_port": int(os.getenv("HTTP_PORT", "8000")),
        "max_queue_size": int(os.getenv("MAX_QUEUE_SIZE", "10"))
    }
    
    # Validate required configuration
    if not config["vestaboard_api_key"]:
        raise ValueError("VESTABOARD_API_KEY environment variable is required")
    
    return config


def main():
    """Main application entry point."""
    # Set up main logger first
    logger = setup_logger(__name__)
    
    try:
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Initialize MQTT bridge
        mqtt_bridge = VestaboardMQTTBridge(
            config["vestaboard_api_key"],
            config["mqtt"],
            config["max_queue_size"]
        )
        
        # Create HTTP API
        app = create_app(mqtt_bridge)
        
        # Start MQTT bridge in separate thread
        mqtt_thread = threading.Thread(target=mqtt_bridge.start, daemon=True)
        mqtt_thread.start()
        logger.info("MQTT bridge started")
        
        # Start HTTP API server
        logger.info(f"Starting HTTP API server on port {config['http_port']}")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=config["http_port"],
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        raise


if __name__ == "__main__":
    main()