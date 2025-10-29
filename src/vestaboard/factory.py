"""Factory function for creating Vestaboard clients."""

import logging
from typing import TYPE_CHECKING, Optional

from .base import BaseVestaboardClient
from .board_types import BoardType
from .cloud_client import VestaboardClient
from .local_client import LocalVestaboardClient

if TYPE_CHECKING:
    from ..config import VestaboardConfig


def create_vestaboard_client(
    api_key: Optional[str] = None,
    board_type: BoardType = BoardType.STANDARD,
    use_local_api: bool = False,
    local_host: str = "vestaboard.local",
    local_port: int = 7000,
    max_queue_size: int = 10,
    config: Optional["VestaboardConfig"] = None,
) -> BaseVestaboardClient:
    """Factory function to create appropriate Vestaboard client.

    All configuration is explicit - no environment variable reading.
    For environment-based configuration, use AppConfig.from_env() and pass
    config.vestaboard to this function.

    Args:
        api_key: API key (cloud or local), required unless config is provided
        board_type: BoardType enum (default: BoardType.STANDARD)
        use_local_api: If True, use Local API; if False, use Cloud API
        local_host: Hostname for Local API (default: vestaboard.local)
        local_port: Port for Local API (default: 7000)
        max_queue_size: Maximum queue size for rate limiting (default: 10)
        config: VestaboardConfig object (overrides other parameters if provided)

    Returns:
        VestaboardClient or LocalVestaboardClient instance

    Raises:
        ValueError: If required parameters are missing

    Examples:
        >>> # Standard Vestaboard with Cloud API
        >>> client = create_vestaboard_client(api_key="...")

        >>> # Vestaboard Note with Local API
        >>> client = create_vestaboard_client(
        ...     api_key="...",
        ...     board_type=BoardType.NOTE,
        ...     use_local_api=True,
        ...     local_host="192.168.1.100"
        ... )

        >>> # Using config object from environment
        >>> from config import AppConfig
        >>> app_config = AppConfig.from_env()
        >>> client = create_vestaboard_client(config=app_config.vestaboard)
    """
    logger = logging.getLogger(__name__)

    if config is not None:
        if config.use_local_api and config.local_api_key:
            api_key = config.local_api_key
        elif config.api_key:
            api_key = config.api_key
        elif config.local_api_key:
            api_key = config.local_api_key
        else:
            raise ValueError("No API key found in VestaboardConfig")

        board_type = BoardType.from_string(config.board_type)

        use_local_api = config.use_local_api or bool(config.local_api_key and not config.api_key)
        local_host = config.local_host
        local_port = config.local_port
        max_queue_size = config.max_queue_size

    if not api_key:
        raise ValueError("api_key is required")

    if use_local_api:
        logger.info(f"Creating Local API client for {local_host}:{local_port}")
        return LocalVestaboardClient(
            api_key=api_key,
            board_type=board_type,
            host=local_host,
            port=local_port,
            max_queue_size=max_queue_size,
        )
    else:
        logger.info("Creating Cloud API client")
        return VestaboardClient(
            api_key=api_key, board_type=board_type, max_queue_size=max_queue_size
        )
