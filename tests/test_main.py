"""Comprehensive tests for main configuration and application entry point."""

import os
import pytest
from unittest.mock import Mock, MagicMock, patch
from src.main import load_config


class TestLoadConfigBasics:
    """Test basic configuration loading."""

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_defaults(self, mock_load_dotenv):
        """Test load_config with all default values."""
        config = load_config()

        # MQTT defaults
        assert config["mqtt"]["host"] == "localhost"
        assert config["mqtt"]["port"] == 1883
        assert config["mqtt"]["username"] is None
        assert config["mqtt"]["password"] is None
        assert config["mqtt"]["topic_prefix"] == "vestaboard"
        assert config["mqtt"]["client_id"] == ""
        assert config["mqtt"]["clean_session"] is True
        assert config["mqtt"]["keepalive"] == 60
        assert config["mqtt"]["qos"] == 0

        # HTTP defaults
        assert config["http_port"] == 8000

        # Queue defaults
        assert config["max_queue_size"] == 10

    @patch.dict(os.environ, {
        "MQTT_BROKER_HOST": "mqtt.example.com",
        "MQTT_BROKER_PORT": "8883"
    }, clear=True)
    def test_load_config_custom_broker(self):
        """Test load_config with custom broker settings."""
        config = load_config()

        assert config["mqtt"]["host"] == "mqtt.example.com"
        assert config["mqtt"]["port"] == 8883

    @patch.dict(os.environ, {
        "MQTT_USERNAME": "test_user",
        "MQTT_PASSWORD": "test_pass"
    }, clear=True)
    def test_load_config_with_authentication(self):
        """Test load_config with MQTT authentication."""
        config = load_config()

        assert config["mqtt"]["username"] == "test_user"
        assert config["mqtt"]["password"] == "test_pass"


class TestTopicPrefixConfiguration:
    """Test MQTT topic prefix configuration."""

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {
        "MQTT_TOPIC_PREFIX": "office-board"
    }, clear=True)
    def test_custom_topic_prefix(self, mock_load_dotenv):
        """Test custom topic prefix configuration."""
        config = load_config()

        assert config["mqtt"]["topic_prefix"] == "office-board"

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_default_topic_prefix(self, mock_load_dotenv):
        """Test default topic prefix."""
        config = load_config()

        assert config["mqtt"]["topic_prefix"] == "vestaboard"


class TestMQTTAdvancedConfiguration:
    """Test advanced MQTT configuration options."""

    @patch.dict(os.environ, {
        "MQTT_CLIENT_ID": "custom-client-123",
        "MQTT_CLEAN_SESSION": "false",
        "MQTT_KEEPALIVE": "120",
        "MQTT_QOS": "2"
    }, clear=True)
    def test_advanced_mqtt_settings(self):
        """Test advanced MQTT configuration."""
        config = load_config()

        assert config["mqtt"]["client_id"] == "custom-client-123"
        assert config["mqtt"]["clean_session"] is False
        assert config["mqtt"]["keepalive"] == 120
        assert config["mqtt"]["qos"] == 2

    @patch.dict(os.environ, {
        "MQTT_CLEAN_SESSION": "true"
    }, clear=True)
    def test_clean_session_true(self):
        """Test clean_session parsing with true value."""
        config = load_config()

        assert config["mqtt"]["clean_session"] is True

    @patch.dict(os.environ, {
        "MQTT_CLEAN_SESSION": "1"
    }, clear=True)
    def test_clean_session_numeric(self):
        """Test clean_session parsing with numeric value."""
        config = load_config()

        assert config["mqtt"]["clean_session"] is True

    @patch.dict(os.environ, {
        "MQTT_CLEAN_SESSION": "yes"
    }, clear=True)
    def test_clean_session_yes(self):
        """Test clean_session parsing with 'yes' value."""
        config = load_config()

        assert config["mqtt"]["clean_session"] is True

    @patch.dict(os.environ, {
        "MQTT_CLEAN_SESSION": "on"
    }, clear=True)
    def test_clean_session_on(self):
        """Test clean_session parsing with 'on' value."""
        config = load_config()

        assert config["mqtt"]["clean_session"] is True


class TestTLSConfiguration:
    """Test TLS/SSL configuration."""

    @patch.dict(os.environ, {
        "MQTT_TLS_ENABLED": "true",
        "MQTT_TLS_CA_CERTS": "/path/to/ca.crt"
    }, clear=True)
    def test_tls_basic_configuration(self):
        """Test basic TLS configuration."""
        config = load_config()

        assert "tls" in config["mqtt"]
        assert config["mqtt"]["tls"]["enabled"] is True
        assert config["mqtt"]["tls"]["ca_certs"] == "/path/to/ca.crt"
        assert config["mqtt"]["tls"]["insecure"] is False

    @patch.dict(os.environ, {
        "MQTT_TLS_ENABLED": "true",
        "MQTT_TLS_CA_CERTS": "/path/to/ca.crt",
        "MQTT_TLS_CERTFILE": "/path/to/client.crt",
        "MQTT_TLS_KEYFILE": "/path/to/client.key"
    }, clear=True)
    def test_tls_with_client_certificates(self):
        """Test TLS configuration with client certificates."""
        config = load_config()

        assert config["mqtt"]["tls"]["certfile"] == "/path/to/client.crt"
        assert config["mqtt"]["tls"]["keyfile"] == "/path/to/client.key"

    @patch.dict(os.environ, {
        "MQTT_TLS_ENABLED": "true",
        "MQTT_TLS_CA_CERTS": "/path/to/ca.crt",
        "MQTT_TLS_INSECURE": "true"
    }, clear=True)
    def test_tls_insecure_mode(self):
        """Test TLS insecure mode configuration."""
        config = load_config()

        assert config["mqtt"]["tls"]["insecure"] is True

    @patch.dict(os.environ, {
        "MQTT_TLS_ENABLED": "false"
    }, clear=True)
    def test_tls_disabled(self):
        """Test TLS disabled configuration."""
        config = load_config()

        assert "tls" not in config["mqtt"]

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_tls_not_configured_by_default(self, mock_load_dotenv):
        """Test TLS is not configured by default."""
        config = load_config()

        assert "tls" not in config["mqtt"]


class TestLWTConfiguration:
    """Test Last Will and Testament configuration."""

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {
        "MQTT_LWT_TOPIC": "vestaboard/status"
    }, clear=True)
    def test_lwt_basic_configuration(self, mock_load_dotenv):
        """Test basic LWT configuration."""
        config = load_config()

        assert "lwt" in config["mqtt"]
        assert config["mqtt"]["lwt"]["topic"] == "vestaboard/status"
        assert config["mqtt"]["lwt"]["payload"] == "offline"
        assert config["mqtt"]["lwt"]["qos"] == 0
        assert config["mqtt"]["lwt"]["retain"] is True

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {
        "MQTT_LWT_TOPIC": "status/board",
        "MQTT_LWT_PAYLOAD": "disconnected",
        "MQTT_LWT_QOS": "2",
        "MQTT_LWT_RETAIN": "false"
    }, clear=True)
    def test_lwt_custom_configuration(self, mock_load_dotenv):
        """Test custom LWT configuration."""
        config = load_config()

        assert config["mqtt"]["lwt"]["topic"] == "status/board"
        assert config["mqtt"]["lwt"]["payload"] == "disconnected"
        assert config["mqtt"]["lwt"]["qos"] == 2
        assert config["mqtt"]["lwt"]["retain"] is False

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_lwt_not_configured_by_default(self, mock_load_dotenv):
        """Test LWT is not configured by default."""
        config = load_config()

        assert "lwt" not in config["mqtt"]


class TestVestaboardAPIConfiguration:
    """Test Vestaboard API key configuration."""

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {
        "VESTABOARD_API_KEY": "test_cloud_key"
    }, clear=True)
    def test_cloud_api_key(self, mock_load_dotenv):
        """Test cloud API key configuration."""
        config = load_config()

        assert config["vestaboard_api_key"] == "test_cloud_key"

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {
        "VESTABOARD_LOCAL_API_KEY": "test_local_key"
    }, clear=True)
    def test_local_api_key(self, mock_load_dotenv):
        """Test local API key configuration."""
        config = load_config()

        assert config["vestaboard_api_key"] == "test_local_key"

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {
        "VESTABOARD_API_KEY": "cloud_key",
        "VESTABOARD_LOCAL_API_KEY": "local_key"
    }, clear=True)
    def test_local_api_key_takes_precedence(self, mock_load_dotenv):
        """Test that local API key takes precedence over cloud key."""
        config = load_config()

        assert config["vestaboard_api_key"] == "local_key"

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_no_api_key_configured(self, mock_load_dotenv):
        """Test behavior when no API key is configured."""
        config = load_config()

        assert config["vestaboard_api_key"] is None


class TestHTTPConfiguration:
    """Test HTTP server configuration."""

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {
        "HTTP_PORT": "9000"
    }, clear=True)
    def test_custom_http_port(self, mock_load_dotenv):
        """Test custom HTTP port configuration."""
        config = load_config()

        assert config["http_port"] == 9000

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_default_http_port(self, mock_load_dotenv):
        """Test default HTTP port."""
        config = load_config()

        assert config["http_port"] == 8000


class TestQueueConfiguration:
    """Test message queue configuration."""

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {
        "MAX_QUEUE_SIZE": "25"
    }, clear=True)
    def test_custom_queue_size(self, mock_load_dotenv):
        """Test custom queue size configuration."""
        config = load_config()

        assert config["max_queue_size"] == 25

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_default_queue_size(self, mock_load_dotenv):
        """Test default queue size."""
        config = load_config()

        assert config["max_queue_size"] == 10


class TestBooleanParsing:
    """Test boolean environment variable parsing."""

    @pytest.mark.parametrize("value,expected", [
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
    ])
    def test_parse_bool_values(self, value, expected):
        """Parametrized test for boolean parsing."""
        with patch.dict(os.environ, {"MQTT_TLS_ENABLED": value}, clear=True):
            config = load_config()
            if expected:
                assert "tls" in config["mqtt"]
                assert config["mqtt"]["tls"]["enabled"] is True
            else:
                assert "tls" not in config["mqtt"]


class TestCompleteConfiguration:
    """Test complete configuration with all options."""

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {
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
        "MAX_QUEUE_SIZE": "20"
    }, clear=True)
    def test_complete_configuration(self, mock_load_dotenv):
        """Test loading complete configuration with all options."""
        config = load_config()

        # Vestaboard
        assert config["vestaboard_api_key"] == "api_key_123"

        # MQTT basic
        assert config["mqtt"]["host"] == "mqtt.example.com"
        assert config["mqtt"]["port"] == 8883
        assert config["mqtt"]["username"] == "mqtt_user"
        assert config["mqtt"]["password"] == "mqtt_pass"
        assert config["mqtt"]["topic_prefix"] == "office-board"
        assert config["mqtt"]["client_id"] == "office-client"
        assert config["mqtt"]["clean_session"] is False
        assert config["mqtt"]["keepalive"] == 90
        assert config["mqtt"]["qos"] == 1

        # TLS
        assert config["mqtt"]["tls"]["enabled"] is True
        assert config["mqtt"]["tls"]["ca_certs"] == "/certs/ca.crt"
        assert config["mqtt"]["tls"]["certfile"] == "/certs/client.crt"
        assert config["mqtt"]["tls"]["keyfile"] == "/certs/client.key"
        assert config["mqtt"]["tls"]["insecure"] is False

        # LWT
        assert config["mqtt"]["lwt"]["topic"] == "office-board/status"
        assert config["mqtt"]["lwt"]["payload"] == "offline"
        assert config["mqtt"]["lwt"]["qos"] == 2
        assert config["mqtt"]["lwt"]["retain"] is True

        # HTTP
        assert config["http_port"] == 9000

        # Queue
        assert config["max_queue_size"] == 20


class TestConfigurationStructure:
    """Test configuration structure and keys."""

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_config_has_required_keys(self, mock_load_dotenv):
        """Test that configuration has all required keys."""
        config = load_config()

        # Top-level keys
        assert "vestaboard_api_key" in config
        assert "mqtt" in config
        assert "http_port" in config
        assert "max_queue_size" in config

        # MQTT required keys
        mqtt_required = ["host", "port", "topic_prefix", "client_id", "clean_session", "keepalive", "qos"]
        for key in mqtt_required:
            assert key in config["mqtt"]

    @patch('src.main.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_config_types_are_correct(self, mock_load_dotenv):
        """Test that configuration values have correct types."""
        config = load_config()

        # String types
        assert isinstance(config["mqtt"]["host"], str)
        assert isinstance(config["mqtt"]["topic_prefix"], str)
        assert isinstance(config["mqtt"]["client_id"], str)

        # Integer types
        assert isinstance(config["mqtt"]["port"], int)
        assert isinstance(config["mqtt"]["keepalive"], int)
        assert isinstance(config["mqtt"]["qos"], int)
        assert isinstance(config["http_port"], int)
        assert isinstance(config["max_queue_size"], int)

        # Boolean types
        assert isinstance(config["mqtt"]["clean_session"], bool)


@pytest.mark.parametrize("env_var,config_key,default_value", [
    ("MQTT_BROKER_HOST", "host", "localhost"),
    ("MQTT_BROKER_PORT", "port", 1883),
    ("MQTT_TOPIC_PREFIX", "topic_prefix", "vestaboard"),
    ("MQTT_CLIENT_ID", "client_id", ""),
    ("MQTT_KEEPALIVE", "keepalive", 60),
    ("MQTT_QOS", "qos", 0),
])
def test_mqtt_defaults_parametrized(env_var, config_key, default_value):
    """Parametrized test for MQTT default values."""
    with patch('src.main.load_dotenv'):
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
            assert config["mqtt"][config_key] == default_value


class TestDotenvLoading:
    """Test .env file loading."""

    @patch('src.main.load_dotenv')
    def test_load_dotenv_is_called(self, mock_load_dotenv):
        """Test that load_dotenv is called during configuration loading."""
        with patch.dict(os.environ, {}, clear=True):
            load_config()
            mock_load_dotenv.assert_called_once()
