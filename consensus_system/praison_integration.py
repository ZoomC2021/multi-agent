"""
PraisonAI Integration Module

Integrates PraisonAI agents with the consensus system for actual LLM-based execution.
"""

from typing import Dict, Any, Optional, List
from consensus_system.agent import ConsensusAgent

try:
    from praisonaiagents import Agent as PraisonAgent
    PRAISON_AVAILABLE = True
except ImportError:
    PRAISON_AVAILABLE = False
    PraisonAgent = None


class PraisonConsensusAgent(ConsensusAgent):
    """
    Consensus agent that wraps a PraisonAI agent for actual LLM execution.
    """
    
    def __init__(
        self,
        agent_id: str,
        role: str,
        instructions: str,
        initial_value: Optional[Any] = None,
        llm: str = "gpt-4",
        verbose: bool = False,
        tools: Optional[List] = None
    ):
        """
        Initialize a PraisonAI-backed consensus agent.
        
        Args:
            agent_id: Unique identifier for the agent
            role: Role/name of the agent
            instructions: Instructions/prompt for the agent
            initial_value: Initial state/value for consensus
            llm: Language model to use
            verbose: Enable verbose logging
            tools: Optional list of tools for the agent
        """
        super().__init__(agent_id, role, instructions, initial_value, llm, verbose)
        
        self.tools = tools or []
        self.praison_agent = None
        
        if PRAISON_AVAILABLE:
            self._initialize_praison_agent()
        else:
            if verbose:
                print(f"Warning: PraisonAI not available. Agent {role} running in simulation mode.")
                
    def _initialize_praison_agent(self):
        """Initialize the underlying PraisonAI agent."""
        try:
            self.praison_agent = PraisonAgent(
                name=self.role,
                instructions=self.instructions,
                llm=self.llm,
                verbose=self.verbose
            )
            if self.verbose:
                print(f"[{self.role}] PraisonAI agent initialized")
        except Exception as e:
            if self.verbose:
                print(f"[{self.role}] Failed to initialize PraisonAI agent: {e}")
            self.praison_agent = None
            
    def execute(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a task using the PraisonAI agent.
        
        Args:
            task: Task description
            context: Additional context for the task
            
        Returns:
            Result dictionary with agent's response
        """
        if self.verbose:
            print(f"[{self.role}] Executing task: {task}")
            
        # If PraisonAI agent is available, use it
        if self.praison_agent:
            try:
                # Execute the task with PraisonAI
                response = self.praison_agent.start(task)
                
                result = {
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "task": task,
                    "response": response,
                    "value": self.value,
                    "context": context or {},
                    "mode": "praison"
                }
                
                # Extract a quality score or metric from the response
                # This is a simplified example - in practice, you'd parse the response
                # to extract a meaningful consensus value
                if isinstance(response, str):
                    # Simple heuristic: longer responses might indicate more confidence
                    self.value = min(len(response) / 100.0, 10.0)
                    
            except Exception as e:
                if self.verbose:
                    print(f"[{self.role}] Error executing with PraisonAI: {e}")
                result = self._simulate_execution(task, context)
        else:
            # Fallback to simulation
            result = self._simulate_execution(task, context)
            
        if self.verbose:
            print(f"[{self.role}] Result: {result['response'][:100]}...")
            
        return result
        
    def _simulate_execution(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Simulate execution when PraisonAI is not available.
        
        Args:
            task: Task description
            context: Additional context
            
        Returns:
            Simulated result dictionary
        """
        # Simulate different responses based on role
        responses = {
            "CodeAnalyzer": f"Code analysis completed for: {task}. Found 2 potential issues.",
            "CodeReviewer": f"Code review completed for: {task}. Overall quality: Good.",
            "CodeOptimizer": f"Optimization analysis for: {task}. Suggested 3 improvements.",
            "SecurityAnalyzer": f"Security analysis for: {task}. No critical vulnerabilities found.",
            "PerformanceAnalyzer": f"Performance analysis for: {task}. Execution time acceptable."
        }
        
        response = responses.get(self.role, f"{self.role} processed: {task}")
        
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "task": task,
            "response": response,
            "value": self.value,
            "context": context or {},
            "mode": "simulation"
        }


def create_praison_agents_from_config(config: Dict[str, Any]) -> List[PraisonConsensusAgent]:
    """
    Create PraisonConsensusAgent instances from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of PraisonConsensusAgent instances
    """
    agents = []
    
    for agent_config in config['agents']:
        agent = PraisonConsensusAgent(
            agent_id=agent_config['name'],
            role=agent_config['role'],
            instructions=agent_config['instructions'],
            initial_value=agent_config.get('initial_value', 0.0),
            llm=agent_config.get('llm', 'gpt-4'),
            verbose=True,
            tools=agent_config.get('tools', [])
        )
        agents.append(agent)
        
    return agents
