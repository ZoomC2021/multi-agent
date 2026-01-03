"""
Configuration Module

Handles loading and parsing configuration files for the multi-agent system.
"""

import yaml
import copy
from typing import Dict, Any
from pathlib import Path


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Parsed configuration dictionary

    Raises:
        FileNotFoundError: If configuration file is not found
        ValueError: If configuration is invalid or YAML parsing fails
    """
    config_file = Path(config_path).resolve()

    if not config_file.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML configuration: {e}")

    if config is None:
        raise ValueError(f"Configuration file is empty: {config_path}")

    return validate_config(config)


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the configuration structure.

    Args:
        config: Configuration dictionary

    Returns:
        Validated configuration

    Raises:
        ValueError: If configuration is invalid
    """
    # Create a deep copy to avoid in-place mutation of the input
    config = copy.deepcopy(config)

    if not isinstance(config, dict):
        raise ValueError("Configuration must be a dictionary")

    # Validate agents section
    if "agents" not in config:
        raise ValueError("Configuration must include 'agents' section")

    if not isinstance(config["agents"], list):
        raise ValueError("'agents' must be a list")

    if len(config["agents"]) == 0:
        raise ValueError("'agents' list must not be empty")

    seen_names = set()
    for i, agent in enumerate(config["agents"]):
        if not isinstance(agent, dict):
            raise ValueError(f"Agent {i} must be a dictionary")

        required_fields = ["name", "role", "instructions"]
        for field in required_fields:
            if field not in agent:
                raise ValueError(f"Agent {i} missing required field: {field}")
            if not isinstance(agent[field], str):
                raise ValueError(f"Agent {i} field '{field}' must be a string")
            if not agent[field].strip():
                raise ValueError(f"Agent {i} field '{field}' cannot be empty")

        # Check for duplicate agent names
        agent_name = agent["name"]
        if agent_name in seen_names:
            raise ValueError(f"Duplicate agent name detected: '{agent_name}'")
        seen_names.add(agent_name)

        # Set defaults for optional agent fields
        agent.setdefault("llm", "gpt-4")
        agent.setdefault("initial_value", 0.0)

        # Validate initial_value type if provided
        if "initial_value" in agent:
            val = agent["initial_value"]
            # Only force numeric for average/weighted strategies
            strategy = config.get("consensus", {}).get("strategy", "average")
            if strategy in ["average", "weighted"]:
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                     raise ValueError(f"Agent {i} 'initial_value' must be a non-boolean number for '{strategy}' strategy")

        # Validate weight if present (for weighted consensus strategy)
        if "weight" in agent:
            if not isinstance(agent["weight"], (int, float)):
                raise ValueError(f"Agent {i} 'weight' must be a number")
            if agent["weight"] < 0:
                raise ValueError(f"Agent {i} 'weight' must be non-negative")

    # Validate and set defaults for consensus section
    # Handle case where key exists but value is None (empty section in YAML)
    if config.get("consensus") is None:
        config["consensus"] = {}

    consensus = config["consensus"]
    if not isinstance(consensus, dict):
        raise ValueError("'consensus' section must be a dictionary")

    consensus.setdefault("max_iterations", 10)
    consensus.setdefault("convergence_threshold", 0.01)
    consensus.setdefault("strategy", "average")
    consensus.setdefault("topology", "fully_connected")

    # Validate consensus values
    if not isinstance(consensus["max_iterations"], int) or consensus["max_iterations"] <= 0:
        raise ValueError("'max_iterations' must be a positive integer")

    if (
        not isinstance(consensus["convergence_threshold"], (int, float))
        or consensus["convergence_threshold"] <= 1e-6
    ):
        raise ValueError("'convergence_threshold' must be a positive number")

    valid_strategies = ["average", "majority", "weighted"]
    if consensus["strategy"] not in valid_strategies:
        raise ValueError(
            f"Invalid strategy '{consensus['strategy']}'. Must be one of: {valid_strategies}"
        )

    valid_topologies = ["fully_connected", "ring", "chain"]
    if consensus["topology"] not in valid_topologies:
        raise ValueError(
            f"Invalid topology '{consensus['topology']}'. Must be one of: {valid_topologies}"
        )

    # Validate and set defaults for workflow section
    if config.get("workflow") is None:
        config["workflow"] = {}

    workflow = config["workflow"]
    if not isinstance(workflow, dict):
        raise ValueError("'workflow' section must be a dictionary")

    workflow.setdefault("mode", "collaborative")
    workflow.setdefault("headless", True)

    valid_modes = ["sequential", "collaborative", "parallel"]
    if workflow["mode"] not in valid_modes:
        raise ValueError(
            f"Invalid workflow mode '{workflow['mode']}'. Must be one of: {valid_modes}"
        )

    return config


def create_default_config() -> Dict[str, Any]:
    """
    Create a default configuration for coding agents.

    Returns:
        Default configuration dictionary
    """
    return {
        "agents": [
            {
                "name": "code_analyzer",
                "role": "CodeAnalyzer",
                "instructions": "Analyze code for quality, patterns, and potential issues.",
                "llm": "gpt-4",
                "initial_value": 0.0,
            },
            {
                "name": "code_reviewer",
                "role": "CodeReviewer",
                "instructions": "Review code for best practices, security, and maintainability.",
                "llm": "gpt-4",
                "initial_value": 0.0,
            },
            {
                "name": "code_optimizer",
                "role": "CodeOptimizer",
                "instructions": "Suggest optimizations and improvements for code efficiency.",
                "llm": "gpt-4",
                "initial_value": 0.0,
            },
        ],
        "consensus": {
            "max_iterations": 10,
            "convergence_threshold": 0.01,
            "strategy": "average",
            "topology": "fully_connected",
        },
        "workflow": {"mode": "collaborative", "headless": True},
    }


def save_config(config: Dict[str, Any], output_path: str) -> None:
    """
    Save configuration to a YAML file.

    Args:
        config: Configuration dictionary
        output_path: Path to save the configuration

    Raises:
        IOError: If file cannot be written
    """
    output_file = Path(output_path).resolve()
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    except IOError as e:
        raise IOError(f"Failed to save configuration to {output_path}: {e}")
