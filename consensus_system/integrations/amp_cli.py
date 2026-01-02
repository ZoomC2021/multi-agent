"""
Amp CLI Integration.

Wraps the `amp` CLI for use in the consensus system.
"""

from typing import Any, Dict, List, Optional

from .base import ExternalCLIIntegration


class AmpCLIIntegration(ExternalCLIIntegration):
    """
    Integration for Amp CLI.

    Requires:
    - `amp` CLI installed
    - AMP_API_KEY environment variable set (or logged in session)

    Example:
        amp = AmpCLIIntegration(workspace="/my/project")
        result = await amp.execute("Add error handling to utils.py")
    """

    CLI_NAME = "amp"
    API_KEY_ENV_VAR = "AMP_API_KEY"
    INSTALL_HINT = "Download from ampcode.com"

    def __init__(
        self,
        workspace: str = ".",
        output_format: str = "json",
        timeout: int = 300,
        verbose: bool = False,
        force: bool = False,
        mode: str = "smart",
        use_sonnet: bool = False,
        no_ide: bool = True,
    ):
        """
        Initialize Amp CLI integration.

        Args:
            workspace: Working directory
            output_format: Output format (json/text)
            timeout: Execution timeout in seconds
            verbose: Enable verbose output
            force: Force execution without confirmations
            mode: Amp agent mode (free, rush, smart)
            use_sonnet: Use Claude Sonnet 4.5
            no_ide: Disable IDE integration (recommended for CLI use)
        """
        self.force = force
        self.mode = mode
        self.use_sonnet = use_sonnet
        self.no_ide = no_ide

        # Parent init checks requirements
        super().__init__(
            workspace=workspace, output_format=output_format, timeout=timeout, verbose=verbose
        )

    async def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a prompt using Amp CLI.

        Args:
            prompt: The task/prompt to execute
            context: Additional context

        Returns:
            Dictionary with:
            - response: Amp's response
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
                # We used --stream-json, so output should be NDJSON
                # We'll try to collect it, or just return raw if complex
                try:
                    # Attempt to parse as single JSON if possible (sometimes it's just one object)
                    # or list of objects
                    if result.stdout.strip().startswith("{"):
                        # It might be NDJSON, so wrap in list or parse last line?
                        # For safety, let's treat it as text/raw unless we have specific parsing need for Amp
                        # Amp stream-json is "Claude Code-compatible stream JSON"
                        # We'll rely on base parsing which tries to find JSON.
                        parsed = self._parse_json_output(result.stdout)
                        response = parsed.get("content", parsed.get("text", result.stdout))
                    else:
                        response = result.stdout
                        parsed = {"raw": result.stdout}
                except Exception:
                    response = result.stdout
                    parsed = {"raw": result.stdout}
            else:
                # Text mode: Amp returns the last assistant message directly
                response = result.stdout.strip()
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
        args = []

        # Mode
        if self.mode:
            args.extend(["-m", self.mode])

        # Model overrides
        if self.use_sonnet:
            args.append("--use-sonnet")

        # Dangerously allow all (Force)
        if self.force:
            args.append("--dangerously-allow-all")

        # IDE settings
        if self.no_ide:
            args.append("--no-ide")
            args.append("--no-jetbrains")

        # Output format
        if self.output_format == "json":
            args.append("--stream-json")

        # Execute prompt (must be last or properly flagged)
        args.extend(["-x", prompt])

        return args
