# Council Composition — Research-Backed Best Practices

This document synthesizes findings from behavioral economics, organizational psychology, collective intelligence research, group dynamics, neuroscience of conflict, and cognitive science of reasoning to define what makes an effective advisory council.

## The Core Finding

> **Diversity of initial position matters more than expertise per member.** A group of four people who approach a problem from four distinct angles, none of them individually correct, will converge on a better answer than a group of four people two of whom already know the right answer but think about it the same way.

## 1. Size: 4–7, with 5 as the sweet spot

From the Nesta collective intelligence review (Berditchevskaia & Bertoncin) and Karadzhov et al. (2024, arXiv):

- **Below 3**: Insufficient idea pool diversity to outperform the average individual
- **3–5**: Performance gain increases monotonically with size (Karadzhov confirmed this with 500 Wason task dialogues, p = 0.03)
- **5–7**: Optimal band for discussion quality
- **Above 7**: Coordination costs begin to eat into deliberation quality

The tradeoff: enough bodies to guarantee perspective diversity, few enough that everyone speaks and nobody hides.

**Council default: 5 agents.** Quick mode can drop to 3 (the hard minimum). Deep mode can rise to 7.

## 2. Diversity of Perspective > Diversity of Expertise

This is the most striking finding across the literature. Karadzhov et al. (2024) tested whether a group's performance gain came from having a **correct answer** in the room vs having **diverse initial positions**.

- Diversity was the dominant predictor (p = 0.001)
- Presence of a correct initial answer was NOT significant (p = 0.079)
- Adding diversity to a model already controlling for group size significantly improved prediction (p = 0.0006)
- Adding group size to a model that already had diversity did NOT improve prediction (p = 0.81)

**Mechanism:** Distinct initial positions force genuine reasoning — the group has to argue toward a synthesis rather than recognizing shared agreement and stopping.

**Implementation:** When composing agents, prioritize divergent positions over parallel expertise. Two agents with the same background but opposite conclusions are more valuable than two agents with different backgrounds who agree.

## 3. The Inverted-U of Cognitive Diversity

From organizational psychology (ScienceDirect, 2025):

- **Too little diversity** → groupthink
- **Too much diversity** → communication breakdown, coordination failure, personal conflict
- **Sweet spot** → heterogeneity on cognitive style and initial priors, WITH enough shared language or overlapping domain knowledge to make disagreement legible

**Implementation:** All agents should share enough domain vocabulary to argue productively, even when they disagree on conclusions. Don't put a quantum physicist and a marketing director on the same infrastructure debate unless there's a clear reason.

## 4. Adversarial Collaboration (Kahneman)

The goal is not to WIN the debate but to produce an outcome neither starting position could have produced alone.

**Requirements:**
- Participants must accept the possibility of being wrong
- The task must be structured around reconciling contradictions, not scoring points
- A third-party integrator or facilitator holds the synthesis framing

**Implementation:** The council's cross-examination round explicitly asks agents to identify what they CONCEDE, not just what they disagree with. The synthesis is produced by a neutral facilitator (the main agent), not by any debating agent.

## 5. The Mechanism is "Probing for Reasoning"

Karadzhov et al. identified the specific conversational mechanism:

- **Probing for reasoning** had the strongest correlation with performance gain (Pearson R = 0.41, PCR coefficient 0.83 — highest of all measured factors)
- **Probing for solutions** was weaker
- **Moderation** (keeping order) had no effect

This maps to Mercier & Sperber's argumentative theory of reasoning — reasoning evolved to argue, not to find truth alone. When a group probes each other for WHY someone holds a position, it forces the articulation of logic that otherwise stays implicit.

**Implementation:** The cross-examination prompt explicitly prioritizes probing for reasoning over proposing solutions. Agents are instructed to ask "why do you believe X?" and "what evidence supports that?" rather than just stating their counter-position.

## 6. Structural Techniques

### Premortem
Start with: "The decision failed. Why?" Have agents write their failure scenarios independently before any position formation. This surfaces hidden assumptions and risks early.

### Silent Independent Preference First
Each agent forms their initial position WITHOUT seeing others' positions. This prevents anchoring on the first or loudest voice. (Already implemented in the pipeline — Position Round is independent.)

### Compact Delphi
After initial positions are formed, share the distribution of confidence scores. The dispersion chart tells you where real disagreement lives. Focus debate time on high-dispersion items.

### Light Red Team
Assign 1–2 agents the explicit role of stress-testing the leading plan. Specific failure modes, missing evidence, fragile assumptions. This is a scheduled obligation, not an adversarial posture.

### The Single Question
> "Name the single piece of evidence that would change your mind."

This makes everyone's decision threshold explicit. Already included in the position output schema as `evidence_needed`.

## 7. Good Friction vs Bad Friction

From the NeuroLeadership Institute's research on constructive conflict:

- **Moderate cognitive friction** → Level 1 threat state → optimal alertness without fight/flight
- **Task conflict** (disagreement about strategy, interpretation, evidence) → improves decision quality
- **Relationship conflict** (personal friction, ad hominem, identity threat) → destroys it

The composition needs people who can sustain the former without slipping into the latter.

**Implementation:** Agent personas should be designed to disagree on conclusions, not on each other's competence. No "this person is always wrong" framing. Each agent should have a defensible position grounded in real experience.

## 8. Practical Composition Rules

| Principle | Source |
|-----------|--------|
| 4–7 people, 5 is the sweet spot | Nesta, Karadzhov et al. |
| Diversity of initial position matters more than expertise per member | Karadzhov et al. (2024) |
| At least one member should approach the problem from a fundamentally different cognitive frame | Inverted-U research |
| At least one member should be structurally skeptical (red team role) | Decision Lab, Kahneman |
| Avoid selecting solely from the same social/professional cohort | Nesta (CIA pre-9/11 case study) |
| The convener should not be the most senior person, or must actively protect against anchoring | Nesta, Decision Lab |
| Rotate membership — tenure breeds overconfidence and inflexibility | Nesta |
| Train for Actively Open-Minded Thinking (AOMT) and probabilistic reasoning — these are learnable | Nesta |

## Sources

- Berditchevskaia & Bertoncin — Nesta Collective Intelligence Review
- Karadzhov et al. (2024) — arXiv: large-scale Wason task dialogue study (500 dialogues)
- ScienceDirect (2025) — Cognitive diversity inverted-U effect on team creativity
- Kahneman, Sibony & Sunstein — *Noise: A Flaw in Human Judgment*
- Mercier & Sperber — *The Enigma of Reason* (argumentative theory of reasoning)
- Holloway (2025) — Ohio State review of adversarial collaboration framework
- Stasser & Titus — Hidden profile paradigm (unshared information dynamics)
- Edmondson — Psychological safety and team learning
- NeuroLeadership Institute — Constructive conflict and threat response
