"""Comprehensive tests for main configuration and application entry point."""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import ValidationError

from src.config import AppConfig
from tests.conftest import create_test_app_config


class TestLoadConfigBasics:
    """Test basic configuration loading."""

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key"}, clear=True)
    def test_load_config_defaults(self, mock_load_dotenv):
        """Test AppConfig with all default values."""
        config = AppConfig.from_env()

        # MQTT defaults
        assert config.mqtt.host == "localhost"
        assert config.mqtt.port == 1883
        assert config.mqtt.username is None
        assert config.mqtt.password is None
        assert config.mqtt.topic_prefix == "vestaboard"
        assert config.mqtt.client_id == ""
        assert config.mqtt.clean_session is True
        assert config.mqtt.keepalive == 60
        assert config.mqtt.qos == 0

        # HTTP defaults
        assert config.http_port == 8000

        # Queue defaults
        assert config.max_queue_size == 10

    @patch.dict(
        os.environ,
        {
            "VESTABOARD_API_KEY": "test_key",
            "MQTT_BROKER_HOST": "mqtt.example.com",
            "MQTT_BROKER_PORT": "8883",
        },
        clear=True,
    )
    def test_load_config_custom_broker(self):
        """Test AppConfig with custom broker settings."""
        config = AppConfig.from_env()

        assert config.mqtt.host == "mqtt.example.com"
        assert config.mqtt.port == 8883

    @patch.dict(
        os.environ,
        {
            "VESTABOARD_API_KEY": "test_key",
            "MQTT_USERNAME": "test_user",
            "MQTT_PASSWORD": "test_pass",
        },
        clear=True,
    )
    def test_load_config_with_authentication(self):
        """Test AppConfig with MQTT authentication."""
        config = AppConfig.from_env()

        assert config.mqtt.username == "test_user"
        assert config.mqtt.password == "test_pass"


class TestTopicPrefixConfiguration:
    """Test MQTT topic prefix configuration."""

    @patch("src.config.load_dotenv")
    @patch.dict(
        os.environ,
        {"VESTABOARD_API_KEY": "test_key", "MQTT_TOPIC_PREFIX": "office-board"},
        clear=True,
    )
    def test_custom_topic_prefix(self, mock_load_dotenv):
        """Test custom topic prefix configuration."""
        config = AppConfig.from_env()

        assert config.mqtt.topic_prefix == "office-board"

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key"}, clear=True)
    def test_default_topic_prefix(self, mock_load_dotenv):
        """Test default topic prefix."""
        config = AppConfig.from_env()

        assert config.mqtt.topic_prefix == "vestaboard"


class TestMQTTAdvancedConfiguration:
    """Test advanced MQTT configuration options."""

    @patch.dict(
        os.environ,
        {
            "VESTABOARD_API_KEY": "test_key",
            "MQTT_CLIENT_ID": "custom-client-123",
            "MQTT_CLEAN_SESSION": "false",
            "MQTT_KEEPALIVE": "120",
            "MQTT_QOS": "2",
        },
        clear=True,
    )
    def test_advanced_mqtt_settings(self):
        """Test advanced MQTT configuration."""
        config = AppConfig.from_env()

        assert config.mqtt.client_id == "custom-client-123"
        assert config.mqtt.clean_session is False
        assert config.mqtt.keepalive == 120
        assert config.mqtt.qos == 2

    @patch.dict(
        os.environ, {"VESTABOARD_API_KEY": "test_key", "MQTT_CLEAN_SESSION": "true"}, clear=True
    )
    def test_clean_session_true(self):
        """Test clean_session parsing with true value."""
        config = AppConfig.from_env()

        assert config.mqtt.clean_session is True

    @patch.dict(
        os.environ, {"VESTABOARD_API_KEY": "test_key", "MQTT_CLEAN_SESSION": "1"}, clear=True
    )
    def test_clean_session_numeric(self):
        """Test clean_session parsing with numeric value."""
        config = AppConfig.from_env()

        assert config.mqtt.clean_session is True

    @patch.dict(
        os.environ, {"VESTABOARD_API_KEY": "test_key", "MQTT_CLEAN_SESSION": "yes"}, clear=True
    )
    def test_clean_session_yes(self):
        """Test clean_session parsing with 'yes' value."""
        config = AppConfig.from_env()

        assert config.mqtt.clean_session is True

    @patch.dict(
        os.environ, {"VESTABOARD_API_KEY": "test_key", "MQTT_CLEAN_SESSION": "on"}, clear=True
    )
    def test_clean_session_on(self):
        """Test clean_session parsing with 'on' value."""
        config = AppConfig.from_env()

        assert config.mqtt.clean_session is True


class TestTLSConfiguration:
    """Test TLS/SSL configuration."""

    @patch("os.path.exists", return_value=True)
    @patch.dict(
        os.environ,
        {
            "VESTABOARD_API_KEY": "test_key",
            "MQTT_TLS_ENABLED": "true",
            "MQTT_TLS_CA_CERTS": "/path/to/ca.crt",
        },
        clear=True,
    )
    def test_tls_basic_configuration(self, mock_exists):
        """Test basic TLS configuration."""
        config = AppConfig.from_env()

        assert config.mqtt.tls is not None
        assert config.mqtt.tls.enabled is True
        assert config.mqtt.tls.ca_certs == "/path/to/ca.crt"
        assert config.mqtt.tls.insecure is False

    @patch("os.path.exists", return_value=True)
    @patch.dict(
        os.environ,
        {
            "VESTABOARD_API_KEY": "test_key",
            "MQTT_TLS_ENABLED": "true",
            "MQTT_TLS_CA_CERTS": "/path/to/ca.crt",
            "MQTT_TLS_CERTFILE": "/path/to/client.crt",
            "MQTT_TLS_KEYFILE": "/path/to/client.key",
        },
        clear=True,
    )
    def test_tls_with_client_certificates(self, mock_exists):
        """Test TLS configuration with client certificates."""
        config = AppConfig.from_env()

        assert config.mqtt.tls.certfile == "/path/to/client.crt"
        assert config.mqtt.tls.keyfile == "/path/to/client.key"

    @patch("os.path.exists", return_value=True)
    @patch.dict(
        os.environ,
        {
            "VESTABOARD_API_KEY": "test_key",
            "MQTT_TLS_ENABLED": "true",
            "MQTT_TLS_CA_CERTS": "/path/to/ca.crt",
            "MQTT_TLS_INSECURE": "true",
        },
        clear=True,
    )
    def test_tls_insecure_mode(self, mock_exists):
        """Test TLS insecure mode configuration."""
        config = AppConfig.from_env()

        assert config.mqtt.tls.insecure is True

    @patch.dict(
        os.environ, {"VESTABOARD_API_KEY": "test_key", "MQTT_TLS_ENABLED": "false"}, clear=True
    )
    def test_tls_disabled(self):
        """Test TLS disabled configuration."""
        config = AppConfig.from_env()

        assert config.mqtt.tls is None

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key"}, clear=True)
    def test_tls_not_configured_by_default(self, mock_load_dotenv):
        """Test TLS is not configured by default."""
        config = AppConfig.from_env()

        assert config.mqtt.tls is None


class TestLWTConfiguration:
    """Test Last Will and Testament configuration."""

    @patch("src.config.load_dotenv")
    @patch.dict(
        os.environ,
        {"VESTABOARD_API_KEY": "test_key", "MQTT_LWT_TOPIC": "vestaboard/status"},
        clear=True,
    )
    def test_lwt_basic_configuration(self, mock_load_dotenv):
        """Test basic LWT configuration."""
        config = AppConfig.from_env()

        assert config.mqtt.lwt is not None
        assert config.mqtt.lwt.topic == "vestaboard/status"
        assert config.mqtt.lwt.payload == "offline"
        assert config.mqtt.lwt.qos == 0
        assert config.mqtt.lwt.retain is True

    @patch("src.config.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "VESTABOARD_API_KEY": "test_key",
            "MQTT_LWT_TOPIC": "status/board",
            "MQTT_LWT_PAYLOAD": "disconnected",
            "MQTT_LWT_QOS": "2",
            "MQTT_LWT_RETAIN": "false",
        },
        clear=True,
    )
    def test_lwt_custom_configuration(self, mock_load_dotenv):
        """Test custom LWT configuration."""
        config = AppConfig.from_env()

        assert config.mqtt.lwt.topic == "status/board"
        assert config.mqtt.lwt.payload == "disconnected"
        assert config.mqtt.lwt.qos == 2
        assert config.mqtt.lwt.retain is False

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key"}, clear=True)
    def test_lwt_not_configured_by_default(self, mock_load_dotenv):
        """Test LWT is not configured by default."""
        config = AppConfig.from_env()

        assert config.mqtt.lwt is None


class TestVestaboardAPIConfiguration:
    """Test Vestaboard API key configuration."""

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_cloud_key"}, clear=True)
    def test_cloud_api_key(self, mock_load_dotenv):
        """Test cloud API key configuration."""
        config = AppConfig.from_env()

        assert config.vestaboard.api_key == "test_cloud_key"

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {"VESTABOARD_LOCAL_API_KEY": "test_local_key"}, clear=True)
    def test_local_api_key(self, mock_load_dotenv):
        """Test local API key configuration."""
        config = AppConfig.from_env()

        assert config.vestaboard.local_api_key == "test_local_key"

    @patch("src.config.load_dotenv")
    @patch.dict(
        os.environ,
        {"VESTABOARD_API_KEY": "cloud_key", "VESTABOARD_LOCAL_API_KEY": "local_key"},
        clear=True,
    )
    def test_local_api_key_takes_precedence(self, mock_load_dotenv):
        """Test that local API key takes precedence over cloud key."""
        config = AppConfig.from_env()

        assert config.vestaboard.local_api_key == "local_key"
        assert config.vestaboard.api_key == "cloud_key"

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {}, clear=True)
    def test_no_api_key_configured(self, mock_load_dotenv):
        """Test behavior when no API key is configured."""
        with pytest.raises(ValidationError):
            config = AppConfig.from_env()


class TestHTTPConfiguration:
    """Test HTTP server configuration."""

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key", "HTTP_PORT": "9000"}, clear=True)
    def test_custom_http_port(self, mock_load_dotenv):
        """Test custom HTTP port configuration."""
        config = AppConfig.from_env()

        assert config.http_port == 9000

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key"}, clear=True)
    def test_default_http_port(self, mock_load_dotenv):
        """Test default HTTP port."""
        config = AppConfig.from_env()

        assert config.http_port == 8000


class TestQueueConfiguration:
    """Test message queue configuration."""

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key", "MAX_QUEUE_SIZE": "25"}, clear=True)
    def test_custom_queue_size(self, mock_load_dotenv):
        """Test custom queue size configuration."""
        config = AppConfig.from_env()

        assert config.max_queue_size == 25

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key"}, clear=True)
    def test_default_queue_size(self, mock_load_dotenv):
        """Test default queue size."""
        config = AppConfig.from_env()

        assert config.max_queue_size == 10


class TestBooleanParsing:
    """Test boolean environment variable parsing."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("YES", True),
            ("on", True),
            ("ON", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("", False),
            ("random", False),
        ],
    )
    def test_parse_bool_values(self, value, expected):
        """Parametrized test for boolean parsing."""
        with patch("os.path.exists", return_value=True):
            with patch.dict(
                os.environ,
                {
                    "VESTABOARD_API_KEY": "test_key",
                    "MQTT_TLS_ENABLED": value,
                    "MQTT_TLS_CA_CERTS": "/path/to/ca.crt",
                },
                clear=True,
            ):
                if expected:
                    config = AppConfig.from_env()
                    assert config.mqtt.tls is not None
                    assert config.mqtt.tls.enabled is True
                else:
                    config = AppConfig.from_env()
                    assert config.mqtt.tls is None


class TestCompleteConfiguration:
    """Test complete configuration with all options."""

    @patch("os.path.exists", return_value=True)
    @patch("src.config.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "VESTABOARD_API_KEY": "api_key_123",
            "MQTT_BROKER_HOST": "mqtt.example.com",
            "MQTT_BROKER_PORT": "8883",
            "MQTT_USERNAME": "mqtt_user",
            "MQTT_PASSWORD": "mqtt_pass",
            "MQTT_TOPIC_PREFIX": "office-board",
            "MQTT_CLIENT_ID": "office-client",
            "MQTT_CLEAN_SESSION": "false",
            "MQTT_KEEPALIVE": "90",
            "MQTT_QOS": "1",
            "MQTT_TLS_ENABLED": "true",
            "MQTT_TLS_CA_CERTS": "/certs/ca.crt",
            "MQTT_TLS_CERTFILE": "/certs/client.crt",
            "MQTT_TLS_KEYFILE": "/certs/client.key",
            "MQTT_TLS_INSECURE": "false",
            "MQTT_LWT_TOPIC": "office-board/status",
            "MQTT_LWT_PAYLOAD": "offline",
            "MQTT_LWT_QOS": "2",
            "MQTT_LWT_RETAIN": "true",
            "HTTP_PORT": "9000",
            "MAX_QUEUE_SIZE": "20",
        },
        clear=True,
    )
    def test_complete_configuration(self, mock_load_dotenv, mock_exists):
        """Test loading complete configuration with all options."""
        config = AppConfig.from_env()

        # Vestaboard
        assert config.vestaboard.api_key == "api_key_123"

        # MQTT basic
        assert config.mqtt.host == "mqtt.example.com"
        assert config.mqtt.port == 8883
        assert config.mqtt.username == "mqtt_user"
        assert config.mqtt.password == "mqtt_pass"
        assert config.mqtt.topic_prefix == "office-board"
        assert config.mqtt.client_id == "office-client"
        assert config.mqtt.clean_session is False
        assert config.mqtt.keepalive == 90
        assert config.mqtt.qos == 1

        # TLS
        assert config.mqtt.tls.enabled is True
        assert config.mqtt.tls.ca_certs == "/certs/ca.crt"
        assert config.mqtt.tls.certfile == "/certs/client.crt"
        assert config.mqtt.tls.keyfile == "/certs/client.key"
        assert config.mqtt.tls.insecure is False

        # LWT
        assert config.mqtt.lwt.topic == "office-board/status"
        assert config.mqtt.lwt.payload == "offline"
        assert config.mqtt.lwt.qos == 2
        assert config.mqtt.lwt.retain is True

        # HTTP
        assert config.http_port == 9000

        # Queue
        assert config.max_queue_size == 20


class TestConfigurationStructure:
    """Test configuration structure and keys."""

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key"}, clear=True)
    def test_config_has_required_keys(self, mock_load_dotenv):
        """Test that configuration has all required attributes."""
        config = AppConfig.from_env()

        # Top-level attributes
        assert hasattr(config, "vestaboard")
        assert hasattr(config, "mqtt")
        assert hasattr(config, "http_port")
        assert hasattr(config, "max_queue_size")

        # Vestaboard required attributes
        assert hasattr(config.vestaboard, "api_key")

        # MQTT required attributes
        mqtt_required = [
            "host",
            "port",
            "topic_prefix",
            "client_id",
            "clean_session",
            "keepalive",
            "qos",
        ]
        for attr in mqtt_required:
            assert hasattr(config.mqtt, attr)

    @patch("src.config.load_dotenv")
    @patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key"}, clear=True)
    def test_config_types_are_correct(self, mock_load_dotenv):
        """Test that configuration values have correct types."""
        config = AppConfig.from_env()

        # String types
        assert isinstance(config.mqtt.host, str)
        assert isinstance(config.mqtt.topic_prefix, str)
        assert isinstance(config.mqtt.client_id, str)

        # Integer types
        assert isinstance(config.mqtt.port, int)
        assert isinstance(config.mqtt.keepalive, int)
        assert isinstance(config.mqtt.qos, int)
        assert isinstance(config.http_port, int)
        assert isinstance(config.max_queue_size, int)

        # Boolean types
        assert isinstance(config.mqtt.clean_session, bool)


@pytest.mark.parametrize(
    "env_var,config_attr,default_value",
    [
        ("MQTT_BROKER_HOST", "host", "localhost"),
        ("MQTT_BROKER_PORT", "port", 1883),
        ("MQTT_TOPIC_PREFIX", "topic_prefix", "vestaboard"),
        ("MQTT_CLIENT_ID", "client_id", ""),
        ("MQTT_KEEPALIVE", "keepalive", 60),
        ("MQTT_QOS", "qos", 0),
    ],
)
def test_mqtt_defaults_parametrized(env_var, config_attr, default_value):
    """Parametrized test for MQTT default values."""
    with patch("src.config.load_dotenv"):
        with patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key"}, clear=True):
            config = AppConfig.from_env()
            assert getattr(config.mqtt, config_attr) == default_value


class TestDotenvLoading:
    """Test .env file loading."""

    @patch("src.config.load_dotenv")
    def test_load_dotenv_is_called(self, mock_load_dotenv):
        """Test that load_dotenv is called during configuration loading."""
        with patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key"}, clear=True):
            AppConfig.from_env()
            mock_load_dotenv.assert_called_once()
