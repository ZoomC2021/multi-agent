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

import asyncio
import os
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
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from consensus_system import (
    ConsensusManager,
    ExternalCLIConsensusAgent,
    LiteLLMAgent,
    get_available_integrations,
)


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


async def find_bugs_with_consensus(
    target_path: str, cli_types: list = None, verbose: bool = True
) -> dict:
    """
    Find bugs using consensus from multiple AI coding agents.

    Args:
        target_path: Path to file or directory to analyze
        cli_types: List of CLI types to use (auto-detect if None)
        verbose: Enable verbose output

    Returns:
        Consensus result dictionary
    """
    # Create execution log
    log_file = Path("bug_finder_execution.log")
    if log_file.exists():
        log_file.unlink()  # Start fresh

    log_event(f"STARTING BUG ANALYSIS ON: {target_path}", log_file)

    # Auto-detect available CLIs if not specified
    if cli_types is None:
        available = get_available_integrations()
        cli_types = [name for name, status in available.items() if status.get("ready")]

    log_event(f"Available CLIs for workers: {', '.join(cli_types)}", log_file)
    print(f"Target: {target_path}")
    print()

    # Create task
    target = Path(target_path)
    if target.is_file():
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

    # Worker agents - execute in parallel to find bugs
    worker_configs = [
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
            model=config["model"],
            workspace=str(target.parent if target.is_file() else target),
            initial_value=0.0,
            verbose=verbose,
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
    if target.is_file():
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


def print_results(result: dict, log_path: Path, json_path: Path, md_path: Path):
    """Print formatted concise bug finding results."""
    print("\n" + "=" * 60)
    print("BUG FINDING RESULTS")
    print("=" * 60)

    workers = result.get("worker_results", [])
    total_workers = len(workers)
    successful_workers = sum(1 for w in workers if w.get("success", True))

    consensus = result.get("worker_consensus", {})
    converged = "Converged" if consensus.get("converged", False) else "Not Converged"
    iterations = consensus.get("iterations", 0)

    print(f"Worker Agents: {successful_workers}/{total_workers} executed successfully")
    print(f"Consensus: {converged} (Iterations: {iterations})")
    print()
    print(f"[SUCCESS] Full report saved to: {md_path.absolute()}")
    print(f"[DATA] Structured data saved to: {json_path.absolute()}")
    print(f"[LOG] Execution log: {log_path.absolute()}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python bug_finder_example.py <path-to-analyze>")
        print()
        print("Example:")
        print("  python bug_finder_example.py ../my_project/main.py")
        print("  python bug_finder_example.py ../my_project/")
        print()
        print("Available CLIs:")
        available = get_available_integrations()
        for name, status in available.items():
            ready = status.get("ready", False)
            print(f"  {'✓' if ready else '✗'} {name}")
        return 1

    target_path = sys.argv[1]

    # Optional: specify CLIs via additional args
    cli_types = sys.argv[2:] if len(sys.argv) > 2 else None

    try:
        result = asyncio.run(
            find_bugs_with_consensus(target_path=target_path, cli_types=cli_types, verbose=True)
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
