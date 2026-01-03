"""
Consensus Manager Module

Orchestrates multiple agents to reach consensus through iterative collaboration.
"""

from typing import List, Dict, Any, Optional, Callable, Union
import time
import concurrent.futures
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
        verbose: bool = False,
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

        Raises:
            ValueError: If topology is unknown
        """
        if topology == "fully_connected":
            # Each agent is connected to all other agents
            for agent in self.agents:
                for other_agent in self.agents:
                    if agent != other_agent:
                        agent.add_neighbor(other_agent)

        elif topology == "ring":
            # Agents are connected in a ring
            num_agents = len(self.agents)
            if num_agents < 2:
                # No neighbors for 0 or 1 agent
                pass
            else:
                for i, agent in enumerate(self.agents):
                    next_agent = self.agents[(i + 1) % num_agents]
                    # Python modulo handles negative numbers correctly: -1 % N = N-1
                    prev_agent = self.agents[(i - 1) % num_agents]
                    
                    # Add next and previous neighbors
                    # Add neighbors regardless of whether they are the same (deduped in add_neighbor)
                    # to correctly handle the 2-agent case where next == prev
                    if next_agent != agent:
                        agent.add_neighbor(next_agent)
                    if prev_agent != agent:
                        agent.add_neighbor(prev_agent)

        elif topology == "chain":
            # Agents are connected in a chain
            for i, agent in enumerate(self.agents):
                if i > 0:
                    prev_agent = self.agents[i - 1]
                    if prev_agent != agent:
                        agent.add_neighbor(prev_agent)
                if i < len(self.agents) - 1:
                    next_agent = self.agents[i + 1]
                    agent.add_neighbor(next_agent)
        else:
            raise ValueError(
                f"Unknown topology: {topology}. Supported: fully_connected, ring, chain"
            )

        if self.verbose:
            print(f"Network topology: {topology}")
            for agent in self.agents:
                print(f"  {agent.role}: {len(agent.neighbors)} neighbors")

    def iterate_consensus(
        self, strategy: str = "average", callback: Optional[Callable] = None
    ) -> bool:
        """
        Perform one iteration of consensus updates.

        Args:
            strategy: Consensus strategy to use
            callback: Optional callback function called after each iteration

        Returns:
            True if converged, False otherwise
        """
        # Handle empty agent list
        if not self.agents:
            if self.verbose:
                print("No agents available for consensus iteration")
            return False

        # Calculate new values for all agents first (Simultaneous Update / Jacobi method)
        # This prevents order-dependent bias where early-updated agents influence later ones in the same round
        new_values_map = {}
        for agent in self.agents:
            # Use agent_id as key to avoid object identity issues
            new_values_map[agent.agent_id] = agent.calculate_consensus_value(strategy)

        # Apply updates
        changes = []
        for agent in self.agents:
            if agent.agent_id in new_values_map:
                new_val = new_values_map[agent.agent_id]
                old_val = agent.value
                if new_val != old_val:
                    agent.update_value(new_val)
                    changes.append((old_val, new_val))

        # Record iteration state
        iteration_state = {
            "iteration": self.iteration_count,
            "values": {agent.agent_id: agent.value for agent in self.agents},
            "timestamp": time.time(),
        }
        self.consensus_history.append(iteration_state)

        if self.verbose:
            print(f"Iteration {self.iteration_count}:")
            for agent in self.agents:
                print(f"  {agent.role}: {agent.value}")

        # Check convergence
        # We consider it converged if no values changed significantly
        if not changes:
            if self.verbose:
                print("Converged! No values changed.")
            if callback:
                callback(iteration_state)
            return True

        # Check numeric convergence threshold if changes occurred
        try:
            # Check if we have any non-numeric changes
            non_numeric_changes = [
                (old, new)
                for old, new in changes
                if not (isinstance(new, (int, float)) and not isinstance(new, bool))
                or not (isinstance(old, (int, float)) and not isinstance(old, bool))
            ]

            # If there are ANY non-numeric changes, we have not converged because strict equality failed
            # (checked by 'if not changes' above).
            if non_numeric_changes:
                return False

            # Filter for numeric changes only
            numeric_changes = [
                abs(new - old)
                for old, new in changes
                if isinstance(new, (int, float))
                and isinstance(old, (int, float))
                and not isinstance(new, bool)
                and not isinstance(old, bool)
            ]

            if numeric_changes:
                max_change = max(numeric_changes)
                converged = max_change < self.convergence_threshold

                if self.verbose and converged:
                    print(f"Converged! Max change: {max_change}")

                if callback:
                    callback(iteration_state)

                return converged
            
            # If we are here, it means 'changes' was not empty, but we found no non-numeric changes
            # AND no numeric changes. This shouldn't theoretically happen given the logic above,
            # but implies no significant change.
            return True

        except (TypeError, ValueError) as e:
            # Log but don't crash on convergence check errors
            if self.verbose:
                print(f"Warning: Convergence check encountered error: {e}")

        if callback:
            callback(iteration_state)

        return False

    def run_consensus(
        self, strategy: str = "average", callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Run the consensus process until convergence or max iterations.

        Args:
            strategy: Consensus strategy to use
            callback: Optional callback function

        Returns:
            Final consensus results
        """
        # Handle empty agent list
        if not self.agents:
            if self.verbose:
                print("No agents available for consensus")
            return {
                "converged": False,
                "iterations": 0,
                "consensus_value": None,
                "final_values": {},
                "history": [],
            }

        if self.verbose:
            print(f"Starting consensus with {len(self.agents)} agents...")
            print(f"Strategy: {strategy}, Max iterations: {self.max_iterations}")

        # Clear consensus history at the start
        self.consensus_history.clear()
        self.iteration_count = 0
        converged = False

        while self.iteration_count < self.max_iterations and not converged:
            converged = self.iterate_consensus(strategy=strategy, callback=callback)
            self.iteration_count += 1

        # Compute final consensus value
        final_values = [agent.value for agent in self.agents]

        # Calculate final result based on strategy and agent values
        if strategy == "average":
            try:
                # Check for numeric values, excluding booleans
                numeric_values: List[Union[int, float]] = [
                    v for v in final_values if isinstance(v, (int, float)) and not isinstance(v, bool)
                ]

                if numeric_values:
                    consensus_value = sum(numeric_values) / len(numeric_values)
                else:
                    consensus_value = None
            except (TypeError, ValueError):
                consensus_value = None
        
        elif strategy == "majority":
            # Majority vote
            if final_values:
                # Use object identity/equality for counting
                value_counts = []
                for val in final_values:
                    if val is None:
                        continue
                    found = False
                    for i, (existing_val, count) in enumerate(value_counts):
                        if existing_val == val:
                            value_counts[i] = (existing_val, count + 1)
                            found = True
                            break
                    if not found:
                        value_counts.append((val, 1))
                
                if value_counts:
                    winner = max(value_counts, key=lambda x: x[1])
                    consensus_value = winner[0]
                else:
                    consensus_value = None
            else:
                consensus_value = None

        elif strategy == "weighted":
            # Weighted average
            numerator = 0.0
            total_weight = 0.0
            for agent in self.agents:
                val = agent.value
                if val is not None and isinstance(val, (int, float)) and not isinstance(val, bool):
                    numerator += float(val) * agent.weight
                    total_weight += agent.weight
            
            if total_weight > 0:
                consensus_value = numerator / total_weight
            else:
                consensus_value = None
        
        else:
            # Unknown strategy, fallback to majority
            if self.verbose:
                print(f"Warning: Unknown strategy {strategy}, falling back to majority for final value")
            
            if final_values:
                value_counts = []
                for val in final_values:
                    if val is None:
                        continue
                    found = False
                    for i, (existing_val, count) in enumerate(value_counts):
                        if existing_val == val:
                            value_counts[i] = (existing_val, count + 1)
                            found = True
                            break
                    if not found:
                        value_counts.append((val, 1))
                
                if value_counts:
                    winner = max(value_counts, key=lambda x: x[1])
                    consensus_value = winner[0]
                else:
                    consensus_value = None
            else:
                consensus_value = None


        results = {
            "converged": converged,
            "iterations": self.iteration_count,
            "consensus_value": consensus_value,
            "final_values": {agent.agent_id: agent.value for agent in self.agents},
            "history": self.consensus_history,
        }

        if self.verbose:
            print("\nConsensus completed!")
            print(f"  Converged: {converged}")
            print(f"  Iterations: {self.iteration_count}")
            print(f"  Consensus value: {consensus_value}")

        return results

    def execute_collaborative_task(
        self, 
        task: str, 
        consensus_strategy: str = "majority", 
        context: Optional[Dict] = None,
        status_callback: Optional[Callable[[str], None]] = None
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
            print("\n=== Collaborative Task ===")
            print(f"Task: {task}")

        # Each agent executes the task in parallel

        agent_results = []
        if self.verbose:
            print(f"Executing task with {len(self.agents)} agents in parallel...")

        # Calculate max_workers: ensure at least 1, but cap at a reasonable limit
        # to prevent resource exhaustion with many agents
        num_agents = len(self.agents)
        max_workers = max(1, min(num_agents, 32))

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map each agent to an execution future
            future_to_agent = {
                executor.submit(agent.execute, task, context): agent for agent in self.agents
            }

            # Collect results mapped to agents
            agent_results_map = {}
            for future in concurrent.futures.as_completed(future_to_agent):
                agent = future_to_agent[future]
                try:
                    result = future.result()
                    agent_results_map[agent.agent_id] = result
                    
                    if status_callback:
                        status_callback(f"Worker {agent.role} finished analysis.")
                except Exception as e:
                    if self.verbose:
                        print(f"Error executing agent {agent.role}: {e}")
                    agent_results_map[agent.agent_id] = {
                        "agent_id": agent.agent_id,
                        "role": agent.role,
                        "error": str(e),
                        "value": None,  # Assign None on error so it is ignored
                    }

        # Reconstruct results list in original agent order
        for agent in self.agents:
            result = agent_results_map.get(agent.agent_id, {})
            agent_results.append(result)

            # Extract consensus value from the result if available, or calculate fallback
            new_value = result.get("value")

            if new_value is None:
                # Fallback to None if no explicit value is provided
                response = result.get("response", "")
                if isinstance(response, str) and response:
                    # Heuristic: score based on response length as a placeholder for detail/confidence
                    # Standardize divisor to 100.0 (matches external_agent.py)
                    new_value = min(len(response) / 100.0, 10.0)
                else:
                    new_value = None  # Default to None so it's ignored in consensus

            if new_value != agent.value:
                agent.update_value(new_value)

            # Ensure the result dictionary reflects the updated value
            result["value"] = new_value

        # Run consensus to aggregate results
        consensus_result = self.run_consensus(strategy=consensus_strategy)

        return {
            "task": task,
            "agent_results": agent_results,
            "consensus": consensus_result,
            "final_decision": consensus_result["consensus_value"],
        }

    def get_system_state(self) -> Dict[str, Any]:
        """Get the current state of the entire system."""
        return {
            "agent_count": len(self.agents),
            "agents": [agent.get_state() for agent in self.agents],
            "iteration_count": self.iteration_count,
            "history_length": len(self.consensus_history),
        }
