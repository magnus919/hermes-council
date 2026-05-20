# Hermes Council

**Multi-agent structured debate for [Hermes Agent](https://github.com/NousResearch/hermes-agent).**

Spawn a panel of custom-composed expert agents to debate any question. Agents are designed specifically for each topic — not generic archetypes — and engage in structured rounds of debate to surface genuine multi-perspective analysis.

## How It Works

A five-phase pipeline, built entirely on Hermes' existing `delegate_task` infrastructure:

```
Topic ─► COMPOSE ─► POSITION ─► CROSS-EXAMINE ─► CONVERGE ─► SYNTHESIZE
```

| Phase | What Happens |
|-------|-------------|
| **Compose** | A subagent analyzes the topic and designs 4–6 expert personas with backgrounds, biases, and analytical approaches tailored to the specific question |
| **Position** | Each agent forms an independent initial position — parallel subagent calls |
| **Cross-examine** | Each agent reads all other positions and responds — parallel subagent calls |
| **Converge** (deep mode) | Each agent identifies points of consensus and non-negotiable disagreements |
| **Synthesize** | Main agent produces a consensus/divergence map with weighted recommendations |

## Zero New Infrastructure

No Hermes source code changes. No plugins. No MCP servers. Pure SKILL.md + `delegate_task`.

```bash
# In any Hermes session:
/skill council
/council "Should we migrate from SQLite to Postgres?"
```

Or directly:
```
/council deep "Design the auth architecture for a multi-tenant SaaS"
/council quick "Is this a good approach?"
```

## Effort Levels

| Mode | Agents | Rounds | Use Case |
|------|--------|--------|----------|
| `quick` | 3 | 2 | Low-stakes checks, fast perspective |
| `medium` (default) | 4 | 3 | Standard decisions |
| `deep` | 5–6 | 3 + full report | Architecture, strategy, high-stakes |

## Composition Philosophy

**Never use generic agent types.** Every council member is composed for the specific topic — for example, a database migration debate might include:

- An ex-Uber SRE who was burned by a failed migration
- A YC founder who ran 50K tables on SQLite for 3 years
- A Postgres committer who values correctness
- A startup CTO who regrets their last migration

They are designed to create productive friction — real disagreement grounded in real experience, not caricatures.

## Repository Structure

```
hermes-council/
├── skills/
│   └── council/
│       ├── SKILL.md                    # Workflow definition
│       ├── references/
│       │   ├── composition-guide.md    # Worked examples by domain
│       │   ├── debate-protocol.md      # Round structure & JSON schemas
│       │   └── personas/               # Example persona templates
│       └── scripts/
│           └── orchestrate.py          # Optional lifecycle manager
├── README.md
└── LICENSE
```

## Installation

Clone into your Hermes skills directory:

```bash
git clone https://github.com/magnus919/hermes-council.git
ln -s $(pwd)/hermes-council/skills/council ~/.hermes/skills/thinking/council
```

Then `/skill council` in any Hermes session.

## License

MIT
