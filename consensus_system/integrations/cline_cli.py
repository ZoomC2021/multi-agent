"""
Cline CLI Integration.

Wraps the `cline` CLI for use in the consensus system.
Ensures a server instance is running before executing prompts.
"""

import re
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
        no_interactive: bool = True,  # Default to non-interactive for automation
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
            no_interactive: Enable non-interactive mode (default True for automation)
        """
        self.model = model
        self.mode = mode
        self.oneshot = oneshot
        self.no_interactive = no_interactive
        # Address of running instance (populated by _ensure_instance)
        self.instance_address: Optional[str] = None

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
        Ensure a Cline server instance is running and get its address.

        Parses the instance list to find a SERVING instance and stores its address.
        If no instance is running, attempts to start one.
        """
        import asyncio

        try:
            # Check if any instance is running
            result = await self._run_cli(["instance", "list"])

            if result.returncode == 0 and "SERVING" in result.stdout:
                # Parse instance list to get address
                # Format:  ADDRESS (ID)    │ STATUS     │ VERSION    │ ...
                # Example: 127.0.0.1:61228 │ SERVING    │ 3.39.2     │ ...
                address = self._parse_instance_address(result.stdout)
                if address:
                    self.instance_address = address
                    if self.verbose:
                        print(f"[cline] Using existing instance at {address}")
                    return

            # No running instance found, try to start one
            if self.verbose:
                print("[cline] No running instance found. Starting one...")

            # Start a new instance in background (don't await - it's long-running)
            asyncio.create_task(self._run_cli(["instance", "new", "--verbose"]))
            # Give it a moment to start
            await asyncio.sleep(3)

            # Check again for the new instance
            result = await self._run_cli(["instance", "list"])
            if result.returncode == 0 and "SERVING" in result.stdout:
                address = self._parse_instance_address(result.stdout)
                if address:
                    self.instance_address = address
                    if self.verbose:
                        print(f"[cline] Started new instance at {address}")

        except Exception as e:
            if self.verbose:
                print(f"[cline] Warning: Could not ensure instance: {e}")
            # Continue anyway - cline might auto-start

    def _parse_instance_address(self, output: str) -> Optional[str]:
        """
        Parse cline instance list output to find a SERVING instance address.

        Prioritizes the default instance (marked with ✓), otherwise picks the first SERVING one.

        Args:
            output: Raw output from `cline instance list`

        Returns:
            Instance address (e.g., "127.0.0.1:61228") or None if not found
        """
        lines = output.split("\n")
        serving_addresses = []
        default_address = None

        for line in lines:
            # Skip header and separator lines
            if "SERVING" not in line:
                continue

            # Parse address from line
            # Format: "   127.0.0.1:61228 │ SERVING    │ 3.39.2     │ ... │ ✓"
            # Use regex to extract the address (IP:port pattern)
            match = re.search(r"(\d+\.\d+\.\d+\.\d+:\d+)", line)
            if match:
                address = match.group(1)
                serving_addresses.append(address)

                # Check if this is the default instance
                if "✓" in line:
                    default_address = address

        # Prefer default instance, otherwise use first available
        if default_address:
            return default_address
        elif serving_addresses:
            return serving_addresses[0]
        return None

    def _build_args(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Build CLI arguments for execution."""
        args = []

        # Connect to specific instance if address is known
        # This is critical - without --address, cline tries to start a new instance
        if self.instance_address:
            args.extend(["--address", self.instance_address])

        # Add the prompt
        args.append(prompt)

        # Mode selection
        if self.mode in ("plan", "act"):
            args.extend(["--mode", self.mode])

        # Oneshot mode (full autonomous)
        if self.oneshot:
            args.append("--oneshot")

        # Non-interactive mode - required for automation to avoid interactive prompts
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
