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
| `quick` | 3 (hard min) | 2 | Low-stakes checks |
| `medium` (default) | 5 (research sweet spot) | 2 | Standard decisions |
| `deep` | 5–7 | 3 + premortem | Architecture, strategy, high-stakes |

## Inference

Council sub-agents resolve their provider and model in this priority:

1. **`auxiliary.council`** — add a `council` entry under `auxiliary:` in `~/.hermes/config.yaml`
2. **`delegation` section** — standard Hermes sub-agent delegation config
3. **`model` section** — your main agent's provider and model

```yaml
# ~/.hermes/config.yaml
auxiliary:
  council:
    provider: opencode-go
    model: deepseek-v4-flash
```

If none are configured, council agents inherit your main session's settings.

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

## Inspiration

This project was inspired by **PAII** (Personal AI Infrastructure) by Daniel Miessler, specifically its [Council skill](https://github.com/danielmiessler/Personal_AI_Infrastructure/tree/main/Packs/Council) — a multi-agent debate system that composes custom expert agents with domain expertise, unique voices, and distinct analytical approaches. The Hermes Council implementation adapts PAII's composition philosophy and adversarial collaboration principles to run natively on Hermes Agent's existing infrastructure (oneshot spawning, skill system) with zero external dependencies.

Additional research influences:
- Karadzhov et al. (2024) — large-scale Wason task dialogue study on group reasoning
- Kahneman, Sibony & Sunstein — *Noise: A Flaw in Human Judgment* (adversarial collaboration)
- Berditchevskaia & Bertoncin — Nesta Collective Intelligence Review (group composition)
- Mercier & Sperber — *The Enigma of Reason* (argumentative theory of reasoning)
