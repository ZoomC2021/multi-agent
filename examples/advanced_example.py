#!/usr/bin/env python3
"""
Advanced example demonstrating PraisonAI integration with consensus system.

This example shows how to use PraisonAI-backed agents for actual LLM execution
with consensus-based decision making.
"""

from consensus_system.config import load_config
from consensus_system.manager import ConsensusManager
from consensus_system.praison_integration import create_praison_agents_from_config

# Constants
SEPARATOR_WIDTH = 70


def main():
    print("="*SEPARATOR_WIDTH)
    print("PraisonAI Multi-Agent Consensus System - Advanced Example")
    print("="*SEPARATOR_WIDTH)
    
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
    print("-" * SEPARATOR_WIDTH)
    
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
    print("\n" + "="*SEPARATOR_WIDTH)
    print("COLLABORATIVE REVIEW RESULTS")
    print("="*SEPARATOR_WIDTH)
    
    print("\nTask:")
    print("-" * SEPARATOR_WIDTH)
    task_str = str(result.get('task', ''))
    print(task_str[:200] + ("..." if len(task_str) > 200 else ""))
    
    print("\n\nAgent Responses:")
    print("-" * SEPARATOR_WIDTH)
    for agent_result in result.get('agent_results', []):
        role = agent_result.get('role', 'Unknown Agent')
        print(f"\n{role}:")
        response = str(agent_result.get('response', ''))
        print(f"  Response: {response[:100]}...")
        print(f"  Mode: {agent_result.get('mode', 'standard')}")
    
    print("\n\nConsensus Details:")
    print("-" * SEPARATOR_WIDTH)
    consensus = result.get('consensus', {})
    print(f"Converged: {consensus.get('converged', False)}")
    print(f"Iterations: {consensus.get('iterations', 0)}")
    
    consensus_value = consensus.get('consensus_value')
    if isinstance(consensus_value, (int, float)):
        print(f"Final Consensus Value: {consensus_value:.2f}")
    else:
        print(f"Final Consensus Value: {consensus_value}")
    
    print("\n\nFinal Agent Values:")
    print("-" * SEPARATOR_WIDTH)
    for agent_id, value in consensus.get('final_values', {}).items():
        if isinstance(value, (int, float)):
            print(f"  {agent_id}: {value:.2f}")
        else:
            print(f"  {agent_id}: {value}")
    
    print("\n\nInterpretation:")
    print("-" * SEPARATOR_WIDTH)
    
    if isinstance(consensus_value, (int, float)):
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
    else:
        print(f"○ Overall Assessment: {consensus_value}")
    
    # Show convergence history
    history = consensus.get('history', [])
    if len(history) > 0:
        print("\n\nConsensus Convergence History:")
        print("-" * SEPARATOR_WIDTH)
        for iteration in history[:5]:  # Show first 5
            iter_num = iteration.get('iteration', '?')
            print(f"Iteration {iter_num}: ", end="")
            values = []
            for v in iteration.get('values', {}).values():
                if isinstance(v, (int, float)):
                    values.append(f"{v:.2f}")
                else:
                    values.append(str(v))
            print(f"[{', '.join(values)}]")
    
    print("\n" + "="*SEPARATOR_WIDTH)
    print("Advanced example completed successfully!")
    print("="*SEPARATOR_WIDTH)


if __name__ == "__main__":
    main()
