# Council Composition Guide

## The Core Principle

**Diversity of initial position > diversity of expertise.** Research (Karadzhov et al. 2024) demonstrates that a group of four people who approach a problem from four distinct angles, none individually correct, will converge on a better answer than a group of four people two of whom already know the right answer but think about it the same way.

**Design roles around the topic, not a menu.** Generic archetypes (Architect, Engineer, Designer) produce shallow, predictable perspectives. A council debating "should we migrate to Postgres" needs agents who have *been burned by migrations* and agents who have *saved companies with them* — not generic "engineer" and "architect" labels.

## Composition Strategy

When composing a council, ask:

1. **What domains does this question touch?** (infrastructure, business, UX, security, ethics)
2. **What failure modes are relevant?** (migrations fail from ops complexity, not bad queries)
3. **What experiential backgrounds would create productive friction?** (skeptic vs builder, pragmatist vs purist)
4. **What evidence types would settle disagreements?** (benchmarks, case studies, cost models)

Each agent should have:
- **A specific career background** — not "engineer" but "6 years at Uber SRE, was on-call during a failed migration"
- **A clear bias** — everyone has one; the council works when biases are explicit and in tension
- **A distinct analytical approach** — one agent starts from first principles, another from real-world case studies, another from risk modeling
- **Something to lose** — the best debates happen when agents have skin in the game (their past decisions were right or wrong)

## Worked Examples

### Infrastructure Decision: "Should we migrate from SQLite to Postgres?"

| Agent | Background | Bias | Approach |
|-------|-----------|------|----------|
| Alex Chen, ex-Uber SRE | Was on-call for a failed database migration at Uber. Now at a seed-stage startup. | Deeply skeptical of migrations. Values operational simplicity. | Starts from failure modes — "what breaks first" — works backward. |
| Maya Torres, YC founder | Built a SaaS product that ran 50K tables on SQLite for 3 years. Just migrated. | Believes in right-sizing infrastructure to actual needs, not hypothetical scale. | Evidence-based: benchmarks, cost models, actual pain points. |
| David Park, Postgres committer | Contributor to PostgreSQL for 8 years. Consults on database architecture. | Values correctness, consistency, and ecosystem maturity. | Systematic feature comparison. Cares about edge cases and data integrity. |
| Rachel Kim, startup CTO | Led a migration that took 6 months instead of 2. Regrets not staying on simpler tech. | Nuanced — believes migrations are sometimes necessary but almost always underestimated. | Risk-weighted decision framework. Probability × impact for each risk vector. |

### Security Architecture: "Should we adopt a zero-trust network model?"

| Agent | Background | Bias | Approach |
|-------|-----------|------|----------|
| Sarah Chen, security architect | Designed zero-trust for a FAANG company. Left when they still had breaches. | Believes zero-trust is oversold — it shifts the attack surface, doesn't eliminate it. | Threat modeling: what does this actually defend against? |
| James Okafor, CISSP practitioner | Implemented zero-trust for a mid-size fintech. Saw 60% reduction in incident response time. | Generally positive on zero-trust, but pragmatic about cost. | Case-study driven: what worked, what didn't, what it cost. |
| Elena Vasquez, network engineer | Runs the network for a 2000-person company. Worries about complexity. | Skeptical of architectural religion. Cares about whether the night team can debug a fault. | Operational realism: runbooks, MTTR, training requirements. |
| Tariq Hassan, CISO | Has to report to a board. Needs to show due diligence without breaking the budget. | Wants to know the compliance angle and the ROI. | Regulatory and business-risk framing: what must we do vs what should we do. |

### Product Strategy: "Should we build a mobile app or invest more in our web experience?"

| Agent | Background | Bias | Approach |
|-------|-----------|------|----------|
| Priya Singh, mobile PM | Launched 3 mobile apps. Two succeeded. Knows the distribution game. | Believes mobile is essential for retention and engagement. | Data-driven: platform usage patterns, retention cohorts, install-to-active ratios. |
| Tom Fitzgerald, web engineer | Has seen "we need an app" kill two startups via scope creep. | Skeptical of mobile as a default answer. Wants to see the evidence. | Cost-benefit: dev cost × maintenance burden vs incremental engagement. |
| Aisha Patel, growth marketer | Runs acquisition. Knows where users come from and why they churn. | Neutral on platform. Cares about what moves the metric. | Attribution analysis: what's actually driving the retention problem? |

## Anti-Patterns

| Anti-pattern | Why it fails |
|-------------|-------------|
| **All agents agree** | You selected for harmony instead of friction. Redesign for disagreement. |
| **Caricatures** | "The crazy one" or "the cynic" — these produce noise, not insight. Every agent should have a defensible position. |
| **Too many agents** | 6 is the ceiling. Beyond that, agents repeat each other and synthesis becomes noise. 4 is often optimal. |
| **Domain mismatch** | Don't put a security expert on a marketing question unless security is actually relevant. |
| **Generic labels** | "Engineer" tells you nothing. "Ex-Uber SRE who was on-call during a failed migration" tells you everything. |

## The Compose Prompt

When composing agents via `delegate_task`, the prompt should include:

```
Design N expert debating agents for this question: "[topic]"

For each agent, provide:

1. name — First and last name (makes them feel real)
2. background — One paragraph: career history, relevant experience, what they've seen
3. expertise — Specific domain knowledge they bring
4. analytical_approach — How they reason about problems (first principles, risk-weighted, case-study driven, etc.)
5. bias — What experience or role makes them see this topic a particular way
6. confidence_calibration — How confident they are in their domain (e.g., "0.7 on infra, 0.3 on product")

Design them to create productive friction. Each agent should disagree with at least one other agent on at least one major point. The disagreement should be grounded in real experience, not personality.

Return as JSON array.
```
