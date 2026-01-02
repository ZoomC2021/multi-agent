# PraisonAI Integration Guide

This guide explains how to integrate the consensus system with actual PraisonAI agents for LLM-based execution.

## Overview

The multi-agent consensus system supports two modes:

1. **Simulation Mode**: Agents provide pre-defined responses (no API key required)
2. **PraisonAI Mode**: Agents use actual LLMs via PraisonAI (API key required)

## Setting Up PraisonAI Integration

### 1. Install PraisonAI

The system will automatically detect if PraisonAI is installed:

```bash
pip install praisonaiagents
```

### 2. Configure API Keys

Set up your LLM provider API key:

#### For OpenAI (GPT-4, GPT-3.5)

```bash
export OPENAI_API_KEY="your-api-key-here"
```

#### For Local LLM (LM Studio, Ollama)

```bash
export OPENAI_API_BASE="http://localhost:1234/v1"
export OPENAI_API_KEY="not-needed"  # Placeholder for local servers
```

#### For Other Providers

PraisonAI supports 100+ LLM providers. See [PraisonAI documentation](https://docs.praison.ai/) for details.

### 3. Using PraisonAI-Backed Agents

The system automatically uses PraisonAI when available:

```python
from consensus_system.config import load_config
from consensus_system.praison_integration import create_praison_agents_from_config
from consensus_system.manager import ConsensusManager

# Load configuration
config = load_config("examples/coding_agents.yaml")

# Create PraisonAI-backed agents (will use real LLM if API key is set)
agents = create_praison_agents_from_config(config)

# Create manager and run
manager = ConsensusManager(agents, verbose=True)
manager.setup_network("fully_connected")

# Execute collaborative task with real LLM responses
result = manager.execute_collaborative_task(
    task="Review this code for security issues: [your code here]",
    consensus_strategy="average"
)
```

### 4. CLI with PraisonAI

The CLI automatically uses PraisonAI when API keys are configured:

```bash
# Set API key
export OPENAI_API_KEY="your-key"

# Run with PraisonAI-backed agents
consensus-cli run \
  --config examples/coding_agents.yaml \
  --task "Analyze authentication module" \
  --output results.json
```

## Configuration for Different LLMs

### Using GPT-4

```yaml
agents:
  - name: code_analyzer
    role: CodeAnalyzer
    instructions: "Analyze code quality..."
    llm: gpt-4  # or gpt-4-turbo, gpt-4o
```

### Using GPT-3.5 (Faster/Cheaper)

```yaml
agents:
  - name: code_analyzer
    role: CodeAnalyzer
    instructions: "Analyze code quality..."
    llm: gpt-3.5-turbo
```

### Using Local LLM

```yaml
agents:
  - name: code_analyzer
    role: CodeAnalyzer
    instructions: "Analyze code quality..."
    llm: local-model  # Model name from your local server
```

Then set:
```bash
export OPENAI_API_BASE="http://localhost:1234/v1"
export OPENAI_API_KEY="not-needed"
```

### Using Claude (Anthropic)

```yaml
agents:
  - name: code_analyzer
    role: CodeAnalyzer
    instructions: "Analyze code quality..."
    llm: claude-3-opus  # or claude-3-sonnet, claude-3-haiku
```

Set API key:
```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
```

## Fallback Behavior

The system gracefully handles missing API keys:

1. **PraisonAI installed + API key set**: Uses actual LLM
2. **PraisonAI installed + No API key**: Falls back to simulation mode
3. **PraisonAI not installed**: Uses simulation mode

This allows testing without API keys and ensures the system always works.

## Best Practices

### 1. Agent Instructions

Write clear, specific instructions for each agent:

```yaml
agents:
  - name: security_expert
    role: SecurityExpert
    instructions: |
      You are a security expert. For each code review:
      1. Identify security vulnerabilities (SQL injection, XSS, etc.)
      2. Check for authentication/authorization issues
      3. Review data validation and sanitization
      4. Rate security on a scale of 1-10
      5. Provide specific, actionable recommendations
```

### 2. Consensus Strategy

Choose the right consensus strategy:

- **average**: Best for numeric scores (e.g., code quality ratings)
- **majority**: Best for categorical decisions (e.g., approve/reject)
- **weighted**: Advanced - weight agents by expertise

### 3. Iteration Settings

Adjust based on your needs:

```yaml
consensus:
  max_iterations: 15  # More iterations = better convergence
  convergence_threshold: 0.01  # Lower = stricter convergence
```

### 4. Network Topology

- **fully_connected**: Fastest convergence, best for critical decisions
- **ring**: Slower but more diverse perspectives
- **chain**: Sequential review, good for pipeline workflows

## Example: Production Setup

```bash
# production_setup.sh

# Install dependencies
pip install praisonaiagents pyyaml

# Install consensus system
pip install -e .

# Set API keys (use secrets management in production)
export OPENAI_API_KEY="${OPENAI_SECRET}"

# Run consensus review
consensus-cli run \
  --config production_agents.yaml \
  --task "Security audit of payment processing module" \
  --output audit_results.json

# Check exit code
if [ $? -eq 0 ]; then
    echo "Consensus review completed successfully"
    # Process results...
else
    echo "Consensus review failed"
    exit 1
fi
```

## Monitoring and Debugging

### Enable Verbose Mode

```python
manager = ConsensusManager(agents, verbose=True)
```

Or with CLI:
```bash
consensus-cli run --config agents.yaml --verbose
```

### Check Agent Responses

```python
result = manager.execute_collaborative_task(task="...")

for agent_result in result['agent_results']:
    print(f"{agent_result['role']}: {agent_result['response']}")
    print(f"Mode: {agent_result.get('mode')}")  # 'praison' or 'simulation'
```

### Consensus History

```python
consensus = result['consensus']

for iteration in consensus['history']:
    print(f"Iteration {iteration['iteration']}: {iteration['values']}")
```

## Troubleshooting

### "OPENAI_API_KEY environment variable is required"

- Set the API key: `export OPENAI_API_KEY="your-key"`
- Or use local LLM: `export OPENAI_API_BASE="http://localhost:1234/v1"`

### Agents running in simulation mode

- Check if API key is set: `echo $OPENAI_API_KEY`
- Verify PraisonAI is installed: `pip show praisonaiagents`
- Look for error messages in verbose output

### Slow convergence

- Increase `max_iterations` in config
- Relax `convergence_threshold`
- Try different network topology

## Advanced Features

### Custom Tools

Add tools to agents:

```python
from praisonaiagents import Agent

agent = PraisonConsensusAgent(
    agent_id="analyzer",
    role="CodeAnalyzer",
    instructions="...",
    tools=[custom_tool_1, custom_tool_2]
)
```

### Workflow Customization

Implement custom consensus strategies:

```python
class CustomConsensusManager(ConsensusManager):
    def custom_consensus_update(self, agents):
        # Your custom logic here
        pass
```

## Resources

- [PraisonAI Documentation](https://docs.praison.ai/)
- [PraisonAI GitHub](https://github.com/MervinPraison/PraisonAI)
- [Multi-Agent Consensus System Repository](https://github.com/ZoomC2021/multi-agent)

## Support

For issues with:
- **Consensus System**: Open an issue on the GitHub repository
- **PraisonAI Integration**: Check PraisonAI documentation or GitHub issues
- **LLM API Keys**: Contact your LLM provider
