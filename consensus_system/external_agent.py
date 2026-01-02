"""
External CLI Consensus Agent.

Wraps external CLI integrations (Claude, Codex, Gemini, Cursor) as consensus agents.
"""

import asyncio
import concurrent.futures
from typing import Any, Dict, List, Optional

from consensus_system.agent import ConsensusAgent
from consensus_system.integrations import (
    ExternalCLIIntegration,
    get_integration_class,
    get_available_integrations,
)


class ExternalCLIConsensusAgent(ConsensusAgent):
    """
    Consensus agent backed by an external coding CLI.

    This agent uses external AI coding CLIs (Claude Code, Codex, Gemini, Cursor)
    to execute tasks and participate in consensus.

    Follows fail-fast design: raises errors immediately if CLI or API key is missing.

    Example:
        agent = ExternalCLIConsensusAgent(
            agent_id="claude_analyzer",
            role="ClaudeAnalyzer",
            instructions="Analyze code for bugs",
            cli_type="claude",
            workspace="/my/project"
        )
        result = await agent.execute_async("Find bugs in main.py")
    """

    def __init__(
        self,
        agent_id: str,
        role: str,
        instructions: str,
        cli_type: str,
        workspace: str = ".",
        initial_value: Optional[Any] = None,
        weight: float = 1.0,  # Added weight parameter
        verbose: bool = False,
        **cli_options,
    ):
        """
        Initialize an external CLI consensus agent.

        Args:
            agent_id: Unique identifier for the agent
            role: Role/name of the agent
            instructions: Instructions for the agent (used as system prompt)
            cli_type: Type of CLI to use (claude, codex, gemini, cursor)
            workspace: Working directory for CLI operations
            initial_value: Initial value for consensus
            verbose: Enable verbose output
            **cli_options: Additional options passed to the CLI integration

        Raises:
            ValueError: If cli_type is not supported
            CLINotFoundError: If the CLI is not installed
            APIKeyMissingError: If required API key is not set
        """
        super().__init__(
            agent_id=agent_id,
            role=role,
            instructions=instructions,
            initial_value=initial_value,
            weight=weight,
            llm=f"external:{cli_type}",  # Mark as external CLI
            verbose=verbose,
        )

        self.cli_type = cli_type.lower()
        self.workspace = workspace
        self.cli_options = cli_options

        # Get integration class - fails fast if not found
        integration_class = get_integration_class(self.cli_type)
        if integration_class is None:
            available = list(get_available_integrations().keys())
            raise ValueError(f"Unsupported CLI type: {cli_type}. Supported: {', '.join(available)}")

        # Initialize integration - fails fast if CLI/key missing
        # Build kwargs specific to each CLI type
        init_kwargs = {"workspace": workspace, "verbose": verbose, **cli_options}

        # Claude-specific: pass system_prompt
        if self.cli_type == "claude":
            init_kwargs["system_prompt"] = instructions

        self.integration: ExternalCLIIntegration = integration_class(**init_kwargs)

        if verbose:
            print(f"[{role}] Initialized with {cli_type} CLI")

    def execute(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a task synchronously (wraps async execute).

        Args:
            task: Task description
            context: Additional context

        Returns:
            Result dictionary with agent's response
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If we are in an event loop, we must run this in a separate thread
            # with its own event loop to avoid blocking the current one
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._run_isolated_async, task, context)
                return future.result()
        else:
            # If no event loop is running, we can just run it directly
            return asyncio.run(self.execute_async(task, context))

    def _run_isolated_async(self, task: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Helper to run async execution in a dedicated thread/loop."""
        return asyncio.run(self.execute_async(task, context))

    async def execute_async(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a task asynchronously using the external CLI.

        Args:
            task: Task description
            context: Additional context (e.g., file paths)

        Returns:
            Result dictionary with:
            - agent_id: Agent identifier
            - role: Agent role
            - task: Original task
            - response: CLI response
            - value: Consensus value
            - success: Whether execution succeeded
            - cli: CLI type used
        """
        if self.verbose:
            print(f"[{self.role}] Executing: {task}")

        # Build full prompt with instructions
        full_prompt = f"{self.instructions}\n\nTask: {task}"

        # Execute via CLI integration
        result = await self.integration.execute(full_prompt, context)

        # Extract response and update consensus value
        response = result.get("response", "")
        success = result.get("success", False)

        if success and response:
            # Use response quality as consensus value
            # More detailed responses indicate higher confidence
            quality_score = min(len(response) / 100.0, 10.0)
            self.update_value(quality_score)
        else:
            # Failed execution gets low score
            self.update_value(0.0)

        agent_result = {
            "agent_id": self.agent_id,
            "role": self.role,
            "task": task,
            "response": response,
            "value": self.value,
            "context": context or {},
            "success": success,
            "cli": self.cli_type,
            "mode": "external_cli",
        }

        if not success:
            agent_result["error"] = result.get("error", "Unknown error")

        if self.verbose:
            preview = response[:100] if response else "(no response)"
            print(f"[{self.role}] Result: {preview}...")

        return agent_result

    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the agent."""
        state = super().get_state()
        state.update(
            {
                "cli_type": self.cli_type,
                "workspace": self.workspace,
            }
        )
        return state

    def __repr__(self) -> str:
        return (
            f"ExternalCLIConsensusAgent("
            f"id={self.agent_id}, role={self.role}, "
            f"cli={self.cli_type}, value={self.value})"
        )


def create_external_cli_agents(
    cli_types: List[str], task_instructions: str, workspace: str = ".", verbose: bool = False
) -> List[ExternalCLIConsensusAgent]:
    """
    Create multiple external CLI agents for consensus.

    Args:
        cli_types: List of CLI types to create (claude, codex, gemini, cursor)
        task_instructions: Instructions for all agents
        workspace: Working directory
        verbose: Enable verbose output

    Returns:
        List of ExternalCLIConsensusAgent instances

    Raises:
        CLINotFoundError/APIKeyMissingError: If any CLI is not properly configured
    """
    agents = []

    for i, cli_type in enumerate(cli_types):
        agent = ExternalCLIConsensusAgent(
            agent_id=f"{cli_type}_agent_{i}",
            role=f"{cli_type.capitalize()}Analyzer",
            instructions=task_instructions,
            cli_type=cli_type,
            workspace=workspace,
            initial_value=0.0,
            verbose=verbose,
        )
        agents.append(agent)

    return agents
