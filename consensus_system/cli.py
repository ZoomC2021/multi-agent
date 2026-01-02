"""
Command Line Interface Module

Provides CLI for running the multi-agent consensus system in headless mode.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is optional

from consensus_system.agent import ConsensusAgent
from consensus_system.manager import ConsensusManager
from consensus_system.config import load_config, create_default_config, save_config
from consensus_system.external_agent import create_external_cli_agents
from consensus_system.integrations import (
    get_available_integrations,
    CLINotFoundError,
    APIKeyMissingError,
)


def create_agents_from_config(config: dict) -> list:
    """
    Create ConsensusAgent instances from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        List of ConsensusAgent instances
    """
    agents = []

    # Use config.get() to handle missing agents key gracefully
    agent_configs = config.get("agents", [])

    for agent_config in agent_configs:
        agent = ConsensusAgent(
            agent_id=agent_config.get("name", "unknown"),
            role=agent_config.get("role", "Agent"),
            instructions=agent_config.get("instructions", ""),
            initial_value=agent_config.get("initial_value", 0.0),
            llm=agent_config.get("llm", "gpt-4"),
            verbose=agent_config.get("verbose", True),
        )
        agents.append(agent)

    return agents


def run_consensus_system(
    config_path: Optional[str] = None,
    task: Optional[str] = None,
    output: Optional[str] = None,
    headless: bool = True,
    seed: Optional[int] = None,
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
    agent_configs = config.get("agents", [])
    print(f"\nCreating {len(agent_configs)} agents...")
    agents = create_agents_from_config(config)

    for agent in agents:
        print(f"  - {agent.role} ({agent.agent_id})")

    # Create consensus manager
    consensus_config = config.get("consensus", {})
    manager = ConsensusManager(
        agents=agents,
        max_iterations=consensus_config.get("max_iterations", 10),
        convergence_threshold=consensus_config.get("convergence_threshold", 0.01),
        verbose=True,
    )

    # Setup network topology
    topology = consensus_config.get("topology", "fully_connected")
    print(f"\nSetting up network topology: {topology}")
    manager.setup_network(topology=topology)

    # Execute task if provided
    if task:
        print(f"\n{'=' * 60}")
        print("Executing collaborative task...")
        print(f"{'=' * 60}")

        result = manager.execute_collaborative_task(
            task=task, consensus_strategy=consensus_config.get("strategy", "majority")
        )

        print(f"\n{'=' * 60}")
        print("Task Results")
        print(f"{'=' * 60}")
        print(f"Task: {result.get('task', 'N/A')}")

        consensus_data = result.get("consensus", {})
        print(f"Consensus achieved: {consensus_data.get('converged', False)}")
        print(f"Iterations: {consensus_data.get('iterations', 0)}")
        print(f"Final decision: {result.get('final_decision', 'N/A')}")

        # Save results if output path provided
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(result, f, indent=2, default=str)

            print(f"\nResults saved to: {output}")

        return result
    else:
        # Run basic consensus demonstration
        print(f"\n{'=' * 60}")
        print("Running consensus demonstration...")
        print(f"{'=' * 60}")

        # Set some initial values
        # Set some initial values
        import random

        if seed is not None:
            random.seed(seed)

        for agent in agents:
            agent.value = random.uniform(1.0, 10.0)

        print("\nInitial values:")
        for agent in agents:
            if isinstance(agent.value, (int, float)):
                print(f"  {agent.role}: {agent.value:.2f}")
            else:
                print(f"  {agent.role}: {agent.value}")

        # Run consensus
        result = manager.run_consensus(strategy=consensus_config.get("strategy", "average"))

        print(f"\n{'=' * 60}")
        print("Consensus Results")
        print(f"{'=' * 60}")
        print(f"Converged: {result['converged']}")
        print(f"Iterations: {result['iterations']}")
        print(f"Consensus value: {result['consensus_value']}")

        print("\nFinal values:")
        for agent_id, value in result["final_values"].items():
            if isinstance(value, (int, float)):
                print(f"  {agent_id}: {value:.2f}")
            else:
                print(f"  {agent_id}: {value}")

        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
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


def run_external_consensus(
    external_agents: list,
    task: str,
    output: Optional[str] = None,
    workspace: str = ".",
    verbose: bool = False,
):
    """
    Run consensus with external CLI agents (Claude, Codex, Gemini, Cursor).

    Args:
        external_agents: List of CLI types to use (claude, codex, gemini, cursor)
        task: Task to execute
        output: Optional output file for results
        workspace: Working directory for CLIs
        verbose: Enable verbose output

    Raises:
        CLINotFoundError: If any CLI is not installed
        APIKeyMissingError: If required API keys are missing
    """

    print(f"\n{'=' * 60}")
    print("External CLI Consensus")
    print(f"{'=' * 60}")

    # Check availability first
    available = get_available_integrations()
    print("\nCLI Availability:")
    for cli_name in external_agents:
        status = available.get(cli_name, {})
        cli_ok = status.get("cli_available", False)
        key_ok = status.get("api_key_set", False)
        ready = status.get("ready", False)
        print(
            f"  {cli_name}: CLI={'✓' if cli_ok else '✗'} API_KEY={'✓' if key_ok else '✗'} Ready={'✓' if ready else '✗'}"
        )

    # Build instructions for bug/issue finding
    instructions = """
    You are a code analysis expert. Analyze the given code/files for:
    - Bugs and potential issues
    - Regressions or breaking changes
    - Security vulnerabilities
    - Performance problems
    - Code quality issues
    
    Provide a detailed analysis with specific line numbers and recommendations.
    """

    print(f"\nCreating {len(external_agents)} external CLI agents...")

    # Create agents - will fail fast if CLIs/keys missing
    agents = create_external_cli_agents(
        cli_types=external_agents,
        task_instructions=instructions,
        workspace=workspace,
        verbose=verbose,
    )

    for agent in agents:
        print(f"  - {agent.role} ({agent.cli_type})")

    # Create manager
    manager = ConsensusManager(
        agents=agents, max_iterations=5, convergence_threshold=0.1, verbose=verbose
    )
    manager.setup_network(topology="fully_connected")

    print(f"\nExecuting task: {task}")
    print(f"{'=' * 60}\n")

    # Execute collaborative task
    result = manager.execute_collaborative_task(task=task, consensus_strategy="majority")

    # Print results
    print(f"\n{'=' * 60}")
    print("Agent Results")
    print(f"{'=' * 60}")

    for agent_result in result.get("agent_results", []):
        role = agent_result.get("role", "Unknown")
        cli = agent_result.get("cli", "unknown")
        success = agent_result.get("success", False)
        response = str(agent_result.get("response", ""))[:500]

        print(f"\n[{role}] ({cli}) - {'SUCCESS' if success else 'FAILED'}")
        if success:
            print(f"{response}...")
        else:
            print(f"Error: {agent_result.get('error', 'Unknown error')}")

    consensus_data = result.get("consensus", {})
    print(f"\n{'=' * 60}")
    print("Consensus Result")
    print(f"{'=' * 60}")
    print(f"Converged: {consensus_data.get('converged', False)}")
    print(f"Iterations: {consensus_data.get('iterations', 0)}")
    print(f"Final decision score: {result.get('final_decision', 'N/A')}")

    # Save results
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, default=str)

        print(f"\nResults saved to: {output}")

    return result


def list_available_clis():
    """Print available CLI integrations."""
    print("\nAvailable CLI Integrations:")
    print(f"{'=' * 40}")

    available = get_available_integrations()

    for name, status in available.items():
        cli_ok = status.get("cli_available", False)
        ready = status.get("ready", False)

        status_str = "READY" if ready else ("CLI missing" if not cli_ok else "API key missing")
        icon = "✓" if ready else "✗"

        print(f"  {icon} {name}: {status_str}")

    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Iterative Consensus System (Powered by LiteLLM)",
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
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the consensus system")
    run_parser.add_argument("--config", "-c", type=str, help="Path to configuration YAML file")
    run_parser.add_argument("--task", "-t", type=str, help="Task to execute collaboratively")
    run_parser.add_argument("--output", "-o", type=str, help="Output file for results (JSON)")
    run_parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode (not headless)"
    )
    run_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output with detailed logging"
    )
    run_parser.add_argument(
        "--external-agent",
        "-e",
        type=str,
        action="append",
        choices=["claude", "codex", "gemini", "cursor"],
        help="External CLI agent(s) to use (can specify multiple: -e claude -e codex)",
    )
    run_parser.add_argument(
        "--workspace", "-w", type=str, default=".", help="Working directory for external CLI agents"
    )
    run_parser.add_argument("--seed", "-s", type=int, help="Random seed for reproducibility")

    # List command
    subparsers.add_parser("list", help="List available CLI integrations")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize default configuration")
    init_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="agents.yaml",
        help="Output path for configuration file (default: agents.yaml)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "run":
            # Check if using external agents
            if args.external_agent:
                if not args.task:
                    print("Error: --task is required when using --external-agent", file=sys.stderr)
                    return 1
                run_external_consensus(
                    external_agents=args.external_agent,
                    task=args.task,
                    output=args.output,
                    workspace=args.workspace,
                    verbose=args.verbose,
                )
            else:
                run_consensus_system(
                    config_path=args.config,
                    task=args.task,
                    output=args.output,
                    headless=not args.interactive,
                    seed=args.seed,
                )
        elif args.command == "init":
            init_config(args.output)
        elif args.command == "list":
            list_available_clis()

        return 0

    except (CLINotFoundError, APIKeyMissingError) as e:
        print(f"\nConfiguration Error: {e}", file=sys.stderr)
        print("\nRun 'consensus-cli list' to see available CLI integrations.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if "--verbose" in sys.argv or (hasattr(args, "verbose") and args.verbose):
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
