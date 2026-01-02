"""
Multi-Agent Consensus System

A PraisonAI-based multi-agent iterative consensus system for coding CLIs.
"""

__version__ = "0.1.0"

from consensus_system.agent import ConsensusAgent
from consensus_system.manager import ConsensusManager
from consensus_system.external_agent import ExternalCLIConsensusAgent, create_external_cli_agents
from consensus_system.praison_integration import PraisonConsensusAgent
from consensus_system.integrations import (
    get_available_integrations,
    ClaudeCodeIntegration,
    CodexCLIIntegration,
    GeminiCLIIntegration,
    CursorCLIIntegration,
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
    "PraisonConsensusAgent",
    "create_external_cli_agents",
    "get_available_integrations",
    "ClaudeCodeIntegration",
    "CodexCLIIntegration",
    "GeminiCLIIntegration",
    "CursorCLIIntegration",
]
