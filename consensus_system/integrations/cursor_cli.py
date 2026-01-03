"""
Cursor CLI Integration.

Wraps the `cursor` CLI for use in the consensus system.
"""

from typing import Any, Dict, List, Optional

from .base import ExternalCLIIntegration


class CursorCLIIntegration(ExternalCLIIntegration):
    """
    Integration for Cursor CLI.

    Requires:
    - `cursor` CLI installed
    - CURSOR_API_KEY environment variable set (or logged in session)

    Example:
        cursor = CursorCLIIntegration(workspace="/my/project")
        result = await cursor.execute("Add error handling to utils.py")
    """

    CLI_NAME = "cursor-agent"
    API_KEY_ENV_VAR = "CURSOR_API_KEY"
    INSTALL_HINT = "npm install -g cursor-agent or download from cursor.sh"

    def __init__(
        self,
        workspace: str = ".",
        output_format: str = "json",
        timeout: int = 300,
        verbose: bool = False,
        force: bool = False,
        model: Optional[str] = None,
        stream_partial: bool = False,
        resume_session: Optional[str] = None,
    ):
        """
        Initialize Cursor CLI integration.

        Args:
            workspace: Working directory
            output_format: Output format (json/text)
            timeout: Execution timeout in seconds
            verbose: Enable verbose output
            force: Force execution without confirmations
            model: Model to use (default: cursor's default)
            stream_partial: Enable partial streaming
            resume_session: Session ID to resume
        """
        self.force = force
        self.model = model
        self.stream_partial = stream_partial
        self.resume_session = resume_session

        # Parent init checks requirements
        super().__init__(
            workspace=workspace, output_format=output_format, timeout=timeout, verbose=verbose
        )

    def check_requirements(self) -> None:
        """
        Override to make API key optional for Cursor.
        Cursor can work with logged-in session without explicit API key.
        """
        import shutil
        from .base import CLINotFoundError

        if not shutil.which(self.CLI_NAME):
            raise CLINotFoundError(f"{self.CLI_NAME} CLI not found in PATH. {self.INSTALL_HINT}")
        
        # Call parent to ensure any other base checks run (except API key which we handle as optional)
        # We temporarily unset REQUIRE_API_KEY for the parent check if needed, 
        # but since parent only checks it if REQUIRE_API_KEY is True, and we didn't set it to True on class, we are fine.
        super().check_requirements()
        
        # Note: CURSOR_API_KEY is optional, Cursor can use session auth

    async def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a prompt using Cursor CLI.

        Args:
            prompt: The task/prompt to execute
            context: Additional context

        Returns:
            Dictionary with:
            - response: Cursor's response
            - success: Whether execution succeeded
            - raw_output: Raw CLI output
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
                    # cursor-agent returns {"type":"result", "result": "..."} format
                    response = parsed.get(
                        "result", parsed.get("content", parsed.get("response", result.stdout))
                    )
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
        # Prompt is positional argument (first)
        args = [prompt]

        # Print mode for headless/non-interactive use
        args.append("--print")

        # Force mode - auto-approve commands
        if self.force:
            args.append("--force")

        # Model selection
        if self.model:
            args.extend(["--model", self.model])

        # Output format
        if self.output_format == "json":
            args.extend(["--output-format", "json"])

        # Streaming
        if self.stream_partial:
            args.append("--stream-partial-output")

        # Resume session
        if self.resume_session:
            args.extend(["--resume", self.resume_session])

        # Workspace
        if self.workspace and self.workspace != ".":
            args.extend(["--workspace", self.workspace])

        return args
