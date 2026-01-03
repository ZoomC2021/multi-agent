"""
Amp CLI Integration.

Wraps the `amp` CLI for use in the consensus system.
"""

import logging
import json
from typing import Any, Dict, List, Optional

from .base import ExternalCLIIntegration

logger = logging.getLogger(__name__)


class AmpCLIIntegration(ExternalCLIIntegration):
    """
    Integration for Amp CLI.

    Requires:
    - `amp` CLI installed
    - AMP_API_KEY environment variable set (or logged in session)
    - Amp credits for execute mode (free mode only works interactively)

    Note:
        Amp's 'free' mode does not support execute mode (-x). This integration
        uses execute mode, so you need credits. Use `use_sonnet=True` for
        lower token costs (Claude Sonnet vs Opus).

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
        mode: Optional[str] = None,
        use_sonnet: bool = False,
        no_ide: bool = True,
        model: Optional[str] = None,
    ):
        """
        Initialize Amp CLI integration.

        Args:
            workspace: Working directory
            output_format: Output format (json/text)
            timeout: Execution timeout in seconds
            verbose: Enable verbose output
            force: Force execution without confirmations
            mode: Amp agent mode (rush, smart). Note: 'free' mode does NOT
                  work with execute mode. Default None lets Amp decide.
            use_sonnet: Use Claude Sonnet 4.5 (recommended for lower costs)
            no_ide: Disable IDE integration (recommended for CLI use)
            model: Model parameter (accepted for compatibility but not used)
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
                # Parse each line as a JSON object
                json_objects = []
                raw_text_accumulated = []
                
                try:
                    # Split by newline and filter empty lines
                    lines = [line for line in result.stdout.split('\n') if line.strip()]
                    
                    for line in lines:
                        try:
                            obj = json.loads(line)
                            json_objects.append(obj)
                            
                            # Accumulate text content if present (common in streaming responses)
                            # Handle different potential formats (Claude-like, standard, etc.)
                            if isinstance(obj, dict):
                                content = obj.get("content") or obj.get("text") or obj.get("delta", {}).get("text")
                                if content and isinstance(content, str):
                                    raw_text_accumulated.append(content)
                                    
                        except json.JSONDecodeError:
                            # If a line isn't JSON, just ignore or log it
                            continue
                            
                    if json_objects:
                        # If we successfully parsed JSON objects
                        parsed = json_objects
                        # If we accumulated text, use that as response
                        if raw_text_accumulated:
                             response = "".join(raw_text_accumulated)
                        else:
                             # Fallback: try to extract from the last object if no text accumulated
                             last_obj = json_objects[-1]
                             if isinstance(last_obj, dict):
                                 response = last_obj.get("content", last_obj.get("text", str(last_obj)))
                             else:
                                 response = str(last_obj)
                    else:
                        # Fallback for failed parsing or no JSON found
                        parsed = {"raw": result.stdout}
                        response = result.stdout
                        
                except Exception:
                    # General safety net
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
