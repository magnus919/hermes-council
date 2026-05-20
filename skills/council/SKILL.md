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

| Mode | Rounds | Agents | Cost | When |
|------|--------|--------|------|------|
| `quick` | 2 (Position + Cross-examine) | 3 agents | ~7 subagent calls | Low-stakes, broad checks |
| `medium` (default) | 3 (Position + Cross-examine + Converge) | 4 agents | ~13 subagent calls | Standard use |
| `deep` | 3 + full synthesis report | 5–6 agents | ~19 subagent calls | High-stakes architecture decisions |

### Compose Phase (The Key Innovation)

The compose phase is a single `delegate_task` with a prompt like:

> For the question "[topic]", design N expert debating agents.
> For each agent: name, one-paragraph career background, specific expertise,
> analytical approach, and what bias or experience they bring to THIS question.
> Design them to create productive friction — real disagreement grounded in
> real experience, not caricatures. Return structured JSON.

The output is a roster of persona definitions that get passed into every subsequent `delegate_task` context, giving each subagent a richly textured identity formed specifically for this topic.

## Composition Guidance

**Never use generic types.** Every agent must be composed for the specific topic. See `references/composition-guide.md` for worked examples.

**4–6 well-composed agents outperform 12 generic ones.** The goal is productive friction — each agent should bring a genuinely different lens. If two agents would mostly agree, one is redundant.

**Design roles around the topic, not a menu.** A database migration question needs different expertise than a security architecture question. The compose phase handles this automatically by analyzing the topic before designing the panel.

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

## References

- `references/composition-guide.md` — worked examples for composing councils by topic domain
- `references/personas/` — example persona templates (used by the compose phase as seed data)
- `references/debate-protocol.md` — round structure, timing, output format for each phase
- `scripts/orchestrate.py` — optional orchestrator for managing the round lifecycle
