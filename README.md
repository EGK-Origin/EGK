# EGK — Erasable Growth Kernel

> 具身成长内核：一个零外部依赖的具身认知智能体框架

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

EGK is a minimal embodied cognitive agent framework that simulates:

- **Perception mapping** — distance, zone status, user emotions
- **Emotion dynamics** — curiosity, information satiation, value cognition, anxiety
- **Attachment system** — social value feedback from users
- **Value-action coupling** — reward / no-reward / sacrifice phases
- **Memory buffer** — structured event storage with tag-based retrieval
- **Metacognitive reflection** — periodic internal monologue generation

All behavior is driven by internal desire weights; the agent retains the freedom to "do nothing."

## Quick Start

```bash
python EGK_Core.py
```

This runs the Stage 9 altruism reproduction (3000 steps) and prints the agent's final reflection.

## Architecture

```
┌─────────────────────────────────────────┐
│  Perception Layer  (perceive)           │
│  → distances, zone status, user emotions  │
├─────────────────────────────────────────┤
│  Emotion Dynamics  (update_emotion)       │
│  → curiosity, satiation, value, anxiety   │
├─────────────────────────────────────────┤
│  Desire Computation (compute_desires)   │
│  → native weight matrix, no coercion    │
├─────────────────────────────────────────┤
│  Action Selection  (select_action)        │
│  → free-will noise + weight ranking     │
├─────────────────────────────────────────┤
│  Physical Execution (execute)             │
│  → box pushing, light approach, empathy │
└─────────────────────────────────────────┘
```

## API Example

```python
from EGK_Core import EGKAgent

agent = EGKAgent(start_pos=(0.0, -15.0), energy=100.0)
agent.register_box("red", -8.0, 0.0)
agent.register_user("Alice", -2.0, -2.0, "red")

for i in range(100):
    agent.step(phase="reward")

print(agent.reflect())
print(agent.get_action_summary())
```

## Running Tests

```bash
# Run all unit tests
python -m pytest test_egk.py -v

# Or without pytest
python test_egk.py
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).
