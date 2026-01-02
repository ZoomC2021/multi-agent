# Usage Guide

Practical examples and use cases for the PraisonAI Multi-Agent Iterative Consensus System.

## Table of Contents

- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Python API Usage](#python-api-usage)
- [Use Cases](#use-cases)
- [Configuration Examples](#configuration-examples)

## Quick Start

### Install

```bash
# Clone the repository
git clone https://github.com/ZoomC2021/multi-agent.git
cd multi-agent

# Install
pip install -e .
```

### Run Your First Consensus

```bash
# Initialize a configuration file
consensus-cli init --output my_agents.yaml

# Run with default agents
consensus-cli run

# Run a collaborative task
consensus-cli run --task "Analyze code quality of authentication module"
```

## CLI Usage

### Basic Commands

#### 1. Get Help

```bash
consensus-cli --help
consensus-cli run --help
consensus-cli init --help
```

#### 2. Initialize Configuration

Create a default configuration file:

```bash
consensus-cli init --output agents.yaml
```

Edit `agents.yaml` to customize agents, consensus parameters, and workflow settings.

#### 3. Run Basic Consensus

Run consensus with default configuration:

```bash
consensus-cli run
```

This will:
- Create 3 default coding agents
- Set up a fully-connected network
- Run consensus algorithm
- Display convergence results

#### 4. Run with Custom Configuration

```bash
consensus-cli run --config examples/coding_agents.yaml
```

#### 5. Execute Collaborative Task

```bash
consensus-cli run \
  --config examples/coding_agents.yaml \
  --task "Review this authentication function for security issues" \
  --output results.json
```

The results will be saved to `results.json` with:
- Individual agent responses
- Consensus details
- Final decision
- Convergence history

### CLI Examples

#### Example 1: Code Quality Assessment

```bash
consensus-cli run \
  --task "Assess the code quality of the payment processing module" \
  --output quality_report.json
```

#### Example 2: Security Review

```bash
consensus-cli run \
  --config examples/security_review.yaml \
  --task "Security audit of user authentication system" \
  --output security_audit.json
```

#### Example 3: Performance Analysis

```bash
consensus-cli run \
  --task "Analyze performance bottlenecks in database query layer" \
  --output performance_analysis.json
```

## Python API Usage

### Example 1: Basic Consensus

```python
from consensus_system import ConsensusAgent, ConsensusManager

# Create agents with initial quality scores
agents = [
    ConsensusAgent("analyzer", "CodeAnalyzer", "Analyze code", 7.5),
    ConsensusAgent("reviewer", "CodeReviewer", "Review code", 8.0),
    ConsensusAgent("optimizer", "CodeOptimizer", "Optimize code", 6.5),
]

# Create consensus manager
manager = ConsensusManager(
    agents=agents,
    max_iterations=10,
    convergence_threshold=0.01,
    verbose=True
)

# Setup network (fully connected)
manager.setup_network("fully_connected")

# Run consensus
result = manager.run_consensus(strategy="average")

print(f"Converged: {result['converged']}")
print(f"Consensus value: {result['consensus_value']:.2f}")
```

### Example 2: Collaborative Task

```python
from consensus_system import ConsensusManager
from consensus_system.config import load_config
from consensus_system.praison_integration import create_praison_agents_from_config

# Load configuration
config = load_config("examples/coding_agents.yaml")

# Create PraisonAI-backed agents
agents = create_praison_agents_from_config(config)

# Create manager
manager = ConsensusManager(agents, verbose=True)
manager.setup_network("fully_connected")

# Execute collaborative task
result = manager.execute_collaborative_task(
    task="Review this code:\n\ndef process_payment(card_number, amount):\n    # Process payment logic",
    consensus_strategy="average"
)

# Access results
for agent_result in result['agent_results']:
    print(f"{agent_result['role']}: {agent_result['response']}")

print(f"Final decision: {result['final_decision']}")
```

### Example 3: Custom Network Topology

```python
from consensus_system import ConsensusAgent, ConsensusManager

# Create 5 agents
agents = [
    ConsensusAgent(f"agent_{i}", f"Expert{i}", f"Instructions {i}", float(i))
    for i in range(5)
]

# Create manager
manager = ConsensusManager(agents, verbose=True)

# Try different topologies
topologies = ["fully_connected", "ring", "chain"]

for topology in topologies:
    print(f"\nTopology: {topology}")
    manager.setup_network(topology)
    result = manager.run_consensus()
    print(f"Converged in {result['iterations']} iterations")
```

### Example 4: Monitoring Convergence

```python
from consensus_system import ConsensusManager
from consensus_system.agent import ConsensusAgent

agents = [
    ConsensusAgent("a1", "Agent1", "Test", 10.0),
    ConsensusAgent("a2", "Agent2", "Test", 5.0),
    ConsensusAgent("a3", "Agent3", "Test", 7.0),
]

manager = ConsensusManager(agents, max_iterations=20, verbose=True)
manager.setup_network("fully_connected")

# Define callback to monitor each iteration
def iteration_callback(state):
    iteration = state['iteration']
    values = state['values']
    print(f"Iteration {iteration}: {[f'{v:.2f}' for v in values.values()]}")

# Run with callback
result = manager.run_consensus(callback=iteration_callback)

# Analyze convergence
print("\nConvergence Analysis:")
for i, iteration in enumerate(result['history']):
    values = list(iteration['values'].values())
    variance = sum((v - sum(values)/len(values))**2 for v in values) / len(values)
    print(f"Iteration {i}: variance = {variance:.4f}")
```

## Use Cases

### 1. Code Review Automation

Automate code reviews with multiple specialized agents:

```yaml
# code_review.yaml
agents:
  - name: style_checker
    role: StyleChecker
    instructions: "Check code style and formatting"
    
  - name: security_auditor
    role: SecurityAuditor
    instructions: "Audit for security vulnerabilities"
    
  - name: performance_analyst
    role: PerformanceAnalyst
    instructions: "Analyze performance implications"
```

Run:
```bash
consensus-cli run \
  --config code_review.yaml \
  --task "Review pull request #123" \
  --output pr_review.json
```

### 2. Architecture Decision Making

Use consensus for architectural decisions:

```python
from consensus_system import ConsensusAgent, ConsensusManager

# Create architecture experts
architects = [
    ConsensusAgent("backend", "BackendArchitect", "Backend expert", 0.0),
    ConsensusAgent("frontend", "FrontendArchitect", "Frontend expert", 0.0),
    ConsensusAgent("devops", "DevOpsArchitect", "DevOps expert", 0.0),
    ConsensusAgent("security", "SecurityArchitect", "Security expert", 0.0),
]

manager = ConsensusManager(architects, verbose=True)
manager.setup_network("fully_connected")

# Make decision
result = manager.execute_collaborative_task(
    task="Should we migrate from REST to GraphQL?",
    consensus_strategy="majority"
)
```

### 3. Quality Scoring

Score code quality with multiple criteria:

```python
from consensus_system import ConsensusAgent, ConsensusManager

# Each agent scores a different aspect (1-10)
agents = [
    ConsensusAgent("readability", "ReadabilityExpert", "Score readability", 8.0),
    ConsensusAgent("maintainability", "MaintainabilityExpert", "Score maintainability", 7.0),
    ConsensusAgent("testability", "TestabilityExpert", "Score testability", 6.0),
    ConsensusAgent("performance", "PerformanceExpert", "Score performance", 9.0),
]

manager = ConsensusManager(agents, verbose=True)
manager.setup_network("fully_connected")

# Get overall quality score
result = manager.run_consensus(strategy="average")

overall_score = result['consensus_value']
print(f"Overall Code Quality: {overall_score:.1f}/10")

if overall_score >= 8.0:
    print("Status: EXCELLENT")
elif overall_score >= 6.0:
    print("Status: GOOD")
else:
    print("Status: NEEDS IMPROVEMENT")
```

### 4. Continuous Integration

Integrate with CI/CD pipeline:

```bash
#!/bin/bash
# ci_consensus_check.sh

# Run consensus code review
consensus-cli run \
  --config .github/consensus_config.yaml \
  --task "Review changes in this pull request" \
  --output consensus_results.json

# Parse results
SCORE=$(python3 -c "import json; print(json.load(open('consensus_results.json'))['consensus']['consensus_value'])")

# Gate based on consensus score
if (( $(echo "$SCORE < 5.0" | bc -l) )); then
    echo "Consensus score too low: $SCORE"
    exit 1
else
    echo "Consensus score acceptable: $SCORE"
    exit 0
fi
```

## Configuration Examples

### Minimal Configuration

```yaml
agents:
  - name: agent1
    role: Analyst
    instructions: "Analyze code"

consensus:
  max_iterations: 5
  strategy: average
```

### Full Configuration

```yaml
agents:
  - name: code_analyzer
    role: CodeAnalyzer
    instructions: |
      Comprehensive code analysis instructions...
    llm: gpt-4
    initial_value: 0.0
    
  - name: security_expert
    role: SecurityExpert
    instructions: |
      Security review instructions...
    llm: gpt-4
    initial_value: 0.0

consensus:
  max_iterations: 20
  convergence_threshold: 0.005
  strategy: average
  topology: fully_connected

workflow:
  mode: collaborative
  headless: true
  enable_logging: true
  output_format: json
```

### Specialized Configurations

#### Security-Focused

```yaml
agents:
  - name: owasp_checker
    role: OWASPChecker
    instructions: "Check for OWASP Top 10 vulnerabilities"
    
  - name: auth_expert
    role: AuthExpert
    instructions: "Review authentication and authorization"
    
  - name: data_privacy_expert
    role: DataPrivacyExpert
    instructions: "Ensure data privacy compliance"

consensus:
  max_iterations: 15
  strategy: majority  # Majority vote for critical security decisions
  topology: fully_connected
```

#### Performance-Focused

```yaml
agents:
  - name: cpu_analyzer
    role: CPUAnalyzer
    instructions: "Analyze CPU usage and efficiency"
    
  - name: memory_analyzer
    role: MemoryAnalyzer
    instructions: "Analyze memory usage and leaks"
    
  - name: io_analyzer
    role: IOAnalyzer
    instructions: "Analyze I/O operations and bottlenecks"

consensus:
  max_iterations: 10
  strategy: average  # Average performance scores
  topology: ring  # Ring topology for sequential analysis
```

## Tips and Best Practices

1. **Start Simple**: Begin with 3-4 agents and fully_connected topology
2. **Clear Instructions**: Write specific, actionable instructions for each agent
3. **Appropriate Iterations**: 10-15 iterations is usually sufficient
4. **Monitor Convergence**: Use verbose mode to understand convergence patterns
5. **Save Results**: Always use `--output` to save results for analysis
6. **Test Configurations**: Test with small tasks before deploying to production

## Next Steps

- Check [INTEGRATION.md](INTEGRATION.md) for PraisonAI setup
- See [README.md](README.md) for architecture details
- Explore [examples/](examples/) directory for more examples
- Read [PraisonAI documentation](https://docs.praison.ai/) for advanced features
