"""
Qwen Code CLI Integration.

Wraps the `qwen` CLI for use in the consensus system.
"""

from typing import Any, Dict, List, Optional
import json

from .base import ExternalCLIIntegration


class QwenCLIIntegration(ExternalCLIIntegration):
    """
    Integration for Qwen Code CLI.

    Requires:
    - `qwen` CLI installed

    Example:
    qwen = QwenCLIIntegration(workspace="/my/project")
    result = await qwen.execute("Find bugs in main.py")
    """

    CLI_NAME = "qwen"
    INSTALL_HINT = "Visit Qwen Code documentation for installation instructions"

    def __init__(
        self,
        workspace: str = ".",
        output_format: str = "json",
        timeout: int = 300,
        verbose: bool = False,
        model: Optional[str] = None,
        yolo: bool = True,
    ):
        """
        Initialize Qwen Code integration.

        Args:
            workspace: Working directory
            output_format: Output format (json/text)
            timeout: Execution timeout in seconds
            verbose: Enable verbose output
            model: Model to use
            yolo: Automatically accept all actions
        """
        self.model = model
        self.yolo = yolo

        # Parent init checks requirements
        super().__init__(
            workspace=workspace, output_format=output_format, timeout=timeout, verbose=verbose
        )

    async def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a prompt using Qwen Code CLI.

        Args:
            prompt: The task/prompt to execute
            context: Additional context (e.g., file paths)

        Returns:
            Dictionary with execution results
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
                    # Some CLIs put the final answer in a 'response' or 'result' field
                    response = parsed.get("response", parsed.get("result", result.stdout))
                else:
                    # JSON array or other non-dict type - use raw output
                    response = result.stdout
            else:
                response = result.stdout
                parsed = {"raw": result.stdout}

            return {
                "response": response,
                "success": True,
                "raw_output": result.stdout,
                "parsed": parsed,
                "cli": self.CLI_NAME,
            }

        except Exception as e:
            return {"response": "", "success": False, "error": str(e), "cli": self.CLI_NAME}

    def _build_args(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Build CLI arguments for execution."""
        # Use positional prompt for one-shot
        args = []

        # Model selection
        if self.model:
            args.extend(["--model", self.model])

        # Output format
        if self.output_format:
            args.extend(["--output-format", self.output_format])

        # YOLO mode for automation
        if self.yolo:
            args.append("--yolo")

        # Finally, the positional prompt
        # We append the prompt at the end
        args.append(prompt)

        return args
