#!/usr/bin/env python3
"""
Advanced example demonstrating PraisonAI integration with consensus system.

This example shows how to use PraisonAI-backed agents for actual LLM execution
with consensus-based decision making.
"""

from consensus_system.config import load_config
from consensus_system.manager import ConsensusManager
from consensus_system.praison_integration import create_praison_agents_from_config


def main():
    print("="*70)
    print("PraisonAI Multi-Agent Consensus System - Advanced Example")
    print("="*70)
    
    # Load configuration
    print("\n1. Loading configuration...")
    try:
        config = load_config("examples/coding_agents.yaml")
        print(f"   ✓ Loaded configuration with {len(config['agents'])} agents")
    except Exception as e:
        print(f"   ✗ Error loading configuration: {e}")
        return
    
    # Create PraisonAI-backed agents
    print("\n2. Creating PraisonAI-backed consensus agents...")
    agents = create_praison_agents_from_config(config)
    
    for agent in agents:
        print(f"   - {agent.role} ({agent.agent_id})")
    
    # Create consensus manager
    print("\n3. Initializing consensus manager...")
    consensus_config = config.get('consensus', {})
    
    manager = ConsensusManager(
        agents=agents,
        max_iterations=consensus_config.get('max_iterations', 15),
        convergence_threshold=consensus_config.get('convergence_threshold', 0.01),
        verbose=True
    )
    
    print(f"   ✓ Max iterations: {consensus_config.get('max_iterations', 15)}")
    print(f"   ✓ Convergence threshold: {consensus_config.get('convergence_threshold', 0.01)}")
    
    # Setup network
    print("\n4. Setting up agent communication network...")
    topology = consensus_config.get('topology', 'fully_connected')
    manager.setup_network(topology=topology)
    
    # Execute collaborative task
    print("\n5. Executing collaborative code review task...")
    print("-" * 70)
    
    task = """
    Review the following Python authentication function for security and quality:
    
    def authenticate_user(username, password):
        db = get_database_connection()
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        result = db.execute(query)
        return result is not None
    """
    
    result = manager.execute_collaborative_task(
        task=task,
        consensus_strategy=consensus_config.get('strategy', 'average'),
        context={'module': 'authentication', 'language': 'python'}
    )
    
    # Display comprehensive results
    print("\n" + "="*70)
    print("COLLABORATIVE REVIEW RESULTS")
    print("="*70)
    
    print("\nTask:")
    print("-" * 70)
    print(result['task'][:200] + "...")
    
    print("\n\nAgent Responses:")
    print("-" * 70)
    for agent_result in result['agent_results']:
        print(f"\n{agent_result['role']}:")
        print(f"  Response: {agent_result['response'][:100]}...")
        print(f"  Mode: {agent_result.get('mode', 'standard')}")
    
    print("\n\nConsensus Details:")
    print("-" * 70)
    consensus = result['consensus']
    print(f"Converged: {consensus['converged']}")
    print(f"Iterations: {consensus['iterations']}")
    print(f"Final Consensus Value: {consensus['consensus_value']:.2f}")
    
    print("\n\nFinal Agent Values:")
    print("-" * 70)
    for agent_id, value in consensus['final_values'].items():
        print(f"  {agent_id}: {value:.2f}")
    
    print("\n\nInterpretation:")
    print("-" * 70)
    consensus_value = consensus['consensus_value']
    
    if consensus_value < 3.0:
        status = "CRITICAL ISSUES FOUND"
        symbol = "✗"
        recommendation = "Immediate attention required. Multiple agents identified serious problems."
    elif consensus_value < 5.0:
        status = "NEEDS IMPROVEMENT"
        symbol = "⚠"
        recommendation = "Several issues identified. Code requires refactoring."
    elif consensus_value < 7.0:
        status = "ACCEPTABLE"
        symbol = "○"
        recommendation = "Code is functional but could benefit from improvements."
    elif consensus_value < 8.5:
        status = "GOOD QUALITY"
        symbol = "✓"
        recommendation = "Code meets quality standards with minor suggestions."
    else:
        status = "EXCELLENT"
        symbol = "✓✓"
        recommendation = "Code demonstrates best practices and high quality."
    
    print(f"{symbol} Overall Assessment: {status}")
    print(f"   Recommendation: {recommendation}")
    
    # Show convergence history
    if len(consensus['history']) > 0:
        print("\n\nConsensus Convergence History:")
        print("-" * 70)
        for i, iteration in enumerate(consensus['history'][:5]):  # Show first 5
            print(f"Iteration {iteration['iteration']}: ", end="")
            values = [f"{v:.2f}" for v in iteration['values'].values()]
            print(f"[{', '.join(values)}]")
    
    print("\n" + "="*70)
    print("Advanced example completed successfully!")
    print("="*70)


if __name__ == "__main__":
    main()
