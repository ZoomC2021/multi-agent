"""
Google Gemini CLI Integration.

Wraps the `gemini` CLI for use in the consensus system.
"""

from typing import Any, Dict, List, Optional

from .base import ExternalCLIIntegration


class GeminiCLIIntegration(ExternalCLIIntegration):
    """
    Integration for Google Gemini CLI.

    Requires:
    - `gemini` CLI installed (npm install -g @google/gemini-cli or pip install gemini-cli)
    - GEMINI_API_KEY environment variable set

    Example:
        gemini = GeminiCLIIntegration(workspace="/my/project", model="gemini-2.5-flash")
        result = await gemini.execute("Analyze codebase for issues")
    """

    CLI_NAME = "gemini"
    API_KEY_ENV_VAR = "GEMINI_CLI_API_KEY"  # Use distinct var for CLI if needed, but not required
    INSTALL_HINT = "npm install -g @google/gemini-cli or pip install gemini-cli"
    REQUIRE_API_KEY = False  # Gemini CLI handles its own auth

    def __init__(
        self,
        workspace: str = ".",
        output_format: str = "json",
        timeout: int = 300,
        verbose: bool = False,
        model: str = "gemini-2.5-flash",
        include_directories: Optional[List[str]] = None,
        sandbox: bool = True,
    ):
        """
        Initialize Gemini CLI integration.

        Args:
            workspace: Working directory
            output_format: Output format (json/text)
            timeout: Execution timeout in seconds
            verbose: Enable verbose output
            model: Gemini model to use
            include_directories: Additional directories to include in context
            sandbox: Enable sandbox mode
        """
        self.model = model
        self.include_directories = include_directories or []
        self.sandbox = sandbox

        # Parent init checks requirements
        super().__init__(
            workspace=workspace, output_format=output_format, timeout=timeout, verbose=verbose
        )

    async def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a prompt using Gemini CLI.

        Args:
            prompt: The task/prompt to execute
            context: Additional context

        Returns:
            Dictionary with:
            - response: Gemini's response
            - success: Whether execution succeeded
            - raw_output: Raw CLI output
            - token_stats: Token usage statistics if available
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
                response = parsed.get("response", parsed.get("text", result.stdout))
                token_stats = parsed.get("usage", {})
            else:
                response = result.stdout
                parsed = {"raw": result.stdout}
                token_stats = {}

            return {
                "response": response,
                "success": True,
                "raw_output": result.stdout,
                "parsed": parsed,
                "token_stats": token_stats,
                "cli": self.CLI_NAME,
            }

        except Exception as e:
            return {"response": "", "success": False, "error": str(e), "cli": self.CLI_NAME}

    async def execute_with_stats(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Execute and return both result and token statistics.

        Returns:
            Tuple of (result_dict, stats_dict)
        """
        result = await self.execute(prompt, context)
        stats = result.get("token_stats", {})
        return result, stats

    def _build_args(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Build CLI arguments for execution."""
        args = []

        # Model selection
        if self.model:
            args.extend(["--model", self.model])

        # Output format (Gemini uses --output-format, not --json)
        if self.output_format == "json":
            args.extend(["--output-format", "json"])

        # Sandbox mode
        if self.sandbox:
            args.append("--sandbox")

        # Auto-approve (YOLO mode for headless execution)
        args.append("--yolo")

        # Include directories
        for dir_path in self.include_directories:
            args.extend(["--include-directories", dir_path])

        # Add the prompt as positional argument
        args.append(prompt)

        return args
