# Debate Protocol

## Round Structure

### Round 1: Position Formation

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
  "evidence_needed": [
    "What information would change their mind"
  ]
}
```

### Round 2: Cross-Examination

Each agent receives:
- Their own Round 1 output
- All other agents' Round 1 outputs (anonymized or attributed — see below)
- The original question

**Attribution decision:** In PAII's Council, transcripts are visible and attributed. This creates accountability — agents can be called out. Anonymous cross-examination reduces posturing but loses the social dynamic. Default: attributed.

Produces structured JSON:
```json
{
  "revised_position": "Updated stance after reading other perspectives",
  "conceded_to": [
    {"agent": "Name", "point": "What was conceded and why"}
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
