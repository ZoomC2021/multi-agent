"""
OpenCode CLI Integration.

Wraps the `opencode` CLI for use in the consensus system.
"""

from typing import Any, Dict, List, Optional

from .base import ExternalCLIIntegration


class OpenCodeCLIIntegration(ExternalCLIIntegration):
    """
    Integration for OpenCode CLI.

    Requires:
    - `opencode` CLI installed
    - Appropriate model/provider credentials configured

    Example:
        opencode = OpenCodeCLIIntegration(workspace="/my/project")
        result = await opencode.execute("Add error handling to utils.py")
    """

    CLI_NAME = "opencode"
    API_KEY_ENV_VAR = None  # OpenCode manages its own auth via `opencode auth`
    INSTALL_HINT = "Install from https://opencode.ai or via npm"

    def __init__(
        self,
        workspace: str = ".",
        output_format: str = "json",
        timeout: int = 300,
        verbose: bool = False,
        model: Optional[str] = None,
        continue_session: bool = False,
        session_id: Optional[str] = None,
        prompt_name: Optional[str] = None,
        agent: Optional[str] = None,
        print_logs: bool = False,
        log_level: Optional[str] = None,
    ):
        """
        Initialize OpenCode CLI integration.

        Args:
            workspace: Working directory (project path)
            output_format: Output format (json/text)
            timeout: Execution timeout in seconds
            verbose: Enable verbose output
            model: Model to use in format provider/model
            continue_session: Continue the last session
            session_id: Specific session ID to continue
            prompt_name: Prompt to use
            agent: Agent to use
            print_logs: Print logs to stderr
            log_level: Log level (DEBUG, INFO, WARN, ERROR)
        """
        self.model = model
        self.continue_session = continue_session
        self.session_id = session_id
        self.prompt_name = prompt_name
        self.agent = agent
        self.print_logs = print_logs
        self.log_level = log_level

        # Parent init checks requirements
        super().__init__(
            workspace=workspace, output_format=output_format, timeout=timeout, verbose=verbose
        )

    def check_requirements(self) -> None:
        """
        Override to check OpenCode CLI availability.
        OpenCode manages its own auth via `opencode auth`.
        """
        import shutil
        from .base import CLINotFoundError

        if not shutil.which(self.CLI_NAME):
            raise CLINotFoundError(f"{self.CLI_NAME} CLI not found in PATH. {self.INSTALL_HINT}")
        # Note: No API key check - OpenCode handles auth internally

    def _parse_ndjson_events(self, output: str) -> Dict[str, Any]:
        """
        Parse NDJSON streaming output from OpenCode CLI.
        
        Extracts structured events (step_start, text, tool_use, step_finish)
        and combines text content into a final response.
        
        Args:
            output: Raw NDJSON output (one JSON object per line)
            
        Returns:
            Dictionary with:
            - response: Combined text content
            - events: List of all parsed events
            - tool_calls: List of tool usage events
            - steps: List of step events with timing info
        """
        import json
        
        events = []
        text_parts = []
        tool_calls = []
        steps = []
        
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                events.append(event)
                
                event_type = event.get("type", "")
                part = event.get("part", {})
                
                if event_type == "text":
                    text = part.get("text", "")
                    if text:
                        text_parts.append(text)
                        
                elif event_type == "tool_use":
                    state = part.get("state", {})
                    tool_calls.append({
                        "tool": part.get("tool", "unknown"),
                        "call_id": part.get("callID", ""),
                        "status": state.get("status", ""),
                        "input": state.get("input", {}),
                        "output": state.get("output", ""),
                        "title": state.get("title", ""),
                        "time": state.get("time", {}),
                    })
                    
                elif event_type == "step_start":
                    steps.append({
                        "type": "start",
                        "timestamp": event.get("timestamp"),
                        "session_id": event.get("sessionID"),
                        "message_id": part.get("messageID"),
                    })
                    
                elif event_type == "step_finish":
                    steps.append({
                        "type": "finish",
                        "timestamp": event.get("timestamp"),
                        "reason": part.get("reason", ""),
                        "tokens": part.get("tokens", {}),
                        "cost": part.get("cost", 0),
                    })
                    
            except json.JSONDecodeError:
                # Not valid JSON, skip
                continue
        
        return {
            "response": "\n".join(text_parts),
            "events": events,
            "tool_calls": tool_calls,
            "steps": steps,
            "event_count": len(events),
        }

    async def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a prompt using OpenCode CLI.

        Uses the `opencode run` command for non-interactive execution.
        Output is captured as NDJSON streaming events for detailed visibility.

        Args:
            prompt: The task/prompt to execute
            context: Additional context

        Returns:
            Dictionary with:
            - response: OpenCode's response (combined text)
            - success: Whether execution succeeded
            - raw_output: Raw CLI output
            - events: Parsed streaming events
            - tool_calls: List of tool invocations
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

            # Parse NDJSON streaming output
            parsed = self._parse_ndjson_events(result.stdout)
            response = parsed.get("response", "")
            
            # Fallback: if no text events found, try legacy JSON parsing
            if not response and result.stdout.strip():
                legacy_parsed = self._parse_json_output(result.stdout)
                if isinstance(legacy_parsed, dict):
                    response = legacy_parsed.get(
                        "result", legacy_parsed.get("content", legacy_parsed.get("response", result.stdout))
                    )
                else:
                    response = result.stdout

            return {
                "response": response,
                "success": True,
                "raw_output": result.stdout,
                "parsed": parsed,
                "events": parsed.get("events", []),
                "tool_calls": parsed.get("tool_calls", []),
                "steps": parsed.get("steps", []),
                "cli": self.CLI_NAME,
            }

        except Exception as e:
            return {"response": "", "success": False, "error": str(e), "cli": self.CLI_NAME}

    def _build_args(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Build CLI arguments for execution."""
        # Use 'run' subcommand for non-interactive execution
        args = ["run", prompt]

        # Model selection (provider/model format)
        if self.model:
            args.extend(["--model", self.model])
            
        # Use JSON format for structured streaming output (respects output_format setting)
        if self.output_format == "json":
            args.extend(["--format", "json"])

        # Continue last session
        if self.continue_session:
            args.append("--continue")

        # Specific session ID
        if self.session_id:
            args.extend(["--session", self.session_id])

        # Prompt name
        if self.prompt_name:
            args.extend(["--prompt", self.prompt_name])

        # Agent selection
        if self.agent:
            args.extend(["--agent", self.agent])

        # Logging options
        if self.print_logs:
            args.append("--print-logs")

        if self.log_level:
            args.extend(["--log-level", self.log_level])

        return args

    async def start_server(self, port: int = 0, hostname: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Start a headless OpenCode server.

        Args:
            port: Port to listen on (0 for auto)
            hostname: Hostname to bind to

        Returns:
            Dictionary with server info
        """
        args = ["serve", "--port", str(port), "--hostname", hostname]

        try:
            result = await self._run_cli(args)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "cli": self.CLI_NAME,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "cli": self.CLI_NAME}

    async def list_models(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        List available models.

        Args:
            provider: Optional provider to filter by

        Returns:
            Dictionary with model list
        """
        args = ["models"]
        if provider:
            args.append(provider)

        try:
            result = await self._run_cli(args)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "models": result.stdout.strip().split("\n") if result.returncode == 0 else [],
                "cli": self.CLI_NAME,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "cli": self.CLI_NAME}

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get token usage and cost statistics.

        Returns:
            Dictionary with usage stats
        """
        args = ["stats"]

        try:
            result = await self._run_cli(args)
            if self.output_format == "json":
                parsed = self._parse_json_output(result.stdout)
            else:
                parsed = {"raw": result.stdout}

            return {"success": result.returncode == 0, "stats": parsed, "cli": self.CLI_NAME}
        except Exception as e:
            return {"success": False, "error": str(e), "cli": self.CLI_NAME}
