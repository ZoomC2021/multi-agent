"""
Consensus Agent Module

Implements individual agents with consensus capabilities for the multi-agent system.
"""

from typing import Dict, List, Any, Optional, cast, Union


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
        weight: float = 1.0,
        llm: str = "gpt-4",
        verbose: bool = False,
    ):
        """
        Initialize a consensus agent.

        Args:
            agent_id: Unique identifier for the agent
            role: Role/name of the agent (e.g., "CodeAnalyzer", "CodeReviewer")
            instructions: Instructions/prompt for the agent's behavior
            initial_value: Initial state/value for consensus
            weight: Voting weight for weighted consensus (default: 1.0)
            llm: Language model to use (default: gpt-4)
            verbose: Enable verbose logging
        """
        self.agent_id = agent_id
        self.role = role
        self.instructions = instructions
        self.value = initial_value
        self.weight = weight
        self.llm = llm
        self.verbose = verbose
        self.neighbors: List["ConsensusAgent"] = []
        self.history: List[Any] = []

    def add_neighbor(self, agent: "ConsensusAgent"):
        """Add a neighboring agent for consensus communication."""
        if agent not in self.neighbors and agent != self:
            self.neighbors.append(agent)

    def update_value(self, new_value: Any):
        """Update the agent's current value and record in history."""
        self.history.append(self.value)
        self.value = new_value

    def calculate_consensus_value(self, strategy: str = "average") -> Any:
        """
        Calculate the new consensus value based on neighbors' values, without updating state.

        Args:
            strategy: Consensus strategy ("average", "majority", "weighted")

        Returns:
            Calculated consensus value
        """
        if not self.neighbors:
            return self.value

        # Get all valid (non-None) neighbor values
        neighbor_values = [n.value for n in self.neighbors if n.value is not None]

        if strategy == "average":
            # Average consensus (for numeric values, excluding booleans)
            # Filter neighbor values to include only numeric types (excluding booleans)
            numeric_neighbor_values: List[Union[int, float]] = [
                v
                for v in neighbor_values
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]

            # Check if self value is numeric (excluding booleans)
            self_numeric = isinstance(self.value, (int, float)) and not isinstance(self.value, bool)

            all_numeric_values: List[Union[int, float]] = []
            if self_numeric:
                all_numeric_values.append(cast(Union[int, float], self.value))
            all_numeric_values.extend(numeric_neighbor_values)

            if all_numeric_values:
                return sum(all_numeric_values) / len(all_numeric_values)

        elif strategy == "majority":
            # Majority voting (for categorical values)
            all_values = []
            if self.value is not None:
                all_values.append(self.value)
            all_values.extend(neighbor_values)

            if not all_values:
                return self.value

            # Use precise counting instead of string conversion
            # We use a list of (value, count) tuples since values might not be hashable
            value_counts = []
            for val in all_values:
                found = False
                for i, (existing_val, count) in enumerate(value_counts):
                    if existing_val == val:
                        value_counts[i] = (existing_val, count + 1)
                        found = True
                        break
                if not found:
                    value_counts.append((val, 1))

            # Find max count
            if not value_counts:
                return self.value

            # Find the value with the highest count
            # In case of tie, pick the first one encountered (deterministic for stable sort)
            winner = max(value_counts, key=lambda x: x[1])
            return winner[0]

        elif strategy == "weighted":
            # Weighted average consensus
            # Includes self weight and neighbor weights

            numerator = 0.0
            total_weight = 0.0

            # Process self
            if isinstance(self.value, (int, float)) and not isinstance(self.value, bool):
                numerator += float(self.value) * self.weight
                total_weight += self.weight

            # Process neighbors
            for neighbor in self.neighbors:
                val = neighbor.value
                if val is not None and isinstance(val, (int, float)) and not isinstance(val, bool):
                    numerator += float(val) * neighbor.weight
                    total_weight += neighbor.weight

            if total_weight > 0:
                return numerator / total_weight

        return self.value

    def consensus_update(self, strategy: str = "average") -> Any:
        """
        Perform a consensus update based on neighbors' values.

        Note: This updates the agent's state immediately. For synchronized updates,
        manager using calculate_consensus_value() followed by mass update_value() is preferred.

        Args:
            strategy: Consensus strategy ("average", "majority", "weighted")

        Returns:
            Updated consensus value
        """
        new_value = self.calculate_consensus_value(strategy)
        if new_value != self.value:
            self.update_value(new_value)
        return new_value

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

        # Simulate agent execution (in real implementation, use LiteLLMAgent)
        result = {
            "agent_id": self.agent_id,
            "role": self.role,
            "task": task,
            "response": f"{self.role} analyzed: {task}",
            "value": self.value,
            "context": context or {},
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
            "history_length": len(self.history),
        }

    def __repr__(self):
        return f"ConsensusAgent(id={self.agent_id}, role={self.role}, value={self.value})"
