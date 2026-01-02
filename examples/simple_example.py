#!/usr/bin/env python3
"""
Simple example demonstrating the multi-agent consensus system.

This example shows how to create agents, set up a consensus manager,
and run iterative consensus to reach agreement.
"""

from consensus_system import ConsensusAgent, ConsensusManager


def main():
    print("="*60)
    print("Multi-Agent Consensus System - Simple Example")
    print("="*60)
    
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
    print("-" * 60)
    
    result = manager.run_consensus(strategy="average")
    
    # Display results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    print(f"\nConverged: {result['converged']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Consensus Score: {result['consensus_value']:.2f}")
    
    print("\nFinal agent scores:")
    for agent in agents:
        print(f"  {agent.role}: {agent.value:.2f}")
    
    print("\nInterpretation:")
    consensus_score = result['consensus_value']
    if consensus_score >= 8.0:
        print("  ✓ Code quality is EXCELLENT")
    elif consensus_score >= 7.0:
        print("  ✓ Code quality is GOOD")
    elif consensus_score >= 6.0:
        print("  ⚠ Code quality is ACCEPTABLE (improvements recommended)")
    else:
        print("  ✗ Code quality needs SIGNIFICANT improvement")
    
    print("\n" + "="*60)
    print("Example completed successfully!")
    print("="*60)


if __name__ == "__main__":
    main()
