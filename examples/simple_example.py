#!/usr/bin/env python3
"""
Simple example demonstrating the multi-agent consensus system.

This example shows how to create agents, set up a consensus manager,
and run iterative consensus to reach agreement.
"""

from consensus_system import ConsensusAgent, ConsensusManager

# Constants
SEPARATOR_WIDTH = 60


def main():
    print("="*SEPARATOR_WIDTH)
    print("Multi-Agent Consensus System - Simple Example")
    print("="*SEPARATOR_WIDTH)
    
    # Create three coding agents with different initial assessments
    print("\n1. Creating agents...")
    
    code_analyzer = ConsensusAgent(
        agent_id="analyzer",
        role="CodeAnalyzer",
        instructions="Analyze code quality and structure",
        initial_value=7.5,  # Initial quality score
        verbose=True
    )
    
    code_reviewer = ConsensusAgent(
        agent_id="reviewer",
        role="CodeReviewer",
        instructions="Review code for best practices",
        initial_value=8.2,  # Initial quality score
        verbose=True
    )
    
    security_expert = ConsensusAgent(
        agent_id="security",
        role="SecurityExpert",
        instructions="Analyze security aspects",
        initial_value=6.8,  # Initial quality score
        verbose=True
    )
    
    agents = [code_analyzer, code_reviewer, security_expert]
    
    print(f"Created {len(agents)} agents:")
    for agent in agents:
        print(f"  - {agent.role}: initial score = {agent.value}")
    
    # Create consensus manager
    print("\n2. Setting up consensus manager...")
    manager = ConsensusManager(
        agents=agents,
        max_iterations=10,
        convergence_threshold=0.01,
        verbose=True
    )
    
    # Setup fully-connected network (each agent talks to all others)
    print("\n3. Setting up network topology...")
    manager.setup_network(topology="fully_connected")
    
    # Run consensus
    print("\n4. Running consensus algorithm...")
    print("-" * SEPARATOR_WIDTH)
    
    result = manager.run_consensus(strategy="average")
    
    # Display results
    print("\n" + "="*SEPARATOR_WIDTH)
    print("RESULTS")
    print("="*SEPARATOR_WIDTH)
    
    print(f"\nConverged: {result.get('converged', False)}")
    print(f"Iterations: {result.get('iterations', 0)}")
    
    consensus_value = result.get('consensus_value')
    if isinstance(consensus_value, (int, float)):
        print(f"Consensus Score: {consensus_value:.2f}")
    else:
        print(f"Consensus Score: {consensus_value}")
    
    print("\nFinal agent scores:")
    for agent in agents:
        if isinstance(agent.value, (int, float)):
            print(f"  {agent.role}: {agent.value:.2f}")
        else:
            print(f"  {agent.role}: {agent.value}")
    
    print("\nInterpretation:")
    if isinstance(consensus_value, (int, float)):
        if consensus_value >= 8.0:
            print("  ✓ Code quality is EXCELLENT")
        elif consensus_value >= 7.0:
            print("  ✓ Code quality is GOOD")
        elif consensus_value >= 6.0:
            print("  ⚠ Code quality is ACCEPTABLE (improvements recommended)")
        else:
            print("  ✗ Code quality needs SIGNIFICANT improvement")
    else:
        print(f"  ○ Assessment: {consensus_value}")
    
    print("\n" + "="*SEPARATOR_WIDTH)
    print("Example completed successfully!")
    print("="*SEPARATOR_WIDTH)


if __name__ == "__main__":
    main()
