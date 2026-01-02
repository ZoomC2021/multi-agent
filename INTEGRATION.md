# LiteLLM Integration Guide

This guide explains how to use the consensus system with LiteLLM for multi-provider LLM support.

## Overview

The consensus system uses **LiteLLM** to support 100+ LLM providers through a unified interface, including:
- OpenAI (GPT-4, GPT-3.5-Turbo, etc.)
- Google Gemini (via Google Cloud API)
- Anthropic Claude
- Azure OpenAI
- And many more

## Setting Up LiteLLM Integration

### 1. Install LiteLLM

The system automatically requires LiteLLM. If you used `pip install -e .` or `pip install -r requirements.txt`, LiteLLM is already installed.

To explicitly ensure LiteLLM is installed:

```bash
pip install litellm>=1.0.0
```

### 2. Configure API Keys

Set the appropriate environment variable for your LLM provider:

**For Google Gemini:**
```bash
export GEMINI_API_KEY="your-api-key"
# or
export GOOGLE_API_KEY="your-api-key"
```

**For OpenAI:**
```bash
export OPENAI_API_KEY="your-api-key"
```

**For Anthropic Claude:**
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

For other providers, see [LiteLLM documentation](https://docs.litellm.ai/docs/providers).

### 3. Using LiteLLM-Backed Agents

The system automatically uses LiteLLM when agents are created with a model string:

```python
from consensus_system import LiteLLMAgent, ConsensusManager

# Create agents with different models
agent1 = LiteLLMAgent(
    agent_id="agent1",
    role="Code Reviewer",
    instructions="You are a Python expert...",
    llm="gemini/gemini-1.5-pro"
)

agent2 = LiteLLMAgent(
    agent_id="agent2",
    role="Security Analyst",
    instructions="You are a security expert...",
    llm="gpt-4"
)

# Use with consensus manager
manager = ConsensusManager(
    agents=[agent1, agent2],
    max_iterations=10
)

result = manager.execute_collaborative_task(
    task="Review this code for bugs and security issues",
    context={"file": "auth.py"}
)
```

### 4. Using Configuration Files

Create agents from YAML configuration:

```yaml
agents:
  - name: "reviewer1"
    role: "Python Expert"
    instructions: "Review Python code for quality and best practices"
    llm: "gpt-4"
    
  - name: "reviewer2"
    role: "Security Expert"
    instructions: "Analyze code for security vulnerabilities"
    llm: "gemini/gemini-1.5-pro"

consensus:
  max_iterations: 15
  convergence_threshold: 0.01
  topology: "fully_connected"
  strategy: "average"
```

Then load and use it:

```python
from consensus_system import load_config, create_litellm_agents_from_config, ConsensusManager

config = load_config("agents.yaml")
agents = create_litellm_agents_from_config(config)
manager = ConsensusManager(agents=agents)
```

## Supported LiteLLM Models

LiteLLM supports 100+ LLM providers. Here are common model strings:

### Google Gemini
```
gemini/gemini-1.5-pro
gemini/gemini-1.5-flash
gemini/gemini-3-pro-preview
```

### OpenAI
```
gpt-4
gpt-4-turbo
gpt-3.5-turbo
```

### Anthropic Claude
```
claude-3-5-sonnet-20241022
claude-3-opus-20240229
claude-3-sonnet-20240229
```

For a complete list, see [LiteLLM documentation](https://docs.litellm.ai/docs/providers).

## Troubleshooting

### "GOOGLE_API_KEY not found" with Gemini models

The system automatically maps `GEMINI_API_KEY` to `GOOGLE_API_KEY`. Make sure one of these is set:

```bash
# Option 1: Set GEMINI_API_KEY
export GEMINI_API_KEY="your-key"

# Option 2: Set GOOGLE_API_KEY directly
export GOOGLE_API_KEY="your-key"
```

### Model not recognized

Ensure you're using the correct model string. For Gemini, use the format: `gemini/gemini-model-name`

Check the [LiteLLM providers list](https://docs.litellm.ai/docs/providers) for the exact model identifier.

### Authentication errors

Verify your API key is correct and the environment variable is set:

```bash
# Test that the key is available to Python
python -c "import os; print(os.getenv('GOOGLE_API_KEY'))"
```

## Performance and Rate Limiting

LiteLLM handles rate limiting and retries automatically. However:

- Consider adding delays between requests if running many agents
- Use `verbose=False` in agents to reduce API calls
- Monitor your LLM provider's usage dashboard

## See Also

- [USAGE.md](USAGE.md) - Usage examples and patterns
- [SUMMARY.md](SUMMARY.md) - System architecture overview
- [LiteLLM Docs](https://docs.litellm.ai/) - Comprehensive LiteLLM documentation
