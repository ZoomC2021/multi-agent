"""
Configuration Module

Handles loading and parsing configuration files for the multi-agent system.
"""

import yaml
from typing import Dict, List, Any
from pathlib import Path


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Parsed configuration dictionary
    """
    config_file = Path(config_path)
    
    if not config_file.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
        
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
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a dictionary")
        
    # Validate agents section
    if 'agents' not in config:
        raise ValueError("Configuration must include 'agents' section")
        
    if not isinstance(config['agents'], list):
        raise ValueError("'agents' must be a list")
        
    for i, agent in enumerate(config['agents']):
        if not isinstance(agent, dict):
            raise ValueError(f"Agent {i} must be a dictionary")
            
        required_fields = ['name', 'role', 'instructions']
        for field in required_fields:
            if field not in agent:
                raise ValueError(f"Agent {i} missing required field: {field}")
                
    # Set defaults for optional sections
    if 'consensus' not in config:
        config['consensus'] = {}
        
    consensus = config['consensus']
    consensus.setdefault('max_iterations', 10)
    consensus.setdefault('convergence_threshold', 0.01)
    consensus.setdefault('strategy', 'average')
    consensus.setdefault('topology', 'fully_connected')
    
    if 'workflow' not in config:
        config['workflow'] = {}
        
    workflow = config['workflow']
    workflow.setdefault('mode', 'sequential')
    
    return config


def create_default_config() -> Dict[str, Any]:
    """
    Create a default configuration for coding agents.
    
    Returns:
        Default configuration dictionary
    """
    return {
        'agents': [
            {
                'name': 'code_analyzer',
                'role': 'CodeAnalyzer',
                'instructions': 'Analyze code for quality, patterns, and potential issues.',
                'llm': 'gpt-4',
                'initial_value': 0.0
            },
            {
                'name': 'code_reviewer',
                'role': 'CodeReviewer',
                'instructions': 'Review code for best practices, security, and maintainability.',
                'llm': 'gpt-4',
                'initial_value': 0.0
            },
            {
                'name': 'code_optimizer',
                'role': 'CodeOptimizer',
                'instructions': 'Suggest optimizations and improvements for code efficiency.',
                'llm': 'gpt-4',
                'initial_value': 0.0
            }
        ],
        'consensus': {
            'max_iterations': 10,
            'convergence_threshold': 0.01,
            'strategy': 'average',
            'topology': 'fully_connected'
        },
        'workflow': {
            'mode': 'collaborative',
            'headless': True
        }
    }


def save_config(config: Dict[str, Any], output_path: str):
    """
    Save configuration to a YAML file.
    
    Args:
        config: Configuration dictionary
        output_path: Path to save the configuration
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
