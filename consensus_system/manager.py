"""
Consensus Manager Module

Orchestrates multiple agents to reach consensus through iterative collaboration.
"""

from typing import List, Dict, Any, Optional, Callable
import time
from consensus_system.agent import ConsensusAgent


class ConsensusManager:
    """
    Manages a multi-agent system with iterative consensus capabilities.
    
    Coordinates multiple agents to collaborate on tasks and reach agreement
    through iterative communication and value updates.
    """
    
    def __init__(
        self,
        agents: List[ConsensusAgent],
        max_iterations: int = 10,
        convergence_threshold: float = 0.01,
        verbose: bool = False
    ):
        """
        Initialize the consensus manager.
        
        Args:
            agents: List of consensus agents
            max_iterations: Maximum number of consensus iterations
            convergence_threshold: Threshold for determining convergence
            verbose: Enable verbose logging
        """
        self.agents = agents
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.verbose = verbose
        self.iteration_count = 0
        self.consensus_history: List[Dict[str, Any]] = []
        
    def setup_network(self, topology: str = "fully_connected"):
        """
        Set up the agent communication network.
        
        Args:
            topology: Network topology ("fully_connected", "ring", "chain")
        """
        if topology == "fully_connected":
            # Each agent is connected to all other agents
            for agent in self.agents:
                for other_agent in self.agents:
                    if agent != other_agent:
                        agent.add_neighbor(other_agent)
                        
        elif topology == "ring":
            # Agents are connected in a ring
            for i, agent in enumerate(self.agents):
                next_agent = self.agents[(i + 1) % len(self.agents)]
                prev_agent = self.agents[(i - 1) % len(self.agents)]
                agent.add_neighbor(next_agent)
                agent.add_neighbor(prev_agent)
                
        elif topology == "chain":
            # Agents are connected in a chain
            for i, agent in enumerate(self.agents):
                if i > 0:
                    agent.add_neighbor(self.agents[i - 1])
                if i < len(self.agents) - 1:
                    agent.add_neighbor(self.agents[i + 1])
                    
        if self.verbose:
            print(f"Network topology: {topology}")
            for agent in self.agents:
                print(f"  {agent.role}: {len(agent.neighbors)} neighbors")
                
    def iterate_consensus(
        self,
        strategy: str = "average",
        callback: Optional[Callable] = None
    ) -> bool:
        """
        Perform one iteration of consensus updates.
        
        Args:
            strategy: Consensus strategy to use
            callback: Optional callback function called after each iteration
            
        Returns:
            True if converged, False otherwise
        """
        # Save current values
        old_values = [agent.value for agent in self.agents]
        
        # Update each agent's value based on consensus
        for agent in self.agents:
            agent.consensus_update(strategy=strategy)
            
        # Get new values
        new_values = [agent.value for agent in self.agents]
        
        # Record iteration state
        iteration_state = {
            "iteration": self.iteration_count,
            "values": {agent.agent_id: agent.value for agent in self.agents},
            "timestamp": time.time()
        }
        self.consensus_history.append(iteration_state)
        
        if self.verbose:
            print(f"Iteration {self.iteration_count}:")
            for agent in self.agents:
                print(f"  {agent.role}: {agent.value}")
                
        # Check convergence (for numeric values)
        try:
            if all(isinstance(v, (int, float)) for v in new_values):
                max_change = max(abs(new - old) for new, old in zip(new_values, old_values))
                converged = max_change < self.convergence_threshold
                
                if self.verbose and converged:
                    print(f"Converged! Max change: {max_change}")
                    
                if callback:
                    callback(iteration_state)
                    
                return converged
        except (TypeError, ValueError):
            pass
            
        if callback:
            callback(iteration_state)
            
        return False
        
    def run_consensus(
        self,
        strategy: str = "average",
        callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Run the consensus process until convergence or max iterations.
        
        Args:
            strategy: Consensus strategy to use
            callback: Optional callback function
            
        Returns:
            Final consensus results
        """
        if self.verbose:
            print(f"Starting consensus with {len(self.agents)} agents...")
            print(f"Strategy: {strategy}, Max iterations: {self.max_iterations}")
            
        self.iteration_count = 0
        converged = False
        
        while self.iteration_count < self.max_iterations and not converged:
            converged = self.iterate_consensus(strategy=strategy, callback=callback)
            self.iteration_count += 1
            
        # Compute final consensus value
        final_values = [agent.value for agent in self.agents]
        
        try:
            if all(isinstance(v, (int, float)) for v in final_values):
                consensus_value = sum(final_values) / len(final_values)
            else:
                # For non-numeric, use most common value
                value_counts = {}
                for val in final_values:
                    val_str = str(val)
                    value_counts[val_str] = value_counts.get(val_str, 0) + 1
                consensus_value = max(value_counts, key=value_counts.get)
        except:
            consensus_value = None
            
        results = {
            "converged": converged,
            "iterations": self.iteration_count,
            "consensus_value": consensus_value,
            "final_values": {agent.agent_id: agent.value for agent in self.agents},
            "history": self.consensus_history
        }
        
        if self.verbose:
            print(f"\nConsensus completed!")
            print(f"  Converged: {converged}")
            print(f"  Iterations: {self.iteration_count}")
            print(f"  Consensus value: {consensus_value}")
            
        return results
        
    def execute_collaborative_task(
        self,
        task: str,
        consensus_strategy: str = "majority",
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a collaborative task with all agents and reach consensus.
        
        Args:
            task: Task description
            consensus_strategy: Strategy for reaching consensus
            context: Additional context
            
        Returns:
            Collaborative task results with consensus
        """
        if self.verbose:
            print(f"\n=== Collaborative Task ===")
            print(f"Task: {task}")
            
        # Each agent executes the task
        agent_results = []
        for agent in self.agents:
            result = agent.execute(task, context)
            agent_results.append(result)
            
        # Update agent values based on their task results
        for i, agent in enumerate(self.agents):
            # Extract some metric from the result to use as value
            # In a real system, this would be a quality score or confidence level
            agent.update_value(i + 1)  # Placeholder value
            
        # Run consensus to aggregate results
        consensus_result = self.run_consensus(strategy=consensus_strategy)
        
        return {
            "task": task,
            "agent_results": agent_results,
            "consensus": consensus_result,
            "final_decision": consensus_result["consensus_value"]
        }
        
    def get_system_state(self) -> Dict[str, Any]:
        """Get the current state of the entire system."""
        return {
            "agent_count": len(self.agents),
            "agents": [agent.get_state() for agent in self.agents],
            "iteration_count": self.iteration_count,
            "history_length": len(self.consensus_history)
        }
