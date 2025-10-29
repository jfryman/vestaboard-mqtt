"""Vestaboard client library for Cloud and Local API interactions.

This package provides a unified interface for interacting with Vestaboard displays
via both the Cloud Read/Write API and Local API.
"""

from .base import BaseVestaboardClient, RateLimitMixin
from .board_types import BoardType
from .cloud_client import VestaboardClient
from .constants import CHAR_CODE_MAP, TEXT_TO_CODE_MAP
from .factory import create_vestaboard_client
from .local_client import LocalVestaboardClient
from .utils import debug_layout_preview, text_to_layout

__all__ = [
    # Base classes
    "BaseVestaboardClient",
    "RateLimitMixin",
    # Board types
    "BoardType",
    # Client implementations
    "VestaboardClient",
    "LocalVestaboardClient",
    # Factory
    "create_vestaboard_client",
    # Constants
    "CHAR_CODE_MAP",
    "TEXT_TO_CODE_MAP",
    # Utilities
    "debug_layout_preview",
    "text_to_layout",
]
