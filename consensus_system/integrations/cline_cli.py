"""
Cline CLI Integration.

Wraps the `cline` CLI for use in the consensus system.
Ensures a server instance is running before executing prompts.
"""

from typing import Any, Dict, List, Optional

from .base import ExternalCLIIntegration


class ClineCLIIntegration(ExternalCLIIntegration):
    """
    Integration for Cline CLI.

    Requires:
    - `cline` CLI installed
    - Node.js 20+ available
    - Appropriate model credentials configured

    Example:
        cline = ClineCLIIntegration(workspace="/my/project")
        result = await cline.execute("Add error handling to utils.py")
    """

    CLI_NAME = "cline"
    API_KEY_ENV_VAR = None  # Cline manages its own auth via `cline auth`
    INSTALL_HINT = "Install from https://cline.bot or via npm: npm install -g cline"

    def __init__(
        self,
        workspace: str = ".",
        output_format: str = "plain",
        timeout: int = 300,
        verbose: bool = False,
        model: Optional[str] = None,
        mode: str = "plan",
        oneshot: bool = False,
        no_interactive: bool = False,
    ):
        """
        Initialize Cline CLI integration.

        Args:
            workspace: Working directory (project path)
            output_format: Output format (text/json/rich)
            timeout: Execution timeout in seconds
            verbose: Enable verbose output
            model: Model to use (optional, cline manages models internally)
            mode: Mode of operation (plan/act)
            oneshot: Enable full autonomous mode
            no_interactive: Enable non-interactive mode
        """
        self.model = model
        self.mode = mode
        self.oneshot = oneshot
        self.no_interactive = no_interactive

        # Parent init checks requirements
        super().__init__(
            workspace=workspace, output_format=output_format, timeout=timeout, verbose=verbose
        )

    def check_requirements(self) -> None:
        """
        Override to check Cline CLI availability.
        Cline manages its own auth via `cline auth`.
        """
        import shutil
        from .base import CLINotFoundError

        if not shutil.which(self.CLI_NAME):
            raise CLINotFoundError(f"{self.CLI_NAME} CLI not found in PATH. {self.INSTALL_HINT}")
        # Note: No API key check - Cline handles auth internally

    async def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a prompt using Cline CLI.

        First ensures a server instance is running, then executes the prompt.

        Args:
            prompt: The task/prompt to execute
            context: Additional context

        Returns:
            Dictionary with:
            - response: Cline's response
            - success: Whether execution succeeded
            - raw_output: Raw CLI output
        """
        # Ensure instance is running
        await self._ensure_instance()

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
                response = parsed.get(
                    "result", parsed.get("content", parsed.get("response", result.stdout))
                )
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

    async def _ensure_instance(self) -> None:
        """
        Ensure a Cline server instance is running.

        Checks if any instance is serving, and starts one if needed.
        Note: Instance start is fire-and-forget to avoid blocking.
        """
        import asyncio
        
        try:
            # Check if any instance is running
            result = await self._run_cli(["instance", "list"])

            if result.returncode != 0 or "SERVING" not in result.stdout:
                if self.verbose:
                    print("No running instance found. Starting one...")
                # Start a new instance in background (don't await - it's long-running)
                # Fire and forget - the instance will be ready by the time we need it
                asyncio.create_task(self._run_cli(["instance", "new", "--verbose"]))
                # Give it a moment to start
                await asyncio.sleep(2)

        except Exception as e:
            if self.verbose:
                print(f"Warning: Could not ensure instance: {e}")
            # Continue anyway - cline might auto-start

    def _build_args(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Build CLI arguments for execution."""
        args = [prompt]

        # Mode selection
        if self.mode in ("plan", "act"):
            args.extend(["--mode", self.mode])

        # Oneshot mode (full autonomous)
        if self.oneshot:
            args.append("--oneshot")

        # Non-interactive mode
        if self.no_interactive:
            args.append("--no-interactive")

        # Output format (plain, json, or rich)
        if self.output_format in ("plain", "json", "rich"):
            args.extend(["--output-format", self.output_format])

        # Verbose
        if self.verbose:
            args.append("--verbose")

        # File attachments from context
        if context and "files" in context:
            files = context["files"]
            if isinstance(files, str):
                files = [files]
            for file_path in files:
                args.extend(["--file", str(file_path)])

        # Image attachments from context
        if context and "images" in context:
            images = context["images"]
            if isinstance(images, str):
                images = [images]
            for image_path in images:
                args.extend(["--image", str(image_path)])

        return args
