"""
Multi-Agent Consensus System

A multi-agent iterative consensus system for coding CLIs powered by LiteLLM.
"""

__version__ = "0.1.0"

from consensus_system.agent import ConsensusAgent
from consensus_system.manager import ConsensusManager
from consensus_system.external_agent import ExternalCLIConsensusAgent, create_external_cli_agents
from consensus_system.litellm_agent import LiteLLMAgent, create_litellm_agents_from_config
from consensus_system.integrations import (
    get_available_integrations,
    ClaudeCodeIntegration,
    CodexCLIIntegration,
    GeminiCLIIntegration,
    CursorCLIIntegration,
    QwenCLIIntegration,
)


def load_config(path: str):
    """Lazy import to avoid yaml dependency at module load time."""
    from consensus_system.config import load_config as _load_config

    return _load_config(path)


__all__ = [
    "ConsensusAgent",
    "ConsensusManager",
    "load_config",
    "ExternalCLIConsensusAgent",
    "LiteLLMAgent",
    "create_external_cli_agents",
    "create_litellm_agents_from_config",
    "get_available_integrations",
    "ClaudeCodeIntegration",
    "CodexCLIIntegration",
    "GeminiCLIIntegration",
    "CursorCLIIntegration",
    "QwenCLIIntegration",
]
