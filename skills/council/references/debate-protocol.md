# Debate Protocol

## Round Structure

### Round 0: Silent Independent Preference (Premortem — deep mode only)

Before any positions are formed, each agent independently answers:

> "Imagine the decision being debated was made and failed completely. Write a brief history of how that failure happened."

This surfaces hidden assumptions and risks before anyone is committed to a position. Each agent's premortem is private — not shared with other agents — but collected for the synthesis phase.

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
  "evidence_needed": "Single piece of evidence that would change their mind",
  "premortem": "Their premortem scenario (deep mode only)"
}
```

### Round 2: Cross-Examination — Probing for Reasoning

Research (Karadzhov et al. 2024) shows that **probing for reasoning** — asking "why do you believe X?" and "what evidence supports that?" — is the single strongest predictor of group performance gain. This round is structured around that mechanism.

Each agent receives:
- Their own Round 1 output
- All other agents' Round 1 outputs (attributed)
- The original question
- The confidence dispersion (how much confidence varied across agents — high-dispersion items are the debate focus)

**Instructions:** Prioritize probing for reasoning over proposing solutions. For each point of disagreement, ask why the other agent holds that position before stating your counter-position. Identify what you can concede and where your disagreement remains genuinely unresolved.

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

### Round 3: Convergence (deep mode only)

Each agent receives:
- Full transcript of Rounds 1 and 2
- All agents' outputs across both rounds

Produces structured JSON:
```json
{
  "final_position": "Where they land — 1-2 sentences",
  "can_agree_on": [
    "Specific points of consensus they accept"
  ],
  "red_lines": [
    "Non-negotiable disagreements — things they cannot accept"
  ],
  "recommendation": "What action they would take if the decision were theirs"
}
```

## Timing

| Phase | Expected duration | Notes |
|-------|------------------|-------|
| Compose | ~15 seconds | One subagent. Fast. |
| Position round | ~30-60 seconds | Parallel. Batch of 3 + remainder. |
| Cross-examine round | ~30-60 seconds | Parallel. Same batching. |
| Converge round | ~30-60 seconds | Deep mode only. |
| Synthesis | Immediate | Main agent reads outputs, no subagents. |
| **Total (medium mode)** | **~2-3 minutes** | |
| **Total (deep mode)** | **~3-5 minutes** | |

## Output Schema

Every subagent output must be valid JSON for reliable programmatic parsing across rounds. The `delegate_task` result is a text summary, so the agent in each round must be instructed to output valid JSON in its summary.
