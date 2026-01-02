"""
Claude Code CLI Integration.

Wraps the `claude` CLI for use in the consensus system.
"""

from typing import Any, Dict, List, Optional

from .base import ExternalCLIIntegration


class ClaudeCodeIntegration(ExternalCLIIntegration):
    """
    Integration for Claude Code CLI.
    
    Requires:
    - `claude` CLI installed (npm install -g @anthropic-ai/claude-code)
    - ANTHROPIC_API_KEY environment variable set
    
    Example:
        claude = ClaudeCodeIntegration(workspace="/my/project")
        result = await claude.execute("Find bugs in main.py")
    """
    
    CLI_NAME = "claude"
    API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
    INSTALL_HINT = "npm install -g @anthropic-ai/claude-code"
    
    def __init__(
        self,
        workspace: str = ".",
        output_format: str = "json",
        timeout: int = 300,
        verbose: bool = False,
        skip_permissions: bool = True,
        system_prompt: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
        max_turns: int = 10,
        model: Optional[str] = None
    ):
        """
        Initialize Claude Code integration.
        
        Args:
            workspace: Working directory
            output_format: Output format (json/text)
            timeout: Execution timeout in seconds
            verbose: Enable verbose output
            skip_permissions: Skip permission prompts (--dangerously-skip-permissions)
            system_prompt: Custom system prompt
            allowed_tools: List of allowed tools (Read, Write, Bash, etc.)
            max_turns: Maximum conversation turns
            model: Model to use (e.g., claude-sonnet-4-20250514, claude-opus-4-20250514)
        """
        self.skip_permissions = skip_permissions
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools
        self.max_turns = max_turns
        self.model = model
        
        # Parent init checks requirements
        super().__init__(
            workspace=workspace,
            output_format=output_format,
            timeout=timeout,
            verbose=verbose
        )
    
    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a prompt using Claude Code CLI.
        
        Args:
            prompt: The task/prompt to execute
            context: Additional context (e.g., file paths)
            
        Returns:
            Dictionary with:
            - response: Claude's response text
            - success: Whether execution succeeded
            - raw_output: Raw CLI output
            - cost: Token/cost information if available
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
                    "cli": self.CLI_NAME
                }
            
            # Parse output based on format
            if self.output_format == "json":
                parsed = self._parse_json_output(result.stdout)
                response = parsed.get("result", parsed.get("response", result.stdout))
            else:
                response = result.stdout
                parsed = {"raw": result.stdout}
            
            return {
                "response": response,
                "success": True,
                "raw_output": result.stdout,
                "parsed": parsed,
                "cli": self.CLI_NAME
            }
            
        except Exception as e:
            return {
                "response": "",
                "success": False,
                "error": str(e),
                "cli": self.CLI_NAME
            }
    
    def _build_args(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Build CLI arguments for execution."""
        args = ["--print"]  # Non-interactive mode
        
        # Model selection
        if self.model:
            args.extend(["--model", self.model])
        
        # Output format
        if self.output_format == "json":
            args.extend(["--output-format", "json"])
        
        # Skip permission prompts for automated use
        if self.skip_permissions:
            args.append("--dangerously-skip-permissions")
        
        # System prompt
        if self.system_prompt:
            args.extend(["--system-prompt", self.system_prompt])
        
        # Allowed tools
        if self.allowed_tools:
            for tool in self.allowed_tools:
                args.extend(["--allowedTools", tool])
        
        # Max turns
        args.extend(["--max-turns", str(self.max_turns)])
        
        # Add context files if provided
        if context and context.get("files"):
            for file_path in context["files"]:
                args.extend(["--add-file", file_path])
        
        # Finally, the prompt
        args.append(prompt)
        
        return args
