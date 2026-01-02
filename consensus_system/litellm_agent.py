"""
LiteLLM Integration Module

Integrates LiteLLM for multi-model LLM-based agent execution.
"""

import os
from typing import Dict, Any, Optional, List
from consensus_system.agent import ConsensusAgent

try:
    from litellm import completion

    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False


class LiteLLMAgent(ConsensusAgent):
    """
    Consensus agent that uses LiteLLM for actual LLM execution.
    Supports 100+ LLM providers through unified interface.
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
        tools: Optional[List] = None,
    ):
        """
        Initialize a LiteLLM-backed consensus agent.

        Args:
            agent_id: Unique identifier for the agent
            role: Role/name of the agent
            instructions: Instructions/prompt for the agent
            initial_value: Initial state/value for consensus
            weight: Voting weight for weighted consensus (default: 1.0)
            llm: Language model to use (e.g., "gpt-4", "gemini/gemini-1.5-pro")
            verbose: Enable verbose logging
            tools: Optional list of tools for the agent
        """
        super().__init__(
            agent_id=agent_id,
            role=role,
            instructions=instructions,
            initial_value=initial_value,
            weight=weight,
            llm=llm,
            verbose=verbose,
        )

        self.tools = tools or []

        if not LITELLM_AVAILABLE:
            raise RuntimeError("LiteLLM is not installed. Install with: pip install litellm")

        if self.verbose:
            print(f"[{self.role}] LiteLLM agent initialized with model: {self.llm}")

    def execute(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a task using LiteLLM.

        Args:
            task: Task description
            context: Additional context for the task

        Returns:
            Result dictionary with agent's response
        """
        if self.verbose:
            print(f"[{self.role}] Executing task with {self.llm}: {task[:50]}...")

        # Build full prompt with context if available
        full_prompt = task
        if context:
            context_str = "\n\nContext:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"
            full_prompt += context_str

        response = None
        error = None

        try:
            messages = [
                {"role": "system", "content": self.instructions},
                {"role": "user", "content": full_prompt},
            ]

            # Pass API key for Gemini models if available, avoiding global env mutation
            api_key = None
            if self.llm.startswith("gemini/"):
                api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

            if api_key:
                res = completion(model=self.llm, messages=messages, api_key=api_key)
            else:
                res = completion(model=self.llm, messages=messages)

            response = res.choices[0].message.content

        except Exception as e:
            error = e
            if self.verbose:
                print(f"[{self.role}] Error executing LiteLLM: {e}")
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
        }

        if self.verbose:
            response_preview = str(result.get("response", ""))[:100]
            print(f"[{self.role}] Response received: {response_preview}...")

        return result


def create_litellm_agents_from_config(config: Dict[str, Any]) -> List[LiteLLMAgent]:
    """
    Create LiteLLMAgent instances from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        List of LiteLLMAgent instances
    """
    agents = []

    for agent_config in config.get("agents", []):
        agent = LiteLLMAgent(
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
