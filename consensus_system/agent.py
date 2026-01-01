"""
Consensus Agent Module

Implements individual agents with consensus capabilities for the multi-agent system.
"""

from typing import Dict, List, Any, Optional
import json


class ConsensusAgent:
    """
    An agent that participates in iterative consensus with other agents.
    
    Each agent maintains its own state/value and can update it based on
    communication with neighboring agents in the consensus network.
    """
    
    def __init__(
        self,
        agent_id: str,
        role: str,
        instructions: str,
        initial_value: Optional[Any] = None,
        llm: str = "gpt-4",
        verbose: bool = False
    ):
        """
        Initialize a consensus agent.
        
        Args:
            agent_id: Unique identifier for the agent
            role: Role/name of the agent (e.g., "CodeAnalyzer", "CodeReviewer")
            instructions: Instructions/prompt for the agent's behavior
            initial_value: Initial state/value for consensus
            llm: Language model to use (default: gpt-4)
            verbose: Enable verbose logging
        """
        self.agent_id = agent_id
        self.role = role
        self.instructions = instructions
        self.value = initial_value
        self.llm = llm
        self.verbose = verbose
        self.neighbors: List['ConsensusAgent'] = []
        self.history: List[Any] = []
        
    def add_neighbor(self, agent: 'ConsensusAgent'):
        """Add a neighboring agent for consensus communication."""
        if agent not in self.neighbors and agent != self:
            self.neighbors.append(agent)
            
    def update_value(self, new_value: Any):
        """Update the agent's current value and record in history."""
        self.history.append(self.value)
        self.value = new_value
        
    def consensus_update(self, strategy: str = "average") -> Any:
        """
        Perform a consensus update based on neighbors' values.
        
        Args:
            strategy: Consensus strategy ("average", "majority", "weighted")
            
        Returns:
            Updated consensus value
        """
        if not self.neighbors:
            return self.value
            
        neighbor_values = [n.value for n in self.neighbors if n.value is not None]
        
        if not neighbor_values:
            return self.value
            
        if strategy == "average":
            # Average consensus (for numeric values, excluding booleans)
            if isinstance(self.value, (int, float)) and not isinstance(self.value, bool):
                # Filter neighbor values to include only numeric types (excluding booleans)
                numeric_neighbor_values = [v for v in neighbor_values if isinstance(v, (int, float)) and not isinstance(v, bool)]
                all_numeric_values = [self.value] + numeric_neighbor_values
                if all_numeric_values:
                    new_value = sum(all_numeric_values) / len(all_numeric_values)
                    self.update_value(new_value)
                    return new_value
                
        elif strategy == "majority":
            # Majority voting (for categorical values, excluding None)
            # Filter out None values
            all_values = [self.value] + [v for v in neighbor_values if v is not None]
            # Remove None values from all_values
            valid_values = [v for v in all_values if v is not None]
            
            if not valid_values:
                return self.value
                
            value_counts = {}
            for val in valid_values:
                val_str = str(val)
                value_counts[val_str] = value_counts.get(val_str, 0) + 1
            majority_value = max(value_counts, key=value_counts.get)
            # Try to convert back to original type
            for val in valid_values:
                if str(val) == majority_value:
                    self.update_value(val)
                    return val
                    
        elif strategy == "weighted":
            # Weighted consensus strategy not yet implemented
            raise NotImplementedError("Weighted consensus strategy is not yet implemented. Use 'average' or 'majority'.")
                    
        return self.value
        
    def execute(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a task using the agent's capabilities.
        
        Args:
            task: Task description
            context: Additional context for the task
            
        Returns:
            Result dictionary with agent's response
        """
        if self.verbose:
            print(f"[{self.role}] Executing task: {task}")
            
        # Simulate agent execution (in real implementation, this would call PraisonAI)
        result = {
            "agent_id": self.agent_id,
            "role": self.role,
            "task": task,
            "response": f"{self.role} analyzed: {task}",
            "value": self.value,
            "context": context or {}
        }
        
        if self.verbose:
            print(f"[{self.role}] Result: {result['response']}")
            
        return result
        
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the agent."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "value": self.value,
            "neighbor_count": len(self.neighbors),
            "history_length": len(self.history)
        }
        
    def __repr__(self):
        return f"ConsensusAgent(id={self.agent_id}, role={self.role}, value={self.value})"
