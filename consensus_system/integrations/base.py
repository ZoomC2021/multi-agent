"""
Base class for external CLI integrations.

All CLI integrations follow fail-fast design: they raise errors immediately
if required CLIs or API keys are missing, rather than falling back to simulation.
"""

import asyncio
import json
import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional


class CLINotFoundError(RuntimeError):
    """Raised when a required CLI tool is not found in PATH."""

    pass


class APIKeyMissingError(EnvironmentError):
    """Raised when a required API key environment variable is not set."""

    pass


class ExternalCLIIntegration(ABC):
    """
    Abstract base class for external coding CLI integrations.

    Subclasses must implement:
    - CLI_NAME: The name of the CLI executable
    - API_KEY_ENV_VAR: The environment variable for the API key (optional)
    - check_requirements(): Validate CLI and API key availability
    - execute(): Execute a prompt using the CLI
    """

    CLI_NAME: str = ""
    API_KEY_ENV_VAR: Optional[str] = None  # Optional - CLIs handle their own auth
    INSTALL_HINT: str = ""
    REQUIRE_API_KEY: bool = False  # Set to True if API key is strictly required

    def __init__(
        self,
        workspace: str = ".",
        output_format: str = "json",
        timeout: int = 300,
        verbose: bool = False,
    ):
        """
        Initialize the CLI integration.

        Args:
            workspace: Working directory for CLI operations
            output_format: Output format (json/text)
            timeout: Execution timeout in seconds
            verbose: Enable verbose output

        Raises:
            CLINotFoundError: If the CLI is not installed
            APIKeyMissingError: If required API key is not set
        """
        self.workspace = os.path.abspath(workspace)
        self.output_format = output_format
        self.timeout = timeout
        self.verbose = verbose

        # Fail fast: check requirements on initialization
        self.check_requirements()

    def check_requirements(self) -> None:
        """
        Check that all requirements are met.

        Raises:
            CLINotFoundError: If CLI is not found in PATH
            APIKeyMissingError: If required API key is not set (only if REQUIRE_API_KEY=True)
        """
        # Check workspace existence
        if not os.path.exists(self.workspace):
            try:
                os.makedirs(self.workspace, exist_ok=True)
            except Exception as e:
                raise RuntimeError(f"Could not create workspace directory {self.workspace}: {e}")

        # Check CLI availability
        if not self.CLI_NAME:
             raise ValueError("CLI_NAME must be defined in subclass")

        if not shutil.which(self.CLI_NAME):
            hint = f" Install: {self.INSTALL_HINT}" if self.INSTALL_HINT else ""
            raise CLINotFoundError(f"{self.CLI_NAME} CLI not found in PATH.{hint}")

        # Check API key only if strictly required
        # Most CLIs handle their own auth (e.g., `claude auth login`)
        if self.REQUIRE_API_KEY and self.API_KEY_ENV_VAR and not os.getenv(self.API_KEY_ENV_VAR):
            raise APIKeyMissingError(f"{self.API_KEY_ENV_VAR} environment variable not set")

    @abstractmethod
    async def execute(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a prompt using the CLI.

        Args:
            prompt: The task/prompt to execute
            context: Additional context (e.g., file paths, instructions)

        Returns:
            Dictionary with execution results including:
            - response: The CLI's response text
            - success: Whether execution succeeded
            - raw_output: Raw CLI output
            - error: Error message if failed
        """
        pass

    async def stream(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream output from the CLI execution.

        Default implementation yields a single result from execute().
        Subclasses can override for real streaming support.

        Args:
            prompt: The task/prompt to execute
            context: Additional context

        Yields:
            Dictionaries with streaming events/content
        """
        result = await self.execute(prompt, context)
        yield result

    async def _run_cli(
        self, args: List[str], input_text: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """
        Run the CLI with given arguments.

        Args:
            args: Command line arguments (without the CLI name)
            input_text: Optional input to send to stdin

        Returns:
            CompletedProcess with stdout, stderr, returncode

        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
        """
        # Build command list for CompletedProcess result
        cmd = [self.CLI_NAME] + list(args)

        if self.verbose:
            import shlex
            quoted_cmd = [self.CLI_NAME] + [shlex.quote(arg) for arg in args]
            print(f"[{self.CLI_NAME}] Running: {' '.join(quoted_cmd)}")

        # Validate arguments (Security fix)
        # Ensure shell=False is used (implicit in create_subprocess_exec)
        # and validate arguments are safe strings
        forbidden_chars = [";", "&", "|", "`", "$", "(", ")", ">", "<"]
        for arg in args:
            if not isinstance(arg, str):
                raise ValueError(f"All CLI arguments must be strings, got: {type(arg)}")
            
            # Strict validation: prevent common shell injection characters
            # potentially embedded even if shell=False (defense in depth)
            for char in forbidden_chars:
                if char in arg:
                    # Security: Block execution on suspicious shell syntax
                    raise ValueError(
                        f"CLI argument contains forbidden shell character '{char}': {arg!r}. "
                        "This is blocked for security reasons."
                    )


        # Initialize process to None to avoid UnboundLocalError
        process = None

        try:
            # Use create_subprocess_exec for better control (Zombie process fix)
            process = await asyncio.create_subprocess_exec(
                self.CLI_NAME,
                *args,
                stdin=asyncio.subprocess.PIPE if input_text else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace,
            )

            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(input=input_text.encode() if input_text else None),
                timeout=self.timeout,
            )

            # Decode with error handling for non-UTF-8 output
            returncode = process.returncode if process.returncode is not None else -1
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=returncode,
                stdout=stdout_data.decode(errors="replace"),
                stderr=stderr_data.decode(errors="replace"),
            )
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(f"{self.CLI_NAME} execution timed out after {self.timeout}s")
        except Exception as e:
            # Handle creation errors (e.g. file not found)
            if isinstance(e, FileNotFoundError):
                raise CLINotFoundError(f"{self.CLI_NAME} executable not found")
            raise e
        finally:
            # Ensure subprocess is cleaned up in all cases
            if process is not None and process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except Exception as cleanup_error:
                    import sys
                    print(f"[{self.CLI_NAME}] Warning: Could not clean up process: {cleanup_error}", file=sys.stderr)

    def _parse_json_output(self, output: str) -> Any:
        """
        Parse JSON output from CLI.

        Handles single-line JSON, multi-line (pretty-printed) JSON, and NDJSON.

        Args:
            output: Raw CLI output

        Returns:
            Parsed JSON as dictionary/list, or {"raw": output} if parsing fails
        """
        # First, try parsing the entire output as JSON
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON using bracket-balancing for multi-line JSON
        # This handles pretty-printed JSON that spans multiple lines
        depth = 0
        start = None
        in_string = False
        escape_next = False
        bracket_char = None  # Track whether we're looking for {} or []
        
        for i, char in enumerate(output):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
                
            if char in '{[':
                if depth == 0:
                    start = i
                    bracket_char = char
                if (bracket_char == '{' and char == '{') or (bracket_char == '[' and char == '['):
                    depth += 1
                elif bracket_char is None:
                    depth += 1
            elif char in '}]':
                matching = (bracket_char == '{' and char == '}') or (bracket_char == '[' and char == ']')
                if matching or bracket_char is None:
                    depth -= 1
                if depth == 0 and start is not None:
                    try:
                        result = json.loads(output[start:i+1])
                        return result
                    except json.JSONDecodeError:
                        pass
                    start = None
                    bracket_char = None
        
        # Fallback: try line-by-line for simple single-line JSON
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("{") or line.startswith("["):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        
        return {"raw": output}

    def as_tool(self):
        """
        Convert this integration to a tool that can be used by agents.

        Returns:
            A callable tool function
        """

        async def tool(prompt: str) -> str:
            result = await self.execute(prompt)
            return result.get("response", str(result))

        tool.__name__ = f"{self.CLI_NAME}_tool"
        tool.__doc__ = f"Execute a task using {self.CLI_NAME} CLI"
        return tool

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(workspace={self.workspace!r}, cli={self.CLI_NAME!r})"
