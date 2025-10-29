"""State management for Vestaboard displays.

This package provides save/restore functionality for Vestaboard display states
using MQTT retained messages.
"""

from .manager import SaveData, SaveStateManager

__all__ = [
    "SaveStateManager",
    "SaveData",
]
