"""Pytest configuration and fixtures for Vestaboard MQTT tests."""

import pytest

from src.config import AppConfig, LWTConfig, MQTTConfig, TLSConfig, VestaboardConfig

# ============================================================================
# Helper Functions for Creating Test Configurations
# ============================================================================


def create_test_vestaboard_config(
    api_key: str = "test_api_key",
    local_api_key: str = None,
    use_local_api: bool = False,
    local_host: str = "vestaboard.local",
    local_port: int = 7000,
    board_type: str = "standard",
    max_queue_size: int = 10,
) -> VestaboardConfig:
    """Create a VestaboardConfig for testing with sensible defaults.

    Args:
        api_key: Cloud API key (default: "test_api_key")
        local_api_key: Local API key (optional)
        use_local_api: Whether to use Local API
        local_host: Local API hostname
        local_port: Local API port
        board_type: Board type ("standard" or "note")
        max_queue_size: Maximum message queue size

    Returns:
        VestaboardConfig instance ready for testing
    """
    return VestaboardConfig(
        api_key=api_key,
        local_api_key=local_api_key,
        use_local_api=use_local_api,
        local_host=local_host,
        local_port=local_port,
        board_type=board_type,
        max_queue_size=max_queue_size,
    )


def create_test_mqtt_config(
    host: str = "localhost",
    port: int = 1883,
    username: str = None,
    password: str = None,
    topic_prefix: str = "vestaboard",
    client_id: str = "",
    clean_session: bool = True,
    keepalive: int = 60,
    qos: int = 0,
    tls: TLSConfig = None,
    lwt: LWTConfig = None,
) -> MQTTConfig:
    """Create an MQTTConfig for testing with sensible defaults.

    Args:
        host: MQTT broker hostname
        port: MQTT broker port
        username: MQTT username (optional)
        password: MQTT password (optional)
        topic_prefix: Topic prefix for all MQTT topics
        client_id: MQTT client ID
        clean_session: Clean session flag
        keepalive: Keep-alive interval in seconds
        qos: QoS level (0-2)
        tls: TLS configuration (optional)
        lwt: Last Will and Testament configuration (optional)

    Returns:
        MQTTConfig instance ready for testing
    """
    return MQTTConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        topic_prefix=topic_prefix,
        client_id=client_id,
        clean_session=clean_session,
        keepalive=keepalive,
        qos=qos,
        tls=tls,
        lwt=lwt,
    )


def create_test_app_config(
    vestaboard_api_key: str = "test_api_key",
    vestaboard_config: VestaboardConfig = None,
    mqtt_config: MQTTConfig = None,
    http_port: int = 8000,
    max_queue_size: int = 10,
    **vestaboard_kwargs,
) -> AppConfig:
    """Create an AppConfig for testing with sensible defaults.

    This is the main helper function for creating test configurations.
    You can either:
    1. Pass a pre-built vestaboard_config
    2. Pass vestaboard_api_key to build one automatically
    3. Pass vestaboard_kwargs to customize the vestaboard config

    Args:
        vestaboard_api_key: API key for Vestaboard (used if vestaboard_config not provided)
        vestaboard_config: Pre-built VestaboardConfig (optional)
        mqtt_config: Pre-built MQTTConfig (optional, defaults to basic config)
        http_port: HTTP API port
        max_queue_size: Maximum message queue size
        **vestaboard_kwargs: Additional arguments to pass to create_test_vestaboard_config()

    Returns:
        AppConfig instance ready for testing

    Examples:
        >>> # Simple usage
        >>> config = create_test_app_config()

        >>> # Custom API key
        >>> config = create_test_app_config(vestaboard_api_key="my_key")

        >>> # Custom MQTT config
        >>> mqtt = create_test_mqtt_config(topic_prefix="custom")
        >>> config = create_test_app_config(mqtt_config=mqtt)

        >>> # Custom vestaboard settings via kwargs
        >>> config = create_test_app_config(board_type="note", local_api_key="local_key")
    """
    # Build vestaboard config if not provided
    if vestaboard_config is None:
        vestaboard_config = create_test_vestaboard_config(
            api_key=vestaboard_api_key, max_queue_size=max_queue_size, **vestaboard_kwargs
        )

    # Build MQTT config if not provided
    if mqtt_config is None:
        mqtt_config = create_test_mqtt_config()

    return AppConfig(
        vestaboard=vestaboard_config,
        mqtt=mqtt_config,
        http_port=http_port,
        max_queue_size=max_queue_size,
    )


# Backward compatibility alias (for existing tests using old name)
def create_test_config(
    api_key: str = "test_key", topic_prefix: str = "vestaboard", **mqtt_kwargs
) -> AppConfig:
    """Helper function to create test AppConfig with custom settings.

    DEPRECATED: Use create_test_app_config() instead.
    This function is kept for backward compatibility with existing tests.

    Args:
        api_key: Vestaboard API key
        topic_prefix: MQTT topic prefix
        **mqtt_kwargs: Additional MQTT configuration parameters

    Returns:
        AppConfig instance for testing
    """
    mqtt_config = create_test_mqtt_config(topic_prefix=topic_prefix, **mqtt_kwargs)
    return create_test_app_config(vestaboard_api_key=api_key, mqtt_config=mqtt_config)


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture
def test_vestaboard_config():
    """Fixture providing a standard VestaboardConfig for testing."""
    return create_test_vestaboard_config()


@pytest.fixture
def test_mqtt_config():
    """Fixture providing a standard MQTTConfig for testing."""
    return create_test_mqtt_config()


@pytest.fixture
def test_app_config():
    """Fixture providing a standard AppConfig for testing."""
    return create_test_app_config()


@pytest.fixture
def test_app_config_with_local_api():
    """Fixture providing an AppConfig configured for Local API."""
    return create_test_app_config(local_api_key="test_local_key", use_local_api=True)


@pytest.fixture
def test_app_config_with_note_board():
    """Fixture providing an AppConfig configured for Vestaboard Note."""
    return create_test_app_config(board_type="note")
