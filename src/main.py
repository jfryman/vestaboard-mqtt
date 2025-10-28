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

    # Helper function to parse boolean environment variables
    def parse_bool(value: str, default: bool = False) -> bool:
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    # Build MQTT configuration
    mqtt_config = {
        "host": os.getenv("MQTT_BROKER_HOST", "localhost"),
        "port": int(os.getenv("MQTT_BROKER_PORT", "1883")),
        "username": os.getenv("MQTT_USERNAME"),
        "password": os.getenv("MQTT_PASSWORD"),
        "topic_prefix": os.getenv("MQTT_TOPIC_PREFIX", "vestaboard"),
        "client_id": os.getenv("MQTT_CLIENT_ID", ""),
        "clean_session": parse_bool(os.getenv("MQTT_CLEAN_SESSION"), True),
        "keepalive": int(os.getenv("MQTT_KEEPALIVE", "60")),
        "qos": int(os.getenv("MQTT_QOS", "0"))
    }

    # Add TLS/SSL configuration if enabled
    if parse_bool(os.getenv("MQTT_TLS_ENABLED")):
        mqtt_config["tls"] = {
            "enabled": True,
            "ca_certs": os.getenv("MQTT_TLS_CA_CERTS"),
            "certfile": os.getenv("MQTT_TLS_CERTFILE"),
            "keyfile": os.getenv("MQTT_TLS_KEYFILE"),
            "insecure": parse_bool(os.getenv("MQTT_TLS_INSECURE"), False)
        }

    # Add Last Will and Testament configuration if topic is specified
    lwt_topic = os.getenv("MQTT_LWT_TOPIC")
    if lwt_topic:
        mqtt_config["lwt"] = {
            "topic": lwt_topic,
            "payload": os.getenv("MQTT_LWT_PAYLOAD", "offline"),
            "qos": int(os.getenv("MQTT_LWT_QOS", "0")),
            "retain": parse_bool(os.getenv("MQTT_LWT_RETAIN"), True)
        }

    config = {
        "vestaboard_api_key": os.getenv("VESTABOARD_API_KEY") or os.getenv("VESTABOARD_LOCAL_API_KEY"),
        "mqtt": mqtt_config,
        "http_port": int(os.getenv("HTTP_PORT", "8000")),
        "max_queue_size": int(os.getenv("MAX_QUEUE_SIZE", "10"))
    }

    # Validate required configuration - API key will be auto-detected by factory function
    # Keep validation for backward compatibility but make it more flexible
    if not config["vestaboard_api_key"]:
        # Let the factory function handle the error with more detailed messaging
        config["vestaboard_api_key"] = None

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