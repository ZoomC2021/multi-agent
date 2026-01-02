# Agent Guidelines for Multi-Agent Consensus System

This document provides essential information for agentic coding agents operating within this repository. Adhere to these guidelines to ensure consistency, quality, and compatibility.

## 🛠 Build and Development

### Installation
The project uses `setuptools` and `pyproject.toml`.
- **Install for development:** `pip install -e .[dev]`
- **Basic installation:** `pip install -r requirements.txt && pip install -e .`

### Build System
- Backend: `setuptools.build_meta`
- Python requirement: `>=3.8`

### Useful Commands
- **Initialize config:** `consensus-cli init --output agents.yaml`
- **Run consensus:** `consensus-cli run`
- **Run with task:** `consensus-cli run --task "Your task description"`
- **Linting:** `ruff check .`
- **Formatting:** `black .`

## 🧪 Testing

Currently, there are no test files in the repository. However, the project is configured for `pytest`.
- **Run all tests:** `pytest` (when tests are added)
- **Run a single test file:** `pytest path/to/test_file.py`
- **Run a specific test case:** `pytest path/to/test_file.py::test_function_name`
- **Coverage:** `pytest --cov=consensus_system`

## 🎨 Code Style and Conventions

The project uses `black` for formatting and `ruff` for linting.

### Formatting
- **Line Length:** 100 characters (configured in `pyproject.toml`).
- **Tool:** Use `black .` to format the codebase.
- **Quotes:** Prefer double quotes for strings and docstrings.

### Imports
- **Ordering:** Group imports into standard library, third-party, and local modules.
- **Style:** Use absolute imports for local modules (e.g., `from consensus_system.agent import ConsensusAgent`).
- **Typing:** Use the `typing` module for all type hints. Avoid `from typing import *`.

### Typing
Extensive type hinting is required for all function signatures and class members.
- **Preferred types:** `List`, `Dict`, `Any`, `Optional`, `Callable` from `typing`.
- **Forward references:** Use string literals for forward references in type hints (e.g., `neighbors: List['ConsensusAgent']`).
- **New Types:** For complex structures, consider using `TypedDict` or `NamedTuple`.

### Naming Conventions
- **Classes:** `PascalCase` (e.g., `ConsensusManager`).
- **Functions/Methods:** `snake_case` (e.g., `setup_network`).
- **Variables:** `snake_case` (e.g., `max_iterations`).
- **Constants:** `UPPER_SNAKE_CASE`.
- **Agent IDs:** Usually descriptive `snake_case` strings.

### Error Handling
- Use specific exceptions where possible (e.g., `ValueError`, `TypeError`).
- Provide descriptive error messages.
- Use `try...except` blocks around operations that might fail due to type mismatches (especially in consensus calculations).
- Log errors using `logging` module rather than `print` (though current implementation uses some prints for CLI visibility).

### Documentation
- **Style:** Google-style docstrings are preferred.
- **Classes:** Include a summary of the class and descriptions for `__init__` arguments.
- **Methods:** Include `Args`, `Returns`, and `Raises` sections.
- **Module-level:** Each file should start with a docstring describing its purpose.

## 🏗 Architecture Overview

### Core Components
- `ConsensusAgent`: Base class for agents. Maintains state (`value`), `neighbors`, and `history`.
- `ConsensusManager`: Orchestrates the network. Handles `topology` setup and `iterate_consensus` loops.
- `PraisonConsensusAgent`: Specialized agent that integrates with the PraisonAI framework for LLM-based execution.

### Consensus Logic
- **Strategies:** `average` (numeric), `majority` (categorical), `weighted`.
- **Topologies:** `fully_connected`, `ring`, `chain`.
- **Convergence:** Determined by `convergence_threshold` comparing current and previous numeric values.
- **State management:** Values are stored in `self.value`, and the history of values is kept in `self.history`.

## 📂 Project Structure

```text
consensus_system/
├── __init__.py           # Package initialization and exports
├── agent.py              # Base ConsensusAgent class
├── cli.py                # Command-line interface implementation
├── config.py             # Configuration loading and validation
├── manager.py            # ConsensusManager for orchestration
└── praison_integration.py # PraisonAI agent integration
examples/                 # Usage examples and sample configurations
  ├── simple_example.py   # Basic numeric consensus
  ├── advanced_example.py # Collaborative task consensus
  └── *.yaml              # Configuration examples
```

## 🤖 Agent-Specific Instructions

When adding new features or modifying agents:
1. **Maintain Interface:** Do not break the `ConsensusAgent` or `ConsensusManager` public APIs.
2. **Simulation Fallback:** Ensure LLM-based agents can fall back to simulation mode if PraisonAI or API keys are unavailable.
3. **Verbose Logging:** Implement `verbose` flags to provide visibility into agent decision-making.
4. **State Management:** Always update `self.history` when changing `self.value`.
5. **Configurability:** New parameters should be added to the YAML configuration schema in `config.py`.

## 🔄 Workflow for Agents (Task Execution)

1. **Understand:** Read the task and check existing configurations in `examples/`.
2. **Plan:** If modifying core logic, ensure `ConsensusManager` handles the changes across different topologies.
3. **Implement:** Write idiomatic Python code following the style guide.
4. **Verify:** Since there are no formal tests, run the examples (e.g., `python examples/simple_example.py`) to verify behavior.
5. **Document:** Update docstrings if interfaces change.

## 📝 Common Task Examples

### Adding a New Consensus Strategy
1. Modify `ConsensusAgent.consensus_update` to implement the new logic.
2. Update `ConsensusManager.run_consensus` if any aggregation logic needs to change.
3. Update `config.py` to include the new strategy in validation.
4. Add an example in `examples/` demonstrating the new strategy.

### Extending Agent Capabilities
1. If adding a new base behavior, modify `ConsensusAgent.execute`.
2. For LLM-specific features, update `PraisonConsensusAgent` in `praison_integration.py`.
3. Ensure the `verbose` flag provides meaningful output for the new capability.

### Modifying Network Topology
1. Update `ConsensusManager.setup_network` with the new topology logic.
2. Ensure it handles edge cases like 0 or 1 agents.
3. Update `SUMMARY.md` or `USAGE.md` if the new topology is a major feature.

## 📜 Project Rules (Inherited)

- **No Secrets:** Never commit API keys or sensitive configurations. Use environment variables for `OPENAI_API_KEY`.
- **Minimal Dependencies:** Stick to the dependencies listed in `pyproject.toml`. Propose changes before adding new ones.
- **Clean CLI:** Ensure CLI output remains readable and supports headless mode. Avoid excessive printing unless `verbose` is True.
- **Git Hygiene:** Use descriptive commit messages. Work in feature branches when possible.

---
*This file is intended for AI agents. When performing tasks, refer to these rules to maintain project integrity.*
