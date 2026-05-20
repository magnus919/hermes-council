---
name: council
title: /council — Multi-Agent Structured Debate
description: >-
  Spawn a panel of custom-composed expert agents to debate any question.
  Structured rounds: compose → position → cross-examine → converge → synthesize.
  Zero new Hermes infrastructure — pure delegate_task + skill system.
version: 0.1.0
author: Jasper
tags: [debate, multi-agent, council, thinking, reasoning]
metadata:
  hermes:
    category: thinking
    requires_toolsets: [delegation]
triggers:
  - /council "question"
  - /council quick "question"
  - /council deep "question"
---

# /council — Multi-Agent Structured Debate

## What It Is

`/council` spawns a panel of **custom-composed expert agents** to debate any question. Unlike a single agent reasoning in monologue, Council produces **genuine multi-perspective analysis** — independent agents with distinct backgrounds, biases, and analytical approaches engage in structured rounds of debate, then converge on findings.

The agents are **not generic archetypes** (Architect, Engineer, etc.). They are composed on-the-fly for the specific topic — an ex-Uber SRE who's been burned by database migrations, a YC founder running 50K tables on SQLite, a Postgres committer who values correctness, a startup CTO who regrets their last migration.

## How It Works

### Pipeline (5 phases)

```
Topic ─► COMPOSE ─► POSITION ─► CROSS-EXAMINE ─► CONVERGE ─► SYNTHESIZE
                      │             │               │
                  parallel       parallel        parallel
                 delegate_task  delegate_task   delegate_task
```

| Phase | What Happens | Method |
|-------|-------------|--------|
| **1. Compose** | A single `delegate_task` analyzes the topic and designs 4–6 expert personas with backgrounds, biases, and analytical approaches | 1 subagent |
| **2. Position** | Each composed agent forms an independent initial position on the question | Parallel `delegate_task` (batched at 3 concurrent) |
| **3. Cross-examine** | Each agent receives all other agents' positions and responds — defends, concedes, or crystallizes disagreement | Parallel `delegate_task` |
| **4. Converge** (deep only) | Each agent reads full debate transcript and identifies points of agreement and non-negotiable red lines | Parallel `delegate_task` |
| **5. Synthesize** | Main agent reads all outputs across all rounds and produces consensus/divergence map + recommendation | Direct |

### Effort Levels

| Mode | Agents | Rounds | Use Case |
|------|--------|--------|----------|
| `quick` | 3 (hard min) | 2 rounds | Low-stakes checks |
| `medium` (default) | **5 (research sweet spot)** | 2 rounds | Standard decisions |
| `deep` | **5–7** | 3 rounds + premortem | Architecture, strategy |

### Compose Phase (The Key Innovation)

The compose phase is a single `delegate_task` (or Hermes oneshot agent) with a prompt like:

> For the question "[topic]", design **5** expert debating agents.
>
> **Critical directive:** Prioritize **diversity of initial position** over diversity of expertise.
> Research shows that a group with four distinct approaches to a problem — none individually
> correct — outperforms a group with more expertise but shared framing.
>
> For each agent: name, one-paragraph career background, specific expertise, analytical
> approach, and what bias or experience they bring to THIS question. At least one agent
> should be structurally skeptical (a "light red team" role). At least one agent should
> approach the problem from a fundamentally different cognitive frame than the others.
>
> Design them to create productive friction — real disagreement grounded in real
> experience, not caricatures. Ensure every position is defensible.
>
> Return structured JSON.

The output is a roster of persona definitions that get passed into every subsequent `delegate_task` context, giving each subagent a richly textured identity formed specifically for this topic.

## Composition Guidance

**Diversity of initial position > diversity of expertise.** Research (Karadzhov et al. 2024) shows that a group of four people who approach a problem from four distinct angles, none individually correct, will converge on a better answer than four people who already know the right answer but think about it the same way.

**4–7 people, 5 is the research sweet spot.** Below 3, you lack idea pool diversity. Above 7, coordination costs degrade deliberation.

**At least one structurally skeptical member.** Assign a light red team role — someone whose default posture is to stress-test the leading plan. Not as an adversary, but as a scheduled obligation.

**At least one fundamentally different cognitive frame.** Someone who approaches problems from first principles when everyone else is being pragmatic, or vice versa. The inverted-U research shows this prevents groupthink while staying within communication range.

**Design for task conflict, not relationship conflict.** Agents should disagree on conclusions, not on each other's competence. Every position should be defensible and grounded in real experience.

See `references/composition-guide.md` for worked examples and `references/composition-research.md` for the full research synthesis.

## Output Format

### Synthesis Report

```
╔══════════════════════════════════════════════════╗
║  Council Synthesis: [Topic]                     ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║  Panel: [Agent 1], [Agent 2], ..., [Agent N]    ║
║  Mode: [quick / medium / deep]                  ║
║  Rounds: [N]                                    ║
║                                                  ║
║  ── Points of Consensus ──                      ║
║  • What every agent agreed on                    ║
║                                                  ║
║  ── Points of Divergence ──                     ║
║  • Where they disagreed and why                  ║
║                                                  ║
║  ── Key Insights ──                              ║
║  • What emerged that wasn't obvious at the start ║
║                                                  ║
║  ── Recommendation ──                            ║
║  • Weighted by confidence and domain relevance   ║
║    Security concerns weighted higher for infra   ║
║    Business concerns weighted higher for         ║
║    strategy decisions                            ║
╚══════════════════════════════════════════════════╝
```

## Activation

The skill auto-routes on:
- `/council "question"` — medium mode (default)
- `/council quick "question"` — fast check, 2 rounds, 3 agents
- `/council deep "question"` — full protocol, 3 rounds, 5-6 agents
- Phrases like "let's get multiple perspectives", "what would experts say", "debate this", "council"

## Inference

Council sub-agents are spawned as independent Hermes processes (`hermes -z`). They resolve their provider and model from your Hermes config in this priority order:

1. **`auxiliary.council`** — if you have a `council` entry under `auxiliary:` in `~/.hermes/config.yaml`, it is used. This follows the same pattern as Hermes' other auxiliary tasks (vision, session_search, etc.) and is the recommended way to configure council-specific inference.

2. **`delegation` section** — `delegation.provider` and `delegation.model`. Falls back to the Hermes sub-agent delegation config if set.

3. **`model` section** — your main agent's provider and model.

4. **Built-in fallback** — `deepseek` / `deepseek-v4-flash` as a last resort.

### Examples

Run council agents on a cheap fast model while using a premium model for your main session:

```yaml
# ~/.hermes/config.yaml
auxiliary:
  council:
    provider: opencode-go
    model: deepseek-v4-flash
```

Or use a premium model just for the council:

```yaml
auxiliary:
  council:
    provider: openrouter
    model: anthropic/claude-sonnet-4
```

If neither `auxiliary.council` nor `delegation` are configured, council agents inherit your main session's provider and model — no additional config needed.
- `references/personas/` — example persona templates (used by the compose phase as seed data)
- `references/debate-protocol.md` — round structure, timing, output format for each phase
- `scripts/orchestrate.py` — optional orchestrator for managing the round lifecycle
