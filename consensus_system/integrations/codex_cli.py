"""
OpenAI Codex CLI Integration.

Wraps the `codex` CLI for use in the consensus system.
"""

import json
from typing import Any, Dict, List, Optional

from .base import ExternalCLIIntegration


class CodexCLIIntegration(ExternalCLIIntegration):
    """
    Integration for OpenAI Codex CLI.

    Requires:
    - `codex` CLI installed (npm install -g @openai/codex)
    - Codex handles its own authentication (via `codex login`)

    Example:
        codex = CodexCLIIntegration(workspace="/my/project", full_auto=True)
        result = await codex.execute("Fix the authentication bug")
    """

    CLI_NAME = "codex"
    API_KEY_ENV_VAR = None  # Codex CLI handles its own auth
    INSTALL_HINT = "npm install -g @openai/codex"

    def __init__(
        self,
        workspace: str = ".",
        output_format: str = "json",
        timeout: int = 300,
        verbose: bool = False,
        full_auto: bool = True,
        approval_mode: str = "full-auto",
        sandbox: str = "workspace-write",  # Valid: read-only, workspace-write, danger-full-access
        model: Optional[str] = None,
    ):
        """
        Initialize Codex CLI integration.

        Args:
            workspace: Working directory
            output_format: Output format (json/text)
            timeout: Execution timeout in seconds
            verbose: Enable verbose output
            full_auto: Enable full-auto mode (no confirmations)
            approval_mode: Approval mode (full-auto, auto-edit, suggest, manual)
            sandbox: Sandbox mode (read-only, workspace-write, danger-full-access)
            model: Model to use (default: codex's default)
        """
        self.full_auto = full_auto
        self.approval_mode = approval_mode
        self.sandbox = sandbox
        self.model = model

        # Parent init checks requirements
        super().__init__(
            workspace=workspace, output_format=output_format, timeout=timeout, verbose=verbose
        )

    async def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a prompt using Codex CLI.

        Args:
            prompt: The task/prompt to execute
            context: Additional context

        Returns:
            Dictionary with:
            - response: Codex's response/result
            - success: Whether execution succeeded
            - raw_output: Raw CLI output
            - files_modified: List of modified files if available
        """
        args = self._build_args(prompt, context)

        try:
            result = await self._run_cli(args)

            if result.returncode != 0:
                return {
                    "response": "",
                    "success": False,
                    "raw_output": result.stdout,
                    "error": result.stderr or f"CLI exited with code {result.returncode}",
                    "cli": self.CLI_NAME,
                }

            # Parse output based on format
            if self.output_format == "json":
                parsed = self._parse_json_output(result.stdout)
                # Handle case where parsed is a list (JSON array) not a dict
                if isinstance(parsed, dict):
                    # Codex may return structured response
                    response = parsed.get("result", parsed.get("message", result.stdout))
                    files_modified = parsed.get("files_modified", [])
                else:
                    # JSON array or other non-dict type - use raw output
                    response = result.stdout
                    files_modified = []
            else:
                response = result.stdout
                parsed = {"raw": result.stdout}
                files_modified = []

            return {
                "response": response,
                "success": True,
                "raw_output": result.stdout,
                "parsed": parsed,
                "files_modified": files_modified,
                "cli": self.CLI_NAME,
            }

        except Exception as e:
            return {"response": "", "success": False, "error": str(e), "cli": self.CLI_NAME}

    def _build_args(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Build CLI arguments for execution."""
        # Use 'exec' command for non-interactive execution
        args = ["exec"]

        # Approval mode
        if self.full_auto:
            args.append("--full-auto")
        # Note: 'exec' command might not support --approval-mode or -a in the same way
        # as interactive mode. If not full_auto, we rely on default behavior or
        # further investigation of flags. For now, supporting full-auto is priority.

        # Sandbox mode
        if self.sandbox:
            args.extend(["--sandbox", self.sandbox])

        # Model
        if self.model:
            args.extend(["--model", self.model])

        # JSON output
        if self.output_format == "json":
            args.append("--json")

        # Add the prompt
        args.append(prompt)

        return args

    def _parse_json_output(self, output: str) -> Dict[str, Any]:
        """
        Parse JSONL output from Codex CLI.

        Args:
            output: Raw CLI output (JSON Lines)

        Returns:
            Parsed dictionary with 'message' containing aggregated response text
        """
        response_text = []
        events = []

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                events.append(event)

                # Extract text from agent messages
                # Format: {"type":"item.completed","item":{"type":"agent_message","text":"..."}}
                if event.get("type") == "item.completed":
                    item = event.get("item", {})
                    if item.get("type") == "agent_message":
                        text = item.get("text", "")
                        if text:
                            response_text.append(text)

            except json.JSONDecodeError:
                # Ignore non-JSON lines (though --json should produce only JSONL)
                pass

        full_response = "\n".join(response_text)

        # If no JSONL parsed but we have output, fallback to raw
        if not events and output.strip():
            full_response = output

        return {
            "message": full_response,
            "events": events,
            "files_modified": [],  # TODO: Parse files modified from events if available
        }
