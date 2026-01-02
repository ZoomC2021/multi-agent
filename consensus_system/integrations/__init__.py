"""
External CLI Integrations for Consensus System.

Provides wrappers for external AI coding CLIs (Claude Code, Codex, Gemini, Cursor, OpenCode)
that can be used as agents in the consensus system.

All integrations follow fail-fast design: they raise errors immediately if
required CLIs or API keys are missing.

Example:
    from consensus_system.integrations import ClaudeCodeIntegration, get_available_integrations

    # Check what's available
    available = get_available_integrations()
    print(available)  # {"claude": True, "codex": False, ...}

    # Use an integration (will raise if not available)
    claude = ClaudeCodeIntegration(workspace="/my/project")
    result = await claude.execute("Find bugs in main.py")
"""

import os
import shutil
from typing import Dict, Optional, Type

from .base import (
    ExternalCLIIntegration,
    CLINotFoundError,
    APIKeyMissingError,
)
from .claude_code import ClaudeCodeIntegration
from .codex_cli import CodexCLIIntegration
from .gemini_cli import GeminiCLIIntegration
from .cursor_cli import CursorCLIIntegration
from .opencode_cli import OpenCodeCLIIntegration
from .amp_cli import AmpCLIIntegration


__all__ = [
    # Base
    "ExternalCLIIntegration",
    "CLINotFoundError",
    "APIKeyMissingError",
    # Integrations
    "ClaudeCodeIntegration",
    "CodexCLIIntegration",
    "GeminiCLIIntegration",
    "CursorCLIIntegration",
    "OpenCodeCLIIntegration",
    "AmpCLIIntegration",
    # Utilities
    "get_available_integrations",
    "get_integration_class",
    "INTEGRATION_REGISTRY",
]


# Registry mapping CLI names to integration classes
INTEGRATION_REGISTRY: Dict[str, Type[ExternalCLIIntegration]] = {
    "claude": ClaudeCodeIntegration,
    "codex": CodexCLIIntegration,
    "gemini": GeminiCLIIntegration,
    "cursor": CursorCLIIntegration,
    "opencode": OpenCodeCLIIntegration,
    "amp": AmpCLIIntegration,
}


def get_available_integrations() -> Dict[str, Dict[str, bool]]:
    """
    Check which CLI integrations are available on the system.

    Returns:
        Dictionary mapping CLI names to their availability status:
        {
            "claude": {"cli_available": True, "api_key_set": True},
            "codex": {"cli_available": False, "api_key_set": False},
            ...
        }
    """
    result = {}

    for name, cls in INTEGRATION_REGISTRY.items():
        cli_available = shutil.which(cls.CLI_NAME) is not None
        api_key_set = cls.API_KEY_ENV_VAR is None or bool(os.getenv(cls.API_KEY_ENV_VAR))

        result[name] = {
            "cli_available": cli_available,
            "api_key_set": api_key_set,
            "ready": cli_available and api_key_set,
        }

    return result


def get_integration_class(name: str) -> Optional[Type[ExternalCLIIntegration]]:
    """
    Get the integration class for a given CLI name.

    Args:
        name: CLI name (claude, codex, gemini, cursor, opencode)

    Returns:
        Integration class, or None if not found
    """
    return INTEGRATION_REGISTRY.get(name.lower())
