# Debate Protocol

## Round Structure

### Round 0: Premortem (all modes — standard, not optional)

Before any positions are formed, each agent independently answers:

> "Imagine the decision being debated was made and failed completely. Write a brief history of how that failure happened — the chain of events, the assumptions that turned out wrong, the signals that were missed."

**Why this is standard:** The premortem bypasses positional commitment entirely. Research on adversarial collaboration (Kahneman) and group decision-making shows that agents who state a position first become psychologically committed to it, reducing their ability to consider alternatives. The premortem surfaces shared assumptions and risks before anyone's ego is invested in a stance.

Each agent's premortem is **private** — not shared with other agents — but collected for the synthesis phase. This prevents the premortem framing from anchoring the subsequent debate.

Produces structured JSON:
```json
{
  "premortem_scenario": "3-5 paragraph failure history",
  "failure_modes": ["specific failure mode 1", "mode 2", ...],
  "missed_signals": ["signal 1", "signal 2", ...]
}
```

### Round 1: Position Formation

Each agent forms their initial position **without seeing others' positions** (prevents anchoring). 

Each agent receives:
- Their composed persona definition (background, bias, analytical approach)
- The question being debated
- Any relevant context provided by the user

Produces structured JSON:
```json
{
  "position": "Concise stance on the question — 2-3 sentences",
  "reasoning": [
    "Primary argument with evidence",
    "Secondary argument",
    "Tertiary argument or consideration"
  ],
  "concerns": [
    "What worries them about their own position",
    "What would need to be true for the alternative to be better"
  ],
  "confidence": 0.0-1.0,
  "evidence_needed": "Single piece of evidence that would change their mind"
}
```

### Round 2a: Cross-Examination — Probing for Reasoning

Research (Karadzhov et al. 2024) shows that **probing for reasoning** — asking "why do you believe X?" and "what evidence supports that?" — is the single strongest predictor of group performance gain (Pearson R = 0.41, PCR coefficient 0.83). This round is structured around that mechanism.

**This is the money round.** For a high-friction council, most of the insight is produced here.

Each agent receives:
- Their own Round 1 output
- All other agents' Round 1 outputs (attributed)
- The original question
- The confidence dispersion (how much confidence varied across agents — high-dispersion items are the debate focus)

**Instructions:** Prioritize probing for reasoning over proposing solutions. For each point of disagreement, ask *why* the other agent holds that position before stating your counter-position. Identify what you can concede and where your disagreement remains genuinely unresolved.

Produces structured JSON:
```json
{
  "revised_position": "Updated stance after reading other perspectives",
  "conceded_to": [
    {"agent": "Name", "point": "What was conceded and why", "what_changed_my_mind": "The specific reasoning or evidence that shifted my view"}
  ],
  "probes_for_reasoning": [
    {"agent": "Name", "question": "What I asked them about their reasoning"},
    {"agent": "Name", "response": "How they answered or what I inferred"}
  ],
  "disagrees_with": [
    {"agent": "Name", "point": "What remains unresolved and why"}
  ],
  "new_insights": [
    "What reading others' positions revealed that wasn't in your initial analysis"
  ],
  "updated_confidence": 0.0-1.0
}
```

### Round 2b: Cross-Examination — Reflection & Update (medium/deep modes)

A second pass of cross-examination. Each agent reads the complete cross_a outputs — all concessions, probes, and disagreements from every agent — and produces a structured reflection.

**Why a second pass?** High-friction groups need more cycles to surface the assumptions beneath the reasoning, not just the reasoning itself. Round 2a surfaces *what* others believe and *why*. Round 2b forces each agent to ask "what does this mean for my position?"

Each agent receives:
- Their own persona and initial position
- All cross_a outputs from other agents (what each conceded, probed, and still disagrees on)

Produces structured JSON:
```json
{
  "reflection": "What I heard and how it affected my thinking",
  "conceded": [
    {"to_agent": "Name", "on_point": "Specific point", "why": "Why I conceded this"}
  ],
  "remaining_disagreements": [
    {"with_agent": "Name", "what": "What we still disagree on", "what_would_close_gap": "Specific evidence or reasoning that would resolve this"}
  ],
  "updated_position": "My stance after reflection",
  "updated_confidence": 0.0-1.0
}
```

### Round 3: Assumption Mapping (deep mode only — replaces "convergence")

**This is the key change from the original protocol.** Instead of forcing agents to converge on a recommendation, each agent produces an *assumption map* — identifying what would need to be true for opposing positions to be correct, and where evidence is insufficient to resolve disagreements.

**Why this change:** The inverted-U research on cognitive diversity shows that pushing diverse groups to converge prematurely produces false consensus — agents agree on conclusions they don't actually believe, suppressing the tension that makes the council valuable. The principal doesn't need the council to agree; they need every defensible position made legible.

Each agent receives:
- Full debate transcript (positions, cross_a, cross_b)
- All agents' outputs across all rounds

Produces structured JSON:
```json
{
  "assumptions_for_opposing": [
    {
      "position": "Name of opposing position",
      "what_would_need_to_be_true": ["assumption 1", "assumption 2", ...],
      "evidence_insufficient": "What we still don't know"
    }
  ],
  "unique_risk_vectors": [
    "Risk that my position carries that others don't",
    "Risk that the alternative carries that I'm most concerned about"
  ],
  "what_i_would_watch": "Single metric or signal I'd track to know if I'm wrong"
}
```

## Synthesis: Decision Landscape (all modes)

The synthesis phase reads all outputs across all rounds and produces a **decision landscape** — not a weighted recommendation. The principal reads the map and converges internally.

| Layer | Source | Output |
|-------|--------|--------|
| Points of shared concern | Premortem round | What ALL agents worry about — failure modes appearing across multiple scenarios |
| Points of genuine disagreement | Position + cross rounds | Where positions diverge and why; confidence dispersion |
| Assumptions per position | Assumption map round | What would need to be true for each position; evidence gaps |
| Risk vectors | Cross + assumption rounds | Failure modes each option carries; signals to watch |
| Principal's path | Synthesis | Given all of the above, the tradeoffs and choices available |

## Timing

| Phase | Expected duration | Notes |
|-------|------------------|-------|
| Compose | ~15 seconds | One agent. Fast. |
| Premortem | ~30–60 seconds | Parallel. New. |
| Position round | ~30–60 seconds | Parallel. Batch of 3 + remainder. |
| Cross-examine A | ~30–60 seconds | Parallel. Same batching. |
| Cross-examine B | ~30–60 seconds | Medium/deep modes only. |
| Assumption map | ~30–60 seconds | Deep mode only. |
| Synthesis | Immediate | Main agent reads outputs, no subagents. |
| **Total (quick mode)** | **~2–3 minutes** | 9 subagent calls |
| **Total (medium mode)** | **~3–5 minutes** | 16 subagent calls |
| **Total (deep mode)** | **~4–6 minutes** | ~20 subagent calls |

## Output Schema

Every subagent output must be valid JSON for reliable programmatic parsing across rounds. The `hermes -z` result is the agent's final response text, so each agent must be instructed to output valid JSON as its entire response.
