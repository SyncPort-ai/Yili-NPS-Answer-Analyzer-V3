"""
Configuration management for NPS V3 API.
"""

from .settings import Settings, get_settings
from .constants import *

__all__ = [
    "Settings",
    "get_settings",
    "FOUNDATION_AGENTS",
    "ANALYSIS_AGENTS",
    "CONSULTING_AGENTS",
    "DEFAULT_MEMORY_LIMITS",
    "DEFAULT_TIMEOUT_SECONDS"
]