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

try:
    from litellm import completion

    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False


class PraisonNotAvailableError(RuntimeError):
    """Raised when PraisonAI is not installed but is required."""

    pass


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
        tools: Optional[List] = None,
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
        super().__init__(
            agent_id=agent_id,
            role=role,
            instructions=instructions,
            initial_value=initial_value,
            llm=llm,
            verbose=verbose,
        )

        self.tools = tools or []
        self.praison_agent = None

        if not PRAISON_AVAILABLE and not LITELLM_AVAILABLE:
            raise PraisonNotAvailableError(
                "Neither PraisonAI nor LiteLLM is installed. Install with: pip install praisonaiagents litellm"
            )

        self._initialize_praison_agent()

    def _initialize_praison_agent(self):
        """Initialize the underlying PraisonAI agent."""
        if PRAISON_AVAILABLE:
            try:
                self.praison_agent = PraisonAgent(
                    name=self.role,
                    instructions=self.instructions,
                    llm=self.llm,
                    verbose=self.verbose,
                )
                if self.verbose:
                    print(f"[{self.role}] PraisonAI agent initialized with LLM: {self.llm}")
            except Exception as e:
                if self.verbose:
                    print(f"[{self.role}] Warning: Failed to initialize PraisonAgent: {e}")
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
            print(f"[{self.role}] Executing task: {task[:50]}...")

        # Build full prompt with context if available
        full_prompt = task
        if context:
            context_str = "\n\nContext:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"
            full_prompt += context_str

        response = None
        error = None

        # Try PraisonAI first
        if self.praison_agent:
            try:
                response = self.praison_agent.start(full_prompt)
            except Exception as e:
                error = e
                if self.verbose:
                    print(f"[{self.role}] Error executing PraisonAI agent: {e}")

        # Fallback to LiteLLM if PraisonAI failed or not available
        if response is None and LITELLM_AVAILABLE:
            try:
                if self.verbose:
                    print(f"[{self.role}] Falling back to direct LiteLLM execution with {self.llm}")

                messages = [
                    {"role": "system", "content": self.instructions},
                    {"role": "user", "content": full_prompt},
                ]

                res = completion(model=self.llm, messages=messages)
                response = res.choices[0].message.content
                error = None  # Clear error if fallback succeeded

            except Exception as e:
                error = e
                if self.verbose:
                    print(f"[{self.role}] Error executing LiteLLM fallback: {e}")

        if response is None:
            response = f"Error generating response: {str(error)}"

        # Extract a quality score or metric from the response
        if isinstance(response, str):
            self.update_value(min(len(response) / 100.0, 10.0))
        else:
            self.update_value(0.0)

        result = {
            "agent_id": self.agent_id,
            "role": self.role,
            "task": task,
            "response": response,
            "value": self.value,
            "context": context or {},
            "mode": "praison" if self.praison_agent and not error else "litellm",
        }

        if self.verbose:
            response_preview = str(result.get("response", ""))[:100]
            print(f"[{self.role}] Result: {response_preview}...")

        return result


def create_praison_agents_from_config(config: Dict[str, Any]) -> List[PraisonConsensusAgent]:
    """
    Create PraisonConsensusAgent instances from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        List of PraisonConsensusAgent instances
    """
    agents = []

    for agent_config in config.get("agents", []):
        agent = PraisonConsensusAgent(
            agent_id=agent_config.get("name", "unknown"),
            role=agent_config.get("role", "Agent"),
            instructions=agent_config.get("instructions", ""),
            initial_value=agent_config.get("initial_value", 0.0),
            llm=agent_config.get("llm", "gpt-4"),
            verbose=True,
            tools=agent_config.get("tools", []),
        )
        agents.append(agent)

    return agents
