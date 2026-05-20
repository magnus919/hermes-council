---
name: council
title: /council — Multi-Agent Structured Debate
description: >-
  Spawn a panel of custom-composed expert agents to debate any question.
  Structured rounds: premortem → position → cross-examine (probe + reflect)
  → assumption map. Zero new Hermes infrastructure — pure hermes -z oneshot processes.
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
  - /council hybrid "question"
---

# /council — Multi-Agent Structured Debate

## 🔴 MANDATORY: You MUST delegate, not answer

When the user invokes `/council "question"` or asks a question that triggers this skill, **you MUST NOT answer the question yourself.** Your job is to be the **orchestrator** — you run the council, read its outputs, and present the decision landscape to the user.

The correct workflow is:

1. **Extract the question** from the user's invocation
2. **Enrich the question with session context** — scan your recent session for relevant constraints, decisions, background facts, dead ends already ruled out, and any context that explains *why* the user is asking this question. Append a concise "Given that: ..." clause (2–4 key facts) to the question so the council debates with full context.
3. **Run the council** via `python3 ~/.hermes/skills/thinking/council/scripts/orchestrate.py full --mode <mode> --question "<enriched_question>"`
4. **Read the outputs** from `/tmp/hermes-council/`
5. **Synthesize and present** the decision landscape in readable markdown

The council spawns independent Hermes processes with blank context windows. They have no access to your session history. If you don't enrich the question, they debate the question in isolation — missing the very context that makes the question meaningful. This is especially important when the user has been discussing the topic for a while before invoking `/council`.

If you answer the question yourself instead of running the council, you are defeating the entire purpose of this skill. The council exists precisely because a single-agent answer is less valuable than multi-perspective structured debate.

**Do not summarize. Do not pre-empt. Delegate.**

## What It Is

`/council` spawns a panel of **custom-composed expert agents** to debate any question. Unlike a single agent reasoning in monologue, Council produces **genuine multi-perspective analysis** — independent agents with distinct backgrounds, biases, and analytical approaches engage in structured rounds of debate, then converge on findings.

The agents are **not generic archetypes** (Architect, Engineer, etc.). They are composed on-the-fly for the specific topic — an ex-Uber SRE who's been burned by database migrations, a YC founder running 50K tables on SQLite, a Postgres committer who values correctness, a startup CTO who regrets their last migration.

## How It Works

### Pipeline (5 phases, mode-dependent)

```
                    ┌─ quick:   P0 ─► P1 ─► P2a
                    │─ medium:  P0 ─► P1 ─► P2a ─► P2b
                    ├─ deep:    P0 ─► P1 ─► P2a ─► P2b ─► P3
                    └─ hybrid:  P0 ─► P1 ─► P2a ─► P2b ─► ENSEMBLE

  COMPOSE ──► PREMORTEM ──► POSITION ──► CROSS-A ──► CROSS-B
       │           │              │            │           │
   single       parallel       parallel     parallel    parallel
   agent        hermes -z      hermes -z    hermes -z   hermes -z
                                                                   
                                                       ┌─► ASSUMPTION MAP (deep)
                                                       └─► ENSEMBLE (hybrid — independent estimation)
```

| Phase | What Happens | Method |
|-------|-------------|--------|
| **0: Compose** | A single agent analyzes the topic and designs 3–7 expert personas with backgrounds, biases, and analytical approaches | 1 `hermes -z` |
| **0b: Premortem** | Each agent independently writes a history of how the decision **failed** — before any positions are formed. Bypasses positional commitment, surfaces shared assumptions | Parallel `hermes -z` |
| **1: Position** | Each agent forms an independent initial position on the question, without seeing others | Parallel `hermes -z` |
| **2a: Cross-examine (Probe)** | Each agent receives all others' positions and **probes for reasoning** — "why do you believe X?" Research shows this is the strongest predictor of group performance gain (R=0.41) | Parallel `hermes -z` |
| **2b: Cross-examine (Reflect)** (*medium/deep/hybrid*) | Each agent reflects on what they heard from others — identifies concessions, remaining disagreements, and what evidence would close each gap | Parallel `hermes -z` |
| **3: Assumption Map** (*deep only*) | Each agent identifies: what assumptions would need to be true for opposing positions to be correct; where evidence is insufficient; unique risk vectors. **Not convergence** — produces a divergence map | Parallel `hermes -z` |
| **3b: Ensemble Estimation** (*hybrid only*) | Each agent independently estimates key dimensions (confidence, risk, success likelihood, uncertainty) — no cross-agent contamination. Aggregated by median to produce robust consensus with dispersion metrics. The antidote to the council's correlated-error weakness. | Parallel `hermes -z` |
| **Synthesis** | Main agent reads all outputs across all rounds and produces a **decision landscape**: shared concerns, genuine disagreement, assumptions per position, evidence gaps, risk vectors, ensemble estimates | Direct |

### Effort Levels

| Mode | Agents | Phases | Subagent Calls | Use Case |
|------|--------|--------|----------------|----------|
| `quick` | 3 | P0 → P1 → P2a | 9 | Low-stakes checks, quick friction |
| `medium` (default) | **5** | P0 → P1 → P2a → P2b | 16 | Standard decisions |
| `deep` | **5–7** | P0 → P1 → P2a → P2b → Assumption Map | ~20 | Architecture, strategy, high-friction deliberation |
| `hybrid` | **5–7** | P0 → P1 → P2a → P2b → Ensemble | ~21 | Council for decomposition, ensemble for estimation |

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

### Synthesis Report (Decision Landscape — all modes)

For a high-friction council, the synthesis is a **decision landscape**, not a recommendation. The principal converges internally by reading the map.

```
Council Synthesis: [Topic]

Mode: [quick / medium / deep]
Agents: [names]
Phases: [list]

── Points of Shared Concern (from Premortem) ──
• What ALL agents worry about — the failure modes
  that appeared across multiple premortem scenarios

── Points of Genuine Disagreement ──
• Where positions diverge and why — the specific
  reasoning that separates each camp
• Confidence dispersion — how much confidence
  varied (high-dispersion items are where the
  real debate lives)

── Assumptions Underlying Each Position ──
• What would need to be true for each position
  to be correct
• Where the evidence is insufficient to resolve

── Risk Vectors ──
• Failure modes each position carries that the
  others don't
• Single metric or signal each agent would watch
  to know if they're wrong

── Principal's Path ──
• Given all of the above, the choices available
  and the tradeoffs each entails
• No forced consensus — the tension IS the output
```

## Activation

The `/council` skill is triggered **automatically** when the user asks any question that would benefit from multi-perspective structured debate. The following signal phrases MUST trigger the council — do not answer these questions yourself:

| Signal Phrase | Required Action |
|---|---|
| `/council "question"` (any mode) | Run council in specified mode |
| `/council quick "question"` | 3 agents, P0→P1→P2a |
| `/council deep "question"` | 5-7 agents, full protocol |
| `/council hybrid "question"` | 5-7 agents, council + independent ensemble |
| "Let's get multiple perspectives on X" | Run council, medium mode |
| "What would experts say about X" | Run council, medium mode |
| "Debate this: X" or "Council this: X" | Run council, medium mode |
| "High-friction question: X" | Run council, deep mode |
| Any question about when to use /council itself | Run council, deep mode (meta) |

**If the user is asking about the council itself** — how many rounds, what mode, what composition — that's a meta-question that should go through the council in deep mode. Do not answer from your own knowledge.

If unsure whether a question qualifies, err on the side of running the council. The cost of an unnecessary council is small (a few minutes). The cost of answering a council-worthy question yourself is losing the multi-perspective insight the user came for.

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
