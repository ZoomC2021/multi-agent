"""
Multi-Agent Consensus System

A PraisonAI-based multi-agent iterative consensus system for coding CLIs.
"""

__version__ = "0.1.0"

from consensus_system.agent import ConsensusAgent
from consensus_system.manager import ConsensusManager
from consensus_system.config import load_config

__all__ = ["ConsensusAgent", "ConsensusManager", "load_config"]
