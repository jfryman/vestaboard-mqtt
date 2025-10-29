"""Pytest configuration and fixtures for Vestaboard MQTT tests."""

import pytest
from src.config import AppConfig, MQTTConfig


@pytest.fixture
def test_mqtt_config():
    """Create a test MQTT configuration."""
    return MQTTConfig(host="localhost", port=1883)


@pytest.fixture
def test_app_config(test_mqtt_config):
    """Create a test application configuration."""
    return AppConfig(
        vestaboard_api_key="test_key",
        mqtt=test_mqtt_config,
        http_port=8000,
        max_queue_size=10
    )


def create_test_config(
    api_key: str = "test_key",
    topic_prefix: str = "vestaboard",
    **mqtt_kwargs
) -> AppConfig:
    """Helper function to create test AppConfig with custom settings.

    Args:
        api_key: Vestaboard API key
        topic_prefix: MQTT topic prefix
        **mqtt_kwargs: Additional MQTT configuration parameters

    Returns:
        AppConfig instance for testing
    """
    mqtt_config = MQTTConfig(
        host="localhost",
        port=1883,
        topic_prefix=topic_prefix,
        **mqtt_kwargs
    )
    return AppConfig(
        vestaboard_api_key=api_key,
        mqtt=mqtt_config,
        http_port=8000,
        max_queue_size=10
    )
