"""
Command Line Interface Module

Provides CLI for running the multi-agent consensus system in headless mode.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from consensus_system.agent import ConsensusAgent
from consensus_system.manager import ConsensusManager
from consensus_system.config import load_config, create_default_config, save_config


def create_agents_from_config(config: dict) -> list:
    """
    Create ConsensusAgent instances from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of ConsensusAgent instances
    """
    agents = []
    
    for agent_config in config['agents']:
        agent = ConsensusAgent(
            agent_id=agent_config['name'],
            role=agent_config['role'],
            instructions=agent_config['instructions'],
            initial_value=agent_config.get('initial_value', 0.0),
            llm=agent_config.get('llm', 'gpt-4'),
            verbose=True
        )
        agents.append(agent)
        
    return agents


def run_consensus_system(
    config_path: Optional[str] = None,
    task: Optional[str] = None,
    output: Optional[str] = None,
    headless: bool = True
):
    """
    Run the consensus system with given configuration.
    
    Args:
        config_path: Path to configuration file
        task: Optional task to execute
        output: Optional output file for results
        headless: Run in headless mode (no interactive prompts)
    """
    # Load or create configuration
    if config_path:
        print(f"Loading configuration from: {config_path}")
        config = load_config(config_path)
    else:
        print("Using default configuration")
        config = create_default_config()
        
    # Create agents
    print(f"\nCreating {len(config['agents'])} agents...")
    agents = create_agents_from_config(config)
    
    for agent in agents:
        print(f"  - {agent.role} ({agent.agent_id})")
        
    # Create consensus manager
    consensus_config = config.get('consensus', {})
    manager = ConsensusManager(
        agents=agents,
        max_iterations=consensus_config.get('max_iterations', 10),
        convergence_threshold=consensus_config.get('convergence_threshold', 0.01),
        verbose=True
    )
    
    # Setup network topology
    topology = consensus_config.get('topology', 'fully_connected')
    print(f"\nSetting up network topology: {topology}")
    manager.setup_network(topology=topology)
    
    # Execute task if provided
    if task:
        print(f"\n{'='*60}")
        print(f"Executing collaborative task...")
        print(f"{'='*60}")
        
        result = manager.execute_collaborative_task(
            task=task,
            consensus_strategy=consensus_config.get('strategy', 'majority')
        )
        
        print(f"\n{'='*60}")
        print(f"Task Results")
        print(f"{'='*60}")
        print(f"Task: {result['task']}")
        print(f"Consensus achieved: {result['consensus']['converged']}")
        print(f"Iterations: {result['consensus']['iterations']}")
        print(f"Final decision: {result['final_decision']}")
        
        # Save results if output path provided
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2, default=str)
                
            print(f"\nResults saved to: {output}")
            
        return result
    else:
        # Run basic consensus demonstration
        print(f"\n{'='*60}")
        print(f"Running consensus demonstration...")
        print(f"{'='*60}")
        
        # Set some initial values
        import random
        for agent in agents:
            agent.value = random.uniform(1.0, 10.0)
            
        print("\nInitial values:")
        for agent in agents:
            print(f"  {agent.role}: {agent.value:.2f}")
            
        # Run consensus
        result = manager.run_consensus(
            strategy=consensus_config.get('strategy', 'average')
        )
        
        print(f"\n{'='*60}")
        print(f"Consensus Results")
        print(f"{'='*60}")
        print(f"Converged: {result['converged']}")
        print(f"Iterations: {result['iterations']}")
        print(f"Consensus value: {result['consensus_value']:.2f}")
        
        print("\nFinal values:")
        for agent_id, value in result['final_values'].items():
            print(f"  {agent_id}: {value:.2f}")
            
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2, default=str)
                
            print(f"\nResults saved to: {output}")
            
        return result


def init_config(output_path: str):
    """
    Initialize a default configuration file.
    
    Args:
        output_path: Path to save the configuration
    """
    config = create_default_config()
    save_config(config, output_path)
    print(f"Default configuration saved to: {output_path}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PraisonAI Multi-Agent Iterative Consensus System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default configuration
  consensus-cli run
  
  # Run with custom configuration
  consensus-cli run --config agents.yaml
  
  # Execute a specific task
  consensus-cli run --task "Analyze the code quality of module X"
  
  # Save results to file
  consensus-cli run --task "Review security practices" --output results.json
  
  # Initialize default configuration
  consensus-cli init --output agents.yaml
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run the consensus system')
    run_parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration YAML file'
    )
    run_parser.add_argument(
        '--task', '-t',
        type=str,
        help='Task to execute collaboratively'
    )
    run_parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file for results (JSON)'
    )
    run_parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive mode (not headless)'
    )
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize default configuration')
    init_parser.add_argument(
        '--output', '-o',
        type=str,
        default='agents.yaml',
        help='Output path for configuration file (default: agents.yaml)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
        
    try:
        if args.command == 'run':
            run_consensus_system(
                config_path=args.config,
                task=args.task,
                output=args.output,
                headless=not args.interactive
            )
        elif args.command == 'init':
            init_config(args.output)
            
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if '--verbose' in sys.argv:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
