# Multi-Agent Iterative Consensus System

A production-ready PraisonAI-based multi-agent iterative consensus system that leverages multiple coding CLIs in headless mode for collaborative decision-making and code analysis.

## Overview

This system implements an iterative consensus mechanism where multiple AI agents collaborate to reach agreement on coding tasks, code quality assessments, and technical decisions. The agents communicate through a configurable network topology and iteratively update their assessments until reaching consensus.

## Features

- **Multi-Agent Collaboration**: Multiple AI agents with specialized roles (analyzer, reviewer, optimizer, security)
- **Iterative Consensus**: Agents reach agreement through iterative value updates and communication
- **PraisonAI Integration**: Leverages PraisonAI framework for LLM-based agent execution
- **Headless Mode**: Fully supports CLI-based execution without UI dependencies
- **Configurable Topology**: Support for fully-connected, ring, and chain network topologies
- **YAML Configuration**: Easy agent and workflow configuration through YAML files
- **Flexible Consensus Strategies**: Average, majority voting, and weighted consensus

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install from source

```bash
# Clone the repository
git clone https://github.com/ZoomC2021/multi-agent.git
cd multi-agent

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Install PraisonAI (optional, for full functionality)

```bash
pip install praisonaiagents
```

**Note**: The system works in simulation mode without PraisonAI installed, but for actual LLM-based execution, PraisonAI is required.

## Quick Start

### 1. Initialize Configuration

Generate a default configuration file:

```bash
consensus-cli init --output agents.yaml
```

### 2. Run Basic Consensus

Run a basic consensus demonstration:

```bash
consensus-cli run
```

### 3. Run with Custom Configuration

```bash
consensus-cli run --config examples/coding_agents.yaml
```

### 4. Execute Collaborative Task

```bash
consensus-cli run --task "Analyze the code quality and security of the authentication module"
```

### 5. Save Results

```bash
consensus-cli run --task "Review the performance of the database queries" --output results.json
```

## Configuration

### Agent Configuration

Define agents in a YAML file (`agents.yaml`):

```yaml
agents:
  - name: code_analyzer
    role: CodeAnalyzer
    instructions: "Analyze code for quality, patterns, and potential issues."
    llm: gpt-4
    initial_value: 0.0

  - name: code_reviewer
    role: CodeReviewer
    instructions: "Review code for best practices and maintainability."
    llm: gpt-4
    initial_value: 0.0

consensus:
  max_iterations: 10
  convergence_threshold: 0.01
  strategy: average  # or 'majority', 'weighted'
  topology: fully_connected  # or 'ring', 'chain'

workflow:
  mode: collaborative
  headless: true
```

### Consensus Strategies

- **average**: Agents converge by averaging their values (best for numeric assessments)
- **majority**: Agents vote and the majority value wins (best for categorical decisions)
- **weighted**: Advanced weighted consensus based on agent confidence

### Network Topologies

- **fully_connected**: Each agent communicates with all other agents (fastest convergence)
- **ring**: Agents form a ring, each communicating with two neighbors
- **chain**: Agents form a chain, communicating with immediate neighbors only

## Architecture

### Core Components

1. **ConsensusAgent**: Individual agent with consensus capabilities
   - Maintains state/value
   - Communicates with neighbors
   - Executes tasks
   - Updates value based on consensus strategy

2. **ConsensusManager**: Orchestrates the multi-agent system
   - Manages agent network topology
   - Runs iterative consensus algorithm
   - Coordinates collaborative tasks
   - Tracks convergence and history

3. **PraisonConsensusAgent**: PraisonAI-backed agent
   - Wraps PraisonAI agents for LLM execution
   - Integrates with consensus system
   - Falls back to simulation if PraisonAI unavailable

4. **Configuration Module**: YAML-based configuration
   - Loads and validates configurations
   - Provides default configurations
   - Supports multiple configuration profiles

5. **CLI Interface**: Command-line interface
   - Headless mode execution
   - Task execution
   - Results export

### Consensus Algorithm

The system implements a distributed consensus algorithm:

1. **Initialization**: Agents start with initial values
2. **Iteration**: Each agent updates its value based on neighbors' values
3. **Communication**: Agents exchange values according to network topology
4. **Convergence Check**: System checks if values have converged
5. **Termination**: Process stops when converged or max iterations reached

## Usage Examples

### Example 1: Code Quality Assessment

```python
from consensus_system import ConsensusAgent, ConsensusManager

# Create agents
analyzer = ConsensusAgent("analyzer", "CodeAnalyzer", "Analyze code quality", 5.0)
reviewer = ConsensusAgent("reviewer", "CodeReviewer", "Review code", 7.0)
optimizer = ConsensusAgent("optimizer", "CodeOptimizer", "Optimize code", 6.0)

# Create manager
manager = ConsensusManager([analyzer, reviewer, optimizer], verbose=True)
manager.setup_network("fully_connected")

# Run consensus
result = manager.run_consensus(strategy="average")
print(f"Consensus value: {result['consensus_value']}")
```

### Example 2: Collaborative Task Execution

```bash
# Execute a collaborative code review task
consensus-cli run \
  --config examples/coding_agents.yaml \
  --task "Review the authentication module for security vulnerabilities" \
  --output security_review.json
```

### Example 3: Custom Configuration

Create a custom `my_agents.yaml`:

```yaml
agents:
  - name: frontend_expert
    role: FrontendExpert
    instructions: "Expert in frontend code, React, and UI/UX"
    llm: gpt-4

  - name: backend_expert
    role: BackendExpert
    instructions: "Expert in backend code, APIs, and databases"
    llm: gpt-4

  - name: devops_expert
    role: DevOpsExpert
    instructions: "Expert in deployment, CI/CD, and infrastructure"
    llm: gpt-4

consensus:
  max_iterations: 20
  strategy: majority
  topology: ring
```

Run with:

```bash
consensus-cli run --config my_agents.yaml --task "Evaluate the entire application architecture"
```

## CLI Reference

### Commands

#### `consensus-cli run`

Run the consensus system.

**Options**:
- `--config, -c PATH`: Path to configuration YAML file
- `--task, -t TEXT`: Task to execute collaboratively
- `--output, -o PATH`: Output file for results (JSON)
- `--interactive, -i`: Run in interactive mode (not headless)

**Examples**:
```bash
# Basic run
consensus-cli run

# With configuration
consensus-cli run --config agents.yaml

# With task
consensus-cli run --task "Analyze code" --output results.json
```

#### `consensus-cli init`

Initialize a default configuration file.

**Options**:
- `--output, -o PATH`: Output path for configuration file (default: agents.yaml)

**Example**:
```bash
consensus-cli init --output my_config.yaml
```

## Advanced Usage

### Programmatic API

```python
from consensus_system import load_config, ConsensusManager
from consensus_system.praison_integration import create_praison_agents_from_config

# Load configuration
config = load_config("agents.yaml")

# Create PraisonAI-backed agents
agents = create_praison_agents_from_config(config)

# Create and configure manager
manager = ConsensusManager(agents, max_iterations=15, verbose=True)
manager.setup_network(topology="fully_connected")

# Execute collaborative task
result = manager.execute_collaborative_task(
    task="Analyze this Python module for best practices",
    consensus_strategy="average"
)

print(f"Consensus achieved: {result['consensus']['converged']}")
print(f"Final decision: {result['final_decision']}")
```

### Custom Agent Roles

Extend the system with custom agent roles:

```python
from consensus_system.praison_integration import PraisonConsensusAgent

# Create custom agent
custom_agent = PraisonConsensusAgent(
    agent_id="custom_analyzer",
    role="CustomAnalyzer",
    instructions="Custom analysis instructions...",
    llm="gpt-4",
    verbose=True
)

# Add to agent list and use in manager
agents.append(custom_agent)
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e .[dev]

# Run tests
pytest
```

### Code Style

The project uses Black for formatting and Ruff for linting:

```bash
# Format code
black consensus_system/

# Lint code
ruff check consensus_system/
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [PraisonAI](https://github.com/MervinPraison/PraisonAI) framework
- Inspired by distributed consensus algorithms and multi-agent systems research

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/ZoomC2021/multi-agent).