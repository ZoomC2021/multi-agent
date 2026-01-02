#!/usr/bin/env python3
"""
Bug Finder Example - Consensus-based Bug Detection

This example demonstrates using multiple AI coding CLIs (Claude, Codex, Gemini)
to find bugs through consensus. Each agent analyzes the same code and the system
reaches consensus on identified issues.

Usage:
    python examples/bug_finder_example.py /path/to/code/to/analyze

Requirements:
    - At least one CLI installed (claude, codex, gemini, or cursor)
    - Corresponding API keys set
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Map GEMINI_API_KEY to GOOGLE_API_KEY for LiteLLM compatibility
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    # Avoid modifying global os.environ if possible, but LiteLLM reads from env.
    # We will prefer to pass api_key explicitly to agents if the library supports it.
    # For now, we only set it if strictly necessary and try to scope it.
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

from consensus_system import (
    ConsensusManager,
    ExternalCLIConsensusAgent,
    LiteLLMAgent,
    get_available_integrations,
)

DEFAULT_WORKER_CONFIGS = [
    {
        "type": "opencode",
        "model": "opencode/grok-code",
        "role": "OpenCodeWorker1",
        "mode": "cli",
    },
    {
        "type": "opencode",
        "model": "opencode/glm-4.7-free",
        "role": "OpenCodeWorker2",
        "mode": "cli",
    },
    {
        "type": "opencode",
        "model": "opencode/minimax-m2.1-free",
        "role": "OpenCodeWorker3",
        "mode": "cli",
    },
    {"type": "codex", "model": "gpt-5.2-codex", "role": "CodexWorker4", "mode": "cli"},
    {
        "type": "gemini",
        "model": "gemini-3-flash-preview",
        "role": "GeminiWorker5",
        "mode": "cli",
    },
]


def log_event(message: str, log_file: Path):
    """Log an event to the execution log file."""
    with open(log_file, "a") as f:
        import datetime

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{now}] {message}\n")


def _format_worker_results(worker_results: dict) -> str:
    """Format worker results into a string for the orchestrator to process."""
    formatted = []
    for agent_res in worker_results.get("agent_results", []):
        role = agent_res.get("role", "Unknown")
        response = agent_res.get("response", "No response")
        success = agent_res.get("success", True)

        if success:
            formatted.append(f"### {role}\n\n{response}")
        else:
            error = agent_res.get("error", "Unknown error")
            formatted.append(f"### {role}\n\n[FAILED: {error}]")

    return "\n\n---\n\n".join(formatted)


def print_results(result: dict, log_file: Path, json_file: Path, md_file: Path):
    """Print a summary of the bug finding results."""
    print("\n" + "=" * 60)
    print("BUG FINDER RESULTS SUMMARY")
    print("=" * 60)

    # Note: result keys might distinguish between 'consensus' (final) and 'worker_consensus'
    # 'find_bugs_with_consensus' returns 'worker_consensus' for the worker phase.
    consensus_data = result.get("worker_consensus", result.get("consensus", {}))
    converged = consensus_data.get("converged", False)
    iterations = consensus_data.get("iterations", 0)
    final_decision = result.get("final_decision", "N/A")

    print(f"Consensus Achieved: {converged}")
    print(f"Iterations: {iterations}")
    print(f"Final Decision: {final_decision}")

    agent_results = result.get("agent_results", [])
    print(f"\nAgent Results: {len(agent_results)} agents")

    for agent_result in agent_results:
        role = agent_result.get("role", "Unknown")
        success = agent_result.get("success", False)
        status = "SUCCESS" if success else "FAILED"
        print(f"  - {role}: {status}")

    print("\nOutput Files:")
    print(f"  - Log: {log_file}")
    print(f"  - JSON: {json_file}")
    print(f"  - Markdown: {md_file}")
    print("=" * 60)


def get_git_changed_files(target_path: Path) -> list:
    """Get list of changed files (staged and unstaged) relative to HEAD."""
    try:
        # Check if it's a git repo
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=target_path,
            check=True,
            capture_output=True,
        )

        # Get changed files (staged + unstaged + untracked)
        # Get changed files (staged + unstaged + untracked)
        # 1. Staged and unstaged modifications
        # Handle "unborn HEAD" (new repo with no commits)
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD"], 
                cwd=target_path, 
                check=True, 
                capture_output=True
            )
            base_ref = "HEAD"
        except subprocess.CalledProcessError:
            # No HEAD (new repo), invoke diff against empty tree or just use cached
            # For simplicity, we'll rely on ls-files for everything in this case or just --cached
            base_ref = "--cached"  # This compares index to working tree? No.
            # If no HEAD, everything added is "new". 
            # We will use stricter diff if HEAD exists.
            base_ref = None

        if base_ref:
            cmd_diff = ["git", "diff", base_ref, "--name-only", "--relative"]
        else:
            # No HEAD, just check cached/staged files
            cmd_diff = ["git", "diff", "--cached", "--name-only", "--relative"]

        # 2. Untracked files
        cmd_untracked = ["git", "ls-files", "--others", "--exclude-standard"]

        changed_files = []

        # Run diff
        result_diff = subprocess.run(
            cmd_diff, cwd=target_path, capture_output=True, text=True, check=True
        )
        if result_diff.stdout.strip():
            changed_files.extend(result_diff.stdout.strip().split("\n"))

        # Run untracked
        result_untracked = subprocess.run(
            cmd_untracked, cwd=target_path, capture_output=True, text=True, check=True
        )
        if result_untracked.stdout.strip():
            changed_files.extend(result_untracked.stdout.strip().split("\n"))

        # Dedup and filter
        unique_files = sorted(list(set(changed_files)))

        # Resolve to absolute paths and verify they exist, ensuring they are within target_path
        valid_files = []
        target_path_abs = target_path.resolve()
        
        for f in unique_files:
            try:
                full_path = (target_path / f).resolve()
                # Security check: Ensure file is inside the target directory (prevent path traversal)
                # For Python 3.8 compatibility, use relative_to which raises ValueError
                try:
                    full_path.relative_to(target_path_abs)
                except ValueError:
                    continue
                    
                if full_path.is_file():
                    valid_files.append(str(full_path))
            except Exception:
                pass

        return valid_files

    except subprocess.CalledProcessError:
        print(f"Warning: {target_path} is not a git repository or git error occurred.")
        return []
    except Exception as e:
        print(f"Warning: Could not get git changes: {e}")
        return []


async def find_bugs_with_consensus(
    target_path: str,
    cli_types: list = None,
    verbose: bool = True,
    specific_files: list = None,
    worker_configs: list = None,
) -> dict:
    """
    Find bugs using consensus from multiple AI coding agents.

    Args:
        target_path: Path to file or directory to analyze
        cli_types: List of CLI types to use (auto-detect if None)
        verbose: Enable verbose output
        specific_files: Optional list of specific files to analyze (overrides scanning directory)
        worker_configs: Optional list of worker configurations (overrides default/cli_types)

    Returns:
        Consensus result dictionary
    """
    # Create execution log
    log_file = Path("bug_finder_execution.log")
    if log_file.exists():
        log_file.unlink()  # Start fresh

    log_event(f"STARTING BUG ANALYSIS ON: {target_path}", log_file)

    # Auto-detect available CLIs if not specified
    if cli_types is None and worker_configs is None:
        available = get_available_integrations()
        cli_types = [name for name, status in available.items() if status.get("ready")]

    if worker_configs is None:
        # Filter default configs based on available CLIs if specified
        if cli_types:
            worker_configs = [
                cfg for cfg in DEFAULT_WORKER_CONFIGS if cfg["type"] in cli_types
            ]
        else:
            worker_configs = DEFAULT_WORKER_CONFIGS

    log_event(f"Available CLIs for workers: {', '.join(cli_types) if cli_types else 'Custom Config'}", log_file)
    print(f"Target: {target_path}")
    if specific_files:
        print(f"Analyzing {len(specific_files)} specific files based on criteria (e.g., git diff).")
    print()

    # Create task
    target = Path(target_path)
    if specific_files:
        task = (
            f"Analyze {len(specific_files)} changed files in {target.name} for bugs and regressions"
        )
        files_str = "\n".join([f"- {Path(f).relative_to(target)}" for f in specific_files[:20]])
        if len(specific_files) > 20:
            files_str += f"\n... and {len(specific_files) - 20} more"
        log_event(f"Targeting files:\n{files_str}", log_file)
    elif target.is_file():
        task = f"Analyze {target.name} for bugs, issues, and potential regressions"
    else:
        task = f"Analyze the codebase in {target} for bugs, issues, and potential regressions"

    log_event(f"TASK: {task}", log_file)

    # Worker instructions - find bugs
    worker_instructions = """
    You are a code analysis expert focused on finding bugs and issues.
    
    For each issue found, provide:
    1. File path and line number(s)
    2. Issue type (bug, security, performance, etc.)
    3. Severity (critical, high, medium, low)
    4. Description of the issue
    5. Recommended fix
    
    Be thorough but focus on real issues, not style preferences.
    Format each issue clearly so it can be easily parsed.
    """

    # Orchestrator instructions - synthesize and coordinate
    orchestrator_instructions = """
    You are the lead coordinator for a team of code analysis agents.
    
    You will receive bug reports from multiple worker agents. Your responsibilities:
    1. **Synthesize findings**: Merge overlapping issues reported by multiple agents
    2. **Resolve conflicts**: When agents disagree on severity or classification, use your judgment
    3. **Filter false positives**: If only one agent reports an issue with low confidence, flag it for review
    4. **Prioritize**: Order the final report by severity and confidence (issues found by multiple agents = higher confidence)
    5. **Produce final report**: Create a consolidated bug report in a structured format
    
    Output your final report in this format:
    
    ## High-Confidence Issues (Multiple agents agree)
    [List issues where 2+ agents identified the same problem]
    
    ## Medium-Confidence Issues (Single agent, strong evidence)
    [List issues reported by one agent but with clear evidence]
    
    ## Potential Issues (Needs further review)
    [List issues that may be false positives or need human review]
    
    ## Summary
    [Brief summary of overall code health and top priorities]
    """



    # Orchestrator - runs after workers to synthesize results
    orchestrator_config = {
        "type": "gemini",
        "model": "gemini-3-pro-preview",
        "role": "LeadCoordinator",
        "mode": "api",
    }

    # Create worker agents
    workers = []
    log_event("INITIALIZING WORKER AGENTS:", log_file)
    for i, config in enumerate(worker_configs):
        agent = ExternalCLIConsensusAgent(
            agent_id=f"{config['type']}_cli_agent_{i}",
            role=config["role"],
            instructions=worker_instructions,
            cli_type=config["type"],
            # model=config["model"],  # Remove model here as it is passed via **cli_options if needed
            workspace=str(target.parent if target.is_file() else target),
            initial_value=0.0,
            verbose=verbose,
            model=config["model"] # Pass model as kwarg which goes into cli_options
        )
        workers.append(agent)
        log_event(f"  - {agent.role} (model: {config['model']}, mode: cli)", log_file)
        print(f"Created worker: {agent.role} (model: {config['model']})")

    # Create orchestrator agent
    log_event("INITIALIZING ORCHESTRATOR:", log_file)
    model = orchestrator_config["model"]
    if not model.startswith("gemini/"):
        model = f"gemini/{model}"

    orchestrator = LiteLLMAgent(
        agent_id="orchestrator_api_agent",
        role=orchestrator_config["role"],
        instructions=orchestrator_instructions,
        llm=model,
        initial_value=0.0,
        verbose=verbose,
    )
    log_event(
        f"  - {orchestrator.role} (model: {orchestrator_config['model']}, mode: api)", log_file
    )
    print(f"Created orchestrator: {orchestrator.role} (model: {orchestrator_config['model']})")

    # Prepare context for agents
    context = {"target_path": str(target)}

    if specific_files:
        # Context includes listing of changed files
        context["focus_files"] = specific_files
        context["instruction_override"] = (
            f"Focus your analysis ONLY on these files which have changed: {', '.join([str(Path(p).relative_to(target)) for p in specific_files])}"
        )

        # Read content of small number of files if possible
        if len(specific_files) < 10:
            file_contents = {}
            for p in specific_files:
                try:
                    with open(p, "r") as f:
                        file_contents[str(Path(p).relative_to(target))] = f.read()
                except Exception:
                    pass
            if file_contents:
                context["changed_files_content"] = file_contents

    elif target.is_file():
        try:
            with open(target, "r") as f:
                context["file_content"] = f.read()
        except Exception as e:
            context["error"] = f"Could not read file: {e}"
    else:
        # For directories, provide a file listing
        try:
            files = [
                str(p.relative_to(target))
                for p in target.glob("**/*")
                if p.is_file() and ".git" not in p.parts
            ]
            context["file_listing"] = ", ".join(files[:50])
            if len(files) > 50:
                context["file_listing"] += f" (and {len(files) - 50} more)"
        except Exception as e:
            context["error"] = f"Could not list directory: {e}"

    # ========================================
    # PHASE 1: Workers analyze code in parallel
    # ========================================
    print(f"\n{'=' * 60}")
    print("PHASE 1: Worker agents analyzing code...")
    print(f"{'=' * 60}")
    log_event("PHASE 1: WORKER ANALYSIS", log_file)

    worker_manager = ConsensusManager(
        agents=workers, max_iterations=3, convergence_threshold=0.1, verbose=verbose
    )
    worker_manager.setup_network(topology="fully_connected")

    worker_results = worker_manager.execute_collaborative_task(
        task=task, consensus_strategy="majority", context=context
    )

    log_event("WORKER RESPONSES:", log_file)
    for agent_res in worker_results.get("agent_results", []):
        log_event(f"\n--- {agent_res.get('role')} ---", log_file)
        log_event(f"Response:\n{agent_res.get('response')}", log_file)

    # ========================================
    # PHASE 2: Orchestrator synthesizes results
    # ========================================
    print(f"\n{'=' * 60}")
    print("PHASE 2: Orchestrator synthesizing findings...")
    print(f"{'=' * 60}")
    log_event("PHASE 2: ORCHESTRATOR SYNTHESIS", log_file)

    # Format worker results for the orchestrator
    worker_findings = _format_worker_results(worker_results)

    synthesis_task = f"""
Analyze the following bug reports from {len(worker_results["agent_results"])} code analysis agents.
Synthesize their findings into a final consolidated report.

Target: {target_path}
Focus: {"Git Changed Files" if specific_files else "Full Codebase"}

=== WORKER AGENT FINDINGS ===

{worker_findings}

=== END OF WORKER FINDINGS ===

Please synthesize these findings according to your instructions.
"""

    orchestrator_result = orchestrator.execute(task=synthesis_task, context=context)
    log_event(f"\n--- {orchestrator.role} (Synthesis) ---", log_file)
    log_event(f"Response:\n{orchestrator_result.get('response')}", log_file)

    # Combine results
    result = {
        "task": task,
        "worker_results": worker_results.get("agent_results", []),
        "worker_consensus": worker_results.get("consensus", {}),
        "orchestrator_result": orchestrator_result,
        "final_report": orchestrator_result.get("response", ""),
    }

    print(f"\nAudit log written to: {log_file}")

    return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Consensus-based Bug Finder")
    parser.add_argument(
        "path", nargs="?", default=os.getcwd(), help="Path to file or directory to analyze"
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Analyze only git-changed files (staged+unstaged+untracked)",
    )
    parser.add_argument("--clis", nargs="+", help="Specific CLIs to use (e.g. claude gemini codex)")

    args = parser.parse_args()

    # Handle available CLIs command which doesn't fit argparse well if we want it as a separate mode
    # But simplicity: if no args, we default to cwd.

    target_path = Path(args.path).absolute()

    # Check if we should list available CLIs (maybe if a flag or special command, but let's stick to standard)

    specific_files = None
    if args.diff:
        if not target_path.is_dir():
            print("Error: --diff flag can only be used with a directory/repo path.")
            return 1

        print("Detecting git changes...")
        specific_files = get_git_changed_files(target_path)
        if not specific_files:
            print("No git changes detected to analyze.")
            return 0

        print(f"Found {len(specific_files)} changed files.")

    try:
        result = asyncio.run(
            find_bugs_with_consensus(
                target_path=str(target_path),
                cli_types=args.clis,
                verbose=True,
                specific_files=specific_files,
            )
        )

        # Save structured results for the viewer
        import json

        json_file = Path("bug_report.json")
        try:
            with open(json_file, "w") as f:
                json.dump(result, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not save JSON report: {e}")

        # Save Markdown report
        md_file = Path("bug_report.md")
        try:
            with open(md_file, "w") as f:
                final_report = result.get("final_report", "")
                if not final_report:
                    final_report = "_No final report generated._"
                f.write(final_report)
        except Exception as e:
            print(f"Warning: Could not save Markdown report: {e}")

        # We assume the log file is at the default location since it's hardcoded in find_bugs
        log_file = Path("bug_finder_execution.log")

        print_results(result, log_file, json_file, md_file)
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
