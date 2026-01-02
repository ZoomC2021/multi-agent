#!/usr/bin/env python3
"""
Bug Finder Example - Consensus-based Bug Detection

This example demonstrates using multiple AI coding CLIs (Claude, Codex, Gemini)
to find bugs through consensus. Each agent analyzes the same code and the system
reaches consensus on identified issues.

Usage:
    python examples/bug_finder_example.py /path/to/code/to/analyze

Requirements:
    - At least one CLI installed (claude, codex, gemini, or cursor)
    - Corresponding API keys set
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from consensus_system import (
    ConsensusManager,
    ExternalCLIConsensusAgent,
    create_external_cli_agents,
    get_available_integrations,
)


async def find_bugs_with_consensus(
    target_path: str,
    cli_types: list = None,
    verbose: bool = True
) -> dict:
    """
    Find bugs using consensus from multiple AI coding agents.
    
    Args:
        target_path: Path to file or directory to analyze
        cli_types: List of CLI types to use (auto-detect if None)
        verbose: Enable verbose output
        
    Returns:
        Consensus result dictionary
    """
    # Auto-detect available CLIs if not specified
    if cli_types is None:
        available = get_available_integrations()
        cli_types = [name for name, status in available.items() if status.get('ready')]
        
        if not cli_types:
            raise RuntimeError(
                "No CLI integrations available. Install at least one of: "
                "claude, codex, gemini, cursor"
            )
    
    print(f"Using CLIs: {', '.join(cli_types)}")
    print(f"Target: {target_path}")
    print()
    
    # Create task
    target = Path(target_path)
    if target.is_file():
        task = f"Analyze {target.name} for bugs, issues, and potential regressions"
    else:
        task = f"Analyze the codebase in {target} for bugs, issues, and potential regressions"
    
    # Bug finding instructions
    instructions = """
    You are a code analysis expert focused on finding bugs and issues.
    
    For each issue found, provide:
    1. File path and line number(s)
    2. Issue type (bug, security, performance, etc.)
    3. Severity (critical, high, medium, low)
    4. Description of the issue
    5. Recommended fix
    
    Be thorough but focus on real issues, not style preferences.
    """
    
    # Create agents
    agents = []
    for i, cli_type in enumerate(cli_types):
        agent = ExternalCLIConsensusAgent(
            agent_id=f"{cli_type}_bug_finder_{i}",
            role=f"{cli_type.capitalize()}BugFinder",
            instructions=instructions,
            cli_type=cli_type,
            workspace=str(target.parent if target.is_file() else target),
            initial_value=0.0,
            verbose=verbose
        )
        agents.append(agent)
        print(f"Created agent: {agent.role}")
    
    # Create consensus manager
    manager = ConsensusManager(
        agents=agents,
        max_iterations=5,
        convergence_threshold=0.1,
        verbose=verbose
    )
    manager.setup_network(topology='fully_connected')
    
    print(f"\nExecuting bug analysis with {len(agents)} agents...")
    print("=" * 60)
    
    # Run collaborative analysis
    result = manager.execute_collaborative_task(
        task=task,
        consensus_strategy='majority'
    )
    
    return result


def print_results(result: dict):
    """Print formatted bug finding results."""
    print("\n" + "=" * 60)
    print("BUG FINDING RESULTS")
    print("=" * 60)
    
    # Print each agent's findings
    for agent_result in result.get('agent_results', []):
        role = agent_result.get('role', 'Unknown')
        cli = agent_result.get('cli', 'unknown')
        success = agent_result.get('success', False)
        response = agent_result.get('response', '')
        
        print(f"\n--- {role} ({cli}) ---")
        if success:
            # Print first 1000 chars of response
            print(response[:1000] if len(response) > 1000 else response)
            if len(response) > 1000:
                print("... [truncated]")
        else:
            print(f"FAILED: {agent_result.get('error', 'Unknown error')}")
    
    # Print consensus
    consensus = result.get('consensus', {})
    print(f"\n{'=' * 60}")
    print("CONSENSUS")
    print(f"{'=' * 60}")
    print(f"Converged: {consensus.get('converged', False)}")
    print(f"Iterations: {consensus.get('iterations', 0)}")
    print(f"Agreement score: {result.get('final_decision', 'N/A')}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python bug_finder_example.py <path-to-analyze>")
        print()
        print("Example:")
        print("  python bug_finder_example.py ../my_project/main.py")
        print("  python bug_finder_example.py ../my_project/")
        print()
        print("Available CLIs:")
        available = get_available_integrations()
        for name, status in available.items():
            ready = status.get('ready', False)
            print(f"  {'✓' if ready else '✗'} {name}")
        return 1
    
    target_path = sys.argv[1]
    
    # Optional: specify CLIs via additional args
    cli_types = sys.argv[2:] if len(sys.argv) > 2 else None
    
    try:
        result = asyncio.run(find_bugs_with_consensus(
            target_path=target_path,
            cli_types=cli_types,
            verbose=True
        ))
        print_results(result)
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
