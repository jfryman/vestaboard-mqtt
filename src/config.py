"""Configuration models using Pydantic for type safety and validation."""

import os
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from dotenv import load_dotenv


class TLSConfig(BaseModel):
    """TLS/SSL configuration for MQTT connection."""

    enabled: bool = True
    ca_certs: Optional[str] = Field(None, description="Path to CA certificate file")
    certfile: Optional[str] = Field(None, description="Path to client certificate file")
    keyfile: Optional[str] = Field(None, description="Path to client key file")
    insecure: bool = Field(False, description="Skip certificate verification (INSECURE)")

    @field_validator('ca_certs', 'certfile', 'keyfile')
    @classmethod
    def validate_cert_paths(cls, v: Optional[str]) -> Optional[str]:
        """Validate that certificate paths exist if provided."""
        if v and not os.path.exists(v):
            raise ValueError(f"Certificate file not found: {v}")
        return v

    @model_validator(mode='after')
    def validate_tls_config(self) -> 'TLSConfig':
        """Validate TLS configuration consistency."""
        if self.enabled and not self.ca_certs:
            raise ValueError("ca_certs is required when TLS is enabled")

        # Mutual TLS requires both cert and key
        if self.certfile and not self.keyfile:
            raise ValueError("keyfile is required when certfile is provided")
        if self.keyfile and not self.certfile:
            raise ValueError("certfile is required when keyfile is provided")

        return self


class LWTConfig(BaseModel):
    """Last Will and Testament configuration for MQTT."""

    topic: str = Field(..., description="LWT topic")
    payload: str = Field("offline", description="LWT payload")
    qos: int = Field(0, ge=0, le=2, description="LWT QoS level (0-2)")
    retain: bool = Field(True, description="LWT retain flag")


class MQTTConfig(BaseModel):
    """MQTT broker configuration."""

    host: str = Field("localhost", description="MQTT broker hostname")
    port: int = Field(1883, ge=1, le=65535, description="MQTT broker port")
    username: Optional[str] = Field(None, description="MQTT username")
    password: Optional[str] = Field(None, description="MQTT password")
    topic_prefix: str = Field("vestaboard", description="Topic prefix for all MQTT topics")
    client_id: str = Field("", description="MQTT client ID (auto-generated if empty)")
    clean_session: bool = Field(True, description="Clean session flag")
    keepalive: int = Field(60, ge=1, description="Keep-alive interval in seconds")
    qos: int = Field(0, ge=0, le=2, description="Default QoS level (0-2)")
    tls: Optional[TLSConfig] = Field(None, description="TLS/SSL configuration")
    lwt: Optional[LWTConfig] = Field(None, description="Last Will and Testament configuration")


class VestaboardConfig(BaseModel):
    """Vestaboard API configuration."""

    api_key: Optional[str] = Field(None, description="Vestaboard Cloud API key")
    local_api_key: Optional[str] = Field(None, description="Vestaboard Local API key")
    use_local_api: bool = Field(False, description="Use Local API instead of Cloud API")
    local_host: str = Field("vestaboard.local", description="Local API hostname")
    local_port: int = Field(7000, ge=1, le=65535, description="Local API port")
    board_type: str = Field("standard", description="Board type: 'standard' or 'note'")
    max_queue_size: int = Field(10, ge=1, description="Maximum message queue size")

    @field_validator('board_type')
    @classmethod
    def validate_board_type(cls, v: str) -> str:
        """Validate board type is 'standard' or 'note'."""
        v_lower = v.lower().strip()

        if v_lower in ("standard", "note", ""):
            return v

        raise ValueError(f"Unknown board_type: '{v}'. Valid options: 'standard' or 'note'")

    @model_validator(mode='after')
    def validate_api_key(self) -> 'VestaboardConfig':
        """Validate that at least one API key is provided."""
        if not self.api_key and not self.local_api_key:
            raise ValueError("Either api_key or local_api_key must be provided")
        return self


class AppConfig(BaseModel):
    """Main application configuration."""

    vestaboard: VestaboardConfig = Field(..., description="Vestaboard configuration")
    mqtt: MQTTConfig = Field(default_factory=MQTTConfig, description="MQTT configuration")
    http_port: int = Field(8000, ge=1, le=65535, description="HTTP API port")
    log_level: str = Field("INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")

    # Deprecated - kept for backward compatibility, use vestaboard.max_queue_size instead
    max_queue_size: Optional[int] = Field(None, ge=1, description="Maximum message queue size (deprecated)")

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level."""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        v_upper = v.upper().strip()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log_level: '{v}'. Valid options: {', '.join(sorted(valid_levels))}")
        return v_upper

    @property
    def effective_max_queue_size(self) -> int:
        """Get effective max queue size, preferring vestaboard config."""
        return self.max_queue_size or self.vestaboard.max_queue_size

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Load configuration from environment variables."""
        load_dotenv()

        # Helper function to parse boolean environment variables
        def parse_bool(value: Optional[str], default: bool = False) -> bool:
            if value is None:
                return default
            return value.lower() in ('true', '1', 'yes', 'on')

        # Build TLS configuration if enabled
        tls_config = None
        if parse_bool(os.getenv("MQTT_TLS_ENABLED")):
            tls_config = TLSConfig(
                enabled=True,
                ca_certs=os.getenv("MQTT_TLS_CA_CERTS"),
                certfile=os.getenv("MQTT_TLS_CERTFILE"),
                keyfile=os.getenv("MQTT_TLS_KEYFILE"),
                insecure=parse_bool(os.getenv("MQTT_TLS_INSECURE"), False)
            )

        # Build LWT configuration if topic is specified
        lwt_config = None
        lwt_topic = os.getenv("MQTT_LWT_TOPIC")
        if lwt_topic:
            lwt_config = LWTConfig(
                topic=lwt_topic,
                payload=os.getenv("MQTT_LWT_PAYLOAD", "offline"),
                qos=int(os.getenv("MQTT_LWT_QOS", "0")),
                retain=parse_bool(os.getenv("MQTT_LWT_RETAIN"), True)
            )

        # Build MQTT configuration
        mqtt_config = MQTTConfig(
            host=os.getenv("MQTT_BROKER_HOST", "localhost"),
            port=int(os.getenv("MQTT_BROKER_PORT", "1883")),
            username=os.getenv("MQTT_USERNAME"),
            password=os.getenv("MQTT_PASSWORD"),
            topic_prefix=os.getenv("MQTT_TOPIC_PREFIX", "vestaboard"),
            client_id=os.getenv("MQTT_CLIENT_ID", ""),
            clean_session=parse_bool(os.getenv("MQTT_CLEAN_SESSION"), True),
            keepalive=int(os.getenv("MQTT_KEEPALIVE", "60")),
            qos=int(os.getenv("MQTT_QOS", "0")),
            tls=tls_config,
            lwt=lwt_config
        )

        # Build Vestaboard configuration
        vestaboard_config = VestaboardConfig(
            api_key=os.getenv("VESTABOARD_API_KEY"),
            local_api_key=os.getenv("VESTABOARD_LOCAL_API_KEY"),
            use_local_api=parse_bool(os.getenv("USE_LOCAL_API"), False),
            local_host=os.getenv("VESTABOARD_LOCAL_HOST", "vestaboard.local"),
            local_port=int(os.getenv("VESTABOARD_LOCAL_PORT", "7000")),
            board_type=os.getenv("VESTABOARD_BOARD_TYPE", "standard"),
            max_queue_size=int(os.getenv("MAX_QUEUE_SIZE", "10"))
        )

        # Build main application configuration
        return cls(
            vestaboard=vestaboard_config,
            mqtt=mqtt_config,
            http_port=int(os.getenv("HTTP_PORT", "8000")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_queue_size=int(os.getenv("MAX_QUEUE_SIZE", "10"))
        )
