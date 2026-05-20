#!/usr/bin/env python3
"""
Council Orchestrator — runs the full debate pipeline using Hermes oneshot (-z) agents.

Each agent runs as a fully independent Hermes process, avoiding the stale
CLI_CONFIG issue that blocks delegate_task. Each process loads fresh config.

Pipeline (mode-dependent):

  quick:   compose → premortem → position → cross_a
  medium:  compose → premortem → position → cross_a → cross_b
  deep:    compose → premortem → position → cross_a → cross_b → assumption_map

  0. premortem  — each agent writes a failure history (bypasses positional commitment)
  1. position   — each agent forms initial position (parallel, file-based coordination)
  2a. cross_a   — each agent probes reasoning of all others (the money round)
  2b. cross_b   — each agent reflects, concedes, identifies remaining gaps
  3. assumption — each agent maps assumptions underlying opposing positions
  4. synth      — main agent reads all outputs, produces decision landscape

Usage:
  python3 orchestrate.py compose "topic" [N agents]
  python3 orchestrate.py position <agents.json> <topic>
  python3 orchestrate.py cross-a <agents.json> <positions_dir> <topic>
  python3 orchestrate.py cross-b <agents.json> <cross_a_dir> <topic>
  python3 orchestrate.py assumption <agents.json> <cross_b_dir> <topic>
  python3 orchestrate.py full --mode quick|medium|deep --question "..." [--agents N]
"""

import json, os, subprocess, sys, time, glob, threading
from pathlib import Path
HERMES = str(Path.home() / ".local/bin" / ".hermes-real")
ENV_FILE = str(Path.home() / ".hermes" / ".env")
STATE_DIR = "/tmp/hermes-council"

# Provider/model defaults — resolve via auxiliary.council > delegation > main config.
def _load_provider_config() -> dict:
    """Load provider config: auxiliary.council > delegation > main config > safe defaults."""
    try:
        import yaml
        config_path = str(Path.home() / ".hermes" / "config.yaml")
        if os.path.exists(config_path):
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}

            # 1. Check auxiliary.council first — designed for this purpose
            council_aux = cfg.get("auxiliary", {}).get("council", {})
            if council_aux.get("provider"):
                return {
                    "provider": council_aux["provider"],
                    "model": council_aux.get("model", ""),
                    "base_url": council_aux.get("base_url", ""),
                    "api_key": council_aux.get("api_key", ""),
                }

            # 2. Check delegation section (standard Hermes sub-agent config)
            delegation = cfg.get("delegation", {})
            if delegation.get("provider") or delegation.get("base_url"):
                return {
                    "provider": delegation.get("provider", "deepseek"),
                    "model": delegation.get("model", "deepseek-v4-flash"),
                    "base_url": delegation.get("base_url", ""),
                    "api_key": delegation.get("api_key", ""),
                }

            # 3. Fall back to main model config
            model_cfg = cfg.get("model", {})
            return {
                "provider": model_cfg.get("provider", "deepseek"),
                "model": model_cfg.get("default", "deepseek-v4-flash"),
                "base_url": model_cfg.get("base_url", ""),
                "api_key": "",
            }
    except Exception:
        pass

    # Ultimate fallback — should only trigger if config is unreadable
    return {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "base_url": "",
        "api_key": "",
    }


def _source_env():
    """Load .env into process environment for child Hermes processes."""
    if not os.path.exists(ENV_FILE):
        return
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _spawn_agent(prompt: str, timeout: int = 90, provider_override: dict = None) -> str:
    """Spawn a Hermes oneshot agent and return its output."""
    _source_env()
    prov = provider_override or _load_provider_config()

    cmd = [HERMES, "-z", prompt]
    if prov.get("provider"):
        cmd += ["--provider", prov["provider"]]
    if prov.get("model"):
        cmd += ["-m", prov["model"]]
    if prov.get("base_url"):
        os.environ["OPENAI_BASE_URL"] = prov["base_url"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "timeout", "message": f"Agent timed out after {timeout}s"})
    except Exception as e:
        return json.dumps({"error": "exception", "message": str(e)})


def _strip_fences(text: str) -> str:
    """Strip markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        # Find the first newline after the opening fence
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl:]
        # Remove closing fence
        if text.endswith("```"):
            text = text[:-3]
        elif "```" in text:
            text = text.rsplit("```", 1)[0]
    return text.strip()

def _save_round(round_name: str, agent_name: str, output: str):
    os.makedirs(f"{STATE_DIR}/{round_name}", exist_ok=True)
    safe_name = agent_name.lower().replace(" ", "-")
    path = f"{STATE_DIR}/{round_name}/{safe_name}.json"
    with open(path, "w") as f:
        f.write(output)

def _load_round(round_name: str) -> dict:
    """Load all outputs from a round. Returns {agent_name: parsed_json}."""
    results = {}
    pattern = f"{STATE_DIR}/{round_name}/*.json"
    for path in glob.glob(pattern):
        with open(path) as f:
            content = f.read().strip()
        try:
            data = json.loads(content)
            name = path.split("/")[-1].replace(".json", "").replace("-", " ").title()
            results[name] = data
        except json.JSONDecodeError:
            results[path] = content
    return results


def phase_compose(topic: str, n_agents: int = 5):
    """Phase 1: Generate expert agent roster."""
    prompt = (
        f'Design {n_agents} expert debating agents for the question: "{topic}"\n\n'
        f"CRITICAL DIRECTIVE: Prioritize diversity of INITIAL POSITION over diversity "
        f"of expertise. Research shows that a group with distinct approaches to a "
        f"problem outperforms a group with more expertise but shared framing.\n\n"
        f"For each agent provide: name (first and last), background paragraph, "
        f"expertise, analytical_approach, bias, confidence_calibration (0.0-1.0).\n\n"
        f"At least one agent should be structurally skeptical (light red team role). "
        f"At least one agent should approach the problem from a fundamentally different "
        f"cognitive frame. Every position should be defensible.\n\n"
        f"Return ONLY a raw JSON array. No markdown, no code fences, no explanation. "
        f"Start with [ and end with ]."
    )
    result = _spawn_agent(prompt, timeout=90)

    # Strip markdown code fences if present
    result = result.strip()
    if result.startswith("```"):
        result = result.split("\\n", 1)[1]
        result = result.rsplit("\\n", 1)[0] if "\\n" in result else result
        if result.endswith("```"):
            result = result[:-3]

    try:
        agents = json.loads(result)
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(f"{STATE_DIR}/agents.json", "w") as f:
            json.dump(agents, f, indent=2)
        print(f"COMPOSED {len(agents)} agents")
    except json.JSONDecodeError as e:
        print(f"PARSE ERROR: {e}")
        print(f"RAW OUTPUT:\\n{result[:500]}")
        return None
    return agents


def phase_premortem(topic: str):
    """Phase 0: Each agent independently writes a failure history.

    This runs BEFORE position formation to bypass positional commitment.
    Each agent imagines the decision was made and failed, then writes a
    plausible history of how that failure happened. The outputs are collected
    for the synthesis phase but NOT shared between agents — this prevents
    premortem framing from anchoring the debate.
    """
    with open(f"{STATE_DIR}/agents.json") as f:
        agents = json.load(f)

    threads = []
    for agent in agents:
        prompt = (
            f"You are {agent['name']}.\n\n"
            f"BACKGROUND: {agent['background']}\n"
            f"EXPERTISE: {agent['expertise']}\n"
            f"APPROACH: {agent['analytical_approach']}\n"
            f"BIAS: {agent['bias']}\n\n"
            f"The decision being debated is: {topic}\n\n"
            f"PRE-MORTEM EXERCISE: Imagine the decision was made and it FAILED — "
            f"completely, unambiguously. Write a brief history (3-5 paragraphs) of "
            f"how that failure happened. Be specific about the chain of events, "
            f"the assumptions that turned out wrong, and the signals that were missed.\n\n"
            f"Do NOT state your own position on the decision yet. This is about "
            f"mapping failure modes before anyone commits to a stance.\n\n"
            f"Return JSON only: "
            f'{{"premortem_scenario": "3-5 paragraph failure history...", '
            f'"failure_modes": ["specific failure mode 1", "mode 2", ...], '
            f'"missed_signals": ["signal 1", "signal 2", ...]}}'
        )
        def run(a):
            result = _spawn_agent(prompt, timeout=120)
            result = _strip_fences(result)
            _save_round("premortem", a["name"], result)

        t = threading.Thread(target=run, args=(agent,))
        threads.append(t)
        t.start()
        time.sleep(1)

    for t in threads:
        t.join()

    results = _load_round("premortem")
    print(f"PREMORTEM: {len(results)} agents")
    return results


def phase_position(topic: str):
    """Phase 1: Each agent forms initial position (unchanged from current)."""
    with open(f"{STATE_DIR}/agents.json") as f:
        agents = json.load(f)

    threads = []
    for agent in agents:
        prompt = (
            f"You are {agent['name']}.\n\n"
            f"BACKGROUND: {agent['background']}\n"
            f"EXPERTISE: {agent['expertise']}\n"
            f"APPROACH: {agent['analytical_approach']}\n"
            f"BIAS: {agent['bias']}\n\n"
            f"Question: {topic}\n\n"
            f"Form your initial position on this question. Be specific and grounded in your experience. "
            f"Return JSON only: "
            f'{{"position": "...", "reasoning": ["...",], "concerns": ["..."], '
            f'"confidence": 0.0-1.0, '
            f'"evidence_needed": "Single piece of evidence that would change your mind"}}'
        )
        def run(a):
            result = _spawn_agent(prompt, timeout=120)
            result = _strip_fences(result)
            _save_round("position", a["name"], result)

        t = threading.Thread(target=run, args=(agent,))
        threads.append(t)
        t.start()
        time.sleep(1)  # stagger to avoid thundering herd

    for t in threads:
        t.join()

    positions = _load_round("position")
    print(f"POSITIONS: {len(positions)} agents")
    return positions


def phase_cross_a(topic: str):
    """Phase 2a: Cross-examination — each agent probes reasoning of all others.

    This is the "money round." Research (Karadzhov et al. 2024) shows probing
    for reasoning (R = 0.41) is the single strongest predictor of group
    performance gain. Prioritize asking WHY over proposing solutions.
    """
    with open(f"{STATE_DIR}/agents.json") as f:
        agents = json.load(f)

    positions = _load_round("position")

    threads = []
    for agent in agents:
        others = ""
        for a2 in agents:
            if a2["name"] == agent["name"]:
                continue
            pos = positions.get(a2["name"].title(), {})
            if isinstance(pos, dict):
                others += f"\\n--- {a2['name']} ---\\n"
                others += f"Position: {pos.get('position', 'N/A')}\\n"
                for r in pos.get("reasoning", []):
                    others += f"  - {r}\\n"

        prompt = (
            f"You are {agent['name']}.\n\n"
            f"BACKGROUND: {agent['background']}\n"
            f"EXPERTISE: {agent['expertise']}\n"
            f"APPROACH: {agent['analytical_approach']}\n"
            f"BIAS: {agent['bias']}\n\n"
            f"Question: {topic}\n\n"
            f"Here are the positions of the other council members:\n{others}\n\n"
            f"Research shows that PROBING FOR REASONING — asking 'why do you believe X?' "
            f"and 'what evidence supports that?' — is the single most effective mechanism "
            f"for producing better group decisions. Prioritize probing for reasoning over "
            f"proposing solutions.\n\n"
            f"For each point of disagreement: ask yourself why the other agent holds that "
            f"position before dismissing it. What can you concede? Where does disagreement "
            f"remain genuinely unresolved?\n\n"
            f"Return JSON only: "
            f'{{"revised_position": "...", '
            f'"conceded_to": [{{"agent":"name","point":"...","what_changed_my_mind":"..."}}], '
            f'"probes_for_reasoning": [{{"agent":"name","question":"...","response":"..."}}], '
            f'"disagrees_with": [{{"agent":"name","point":"..."}}], '
            f'"new_insights": ["..."], "updated_confidence": 0.0-1.0}}'
        )
        def run(a):
            result = _spawn_agent(prompt, timeout=150)
            result = _strip_fences(result)
            _save_round("cross_a", a["name"], result)

        t = threading.Thread(target=run, args=(agent,))
        threads.append(t)
        t.start()
        time.sleep(1)

    for t in threads:
        t.join()

    results = _load_round("cross_a")
    print(f"CROSS_A: {len(results)} agents")
    return results


def phase_cross_b(topic: str):
    """Phase 2b: Reflection round — each agent reflects on what they heard.

    Each agent reads all cross_a outputs and produces an update: what
    concessions they make, where their position has shifted, and what
    evidence would close remaining gaps.
    """
    with open(f"{STATE_DIR}/agents.json") as f:
        agents = json.load(f)

    cross_a_results = _load_round("cross_a")

    threads = []
    for agent in agents:
        others = ""
        for a2 in agents:
            if a2["name"] == agent["name"]:
                continue
            ca = cross_a_results.get(a2["name"].title(), {})
            if isinstance(ca, dict):
                others += f"\\n--- {a2['name']} ---\\n"
                conceded = ca.get("conceded_to", [])
                if conceded:
                    for c in conceded:
                        others += f"  Conceded: {c.get('point', '')}\\n"
                probes = ca.get("probes_for_reasoning", [])
                if probes:
                    for p in probes:
                        others += f"  Asked: {p.get('question', '')}\\n"
                disagrees = ca.get("disagrees_with", [])
                if disagrees:
                    for d in disagrees:
                        others += f"  Disagrees: {d.get('point', '')}\\n"

        prompt = (
            f"You are {agent['name']}.\n\n"
            f"BACKGROUND: {agent['background']}\n"
            f"EXPERTISE: {agent['expertise']}\n"
            f"APPROACH: {agent['analytical_approach']}\n"
            f"BIAS: {agent['bias']}\n\n"
            f"Question: {topic}\n\n"
            f"The cross-examination round is complete. Here is what other agents "
            f"conceded, probed, and disagreed on:\n{others}\n\n"
            f"Now reflect: what did you hear that shifted your thinking? What "
            f"concessions can you make? Where does genuine disagreement remain?\n\n"
            f"Be specific about what evidence or reasoning would close each gap.\n\n"
            f"Return JSON only: "
            f'{{"reflection": "What you heard and how it affected your thinking", '
            f'"conceded": [{{"to_agent": "name", "on_point": "...", "why": "..."}}], '
            f'"remaining_disagreements": [{{"with_agent": "name", "what": "...", '
            f'"what_would_close_gap": "..."}}], '
            f'"updated_position": "Your stance after reflection", '
            f'"updated_confidence": 0.0-1.0}}'
        )
        def run(a):
            result = _spawn_agent(prompt, timeout=150)
            result = _strip_fences(result)
            _save_round("cross_b", a["name"], result)

        t = threading.Thread(target=run, args=(agent,))
        threads.append(t)
        t.start()
        time.sleep(1)

    for t in threads:
        t.join()

    results = _load_round("cross_b")
    print(f"CROSS_B: {len(results)} agents")
    return results


def phase_assumption_map(topic: str):
    """Phase 3: Assumption mapping — replaces convergence.

    Instead of forcing agents to agree, each agent identifies the assumptions
    underlying opposing positions and what would need to be true for each
    opposing position to be correct. Produces a divergence map, not consensus.
    """
    with open(f"{STATE_DIR}/agents.json") as f:
        agents = json.load(f)

    cross_results = _load_round("cross_b") or _load_round("cross_a")
    positions = _load_round("position")

    threads = []
    for agent in agents:
        others = ""
        for a2 in agents:
            if a2["name"] == agent["name"]:
                continue
            pos = positions.get(a2["name"].title(), {})
            cr = cross_results.get(a2["name"].title(), {})
            if isinstance(pos, dict):
                others += f"\\n--- {a2['name']} ---\\n"
                others += f"Position: {pos.get('position', 'N/A')}\\n"
                others += f"Final stance: {cr.get('updated_position', cr.get('revised_position', 'N/A'))}\\n"

        prompt = (
            f"You are {agent['name']}.\n\n"
            f"BACKGROUND: {agent['background']}\n"
            f"EXPERTISE: {agent['expertise']}\n"
            f"APPROACH: {agent['analytical_approach']}\n"
            f"BIAS: {agent['bias']}\n\n"
            f"Question: {topic}\n\n"
            f"Here are the final positions of the other council members after full debate:\n{others}\n\n"
            f"Do NOT try to converge on agreement. Instead, produce an ASSUMPTION MAP:\n\n"
            f"1. For each opposing position: what assumptions would need to be true for that "
            f"position to be the correct call?\n"
            f"2. What evidence is currently insufficient to resolve the disagreement?\n"
            f"3. What risk vectors does each position carry that the other positions don't?\n\n"
            f"The goal is to make every defensible position legible — not to find common ground.\n\n"
            f"Return JSON only: "
            f'{{"assumptions_for_opposing": [{{"position": "name of position", '
            f'"what_would_need_to_be_true": ["assumption 1", "assumption 2", ...], '
            f'"evidence_insufficient": "what we still don\'t know"}}], '
            f'"unique_risk_vectors": ["risk 1", "risk 2", ...], '
            f'"what_i_would_watch": "Single metric or signal I\'d track to know if I\'m wrong"}}'
        )
        def run(a):
            result = _spawn_agent(prompt, timeout=150)
            result = _strip_fences(result)
            _save_round("assumption_map", a["name"], result)

        t = threading.Thread(target=run, args=(agent,))
        threads.append(t)
        t.start()
        time.sleep(1)

    for t in threads:
        t.join()

    results = _load_round("assumption_map")
    print(f"ASSUMPTION MAP: {len(results)} agents")
    return results


if __name__ == "__main__":
    _source_env()

    # Support env var override for the question (for Docker/CI use)
    topic = os.environ.get("COUNCIL_QUESTION") or "Should we use WebSockets or Server-Sent Events for real-time notifications in a web application?"
    default_agents = int(os.environ.get("COUNCIL_AGENTS", "5"))
    mode = "medium"  # default mode

    # Parse flags from args
    extra_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for i, a in enumerate(sys.argv):
        if a == "--question" and i + 1 < len(sys.argv):
            topic = sys.argv[i + 1]
        elif a == "--agents" and i + 1 < len(sys.argv):
            default_agents = int(sys.argv[i + 1])
        elif a == "--mode" and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1]

    if len(sys.argv) > 1 and sys.argv[1] == "compose":
        n = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else default_agents
        phase_compose(topic, n)
    elif len(sys.argv) > 1 and sys.argv[1] == "premortem":
        phase_premortem(topic)
    elif len(sys.argv) > 1 and sys.argv[1] == "position":
        phase_position(topic)
    elif len(sys.argv) > 1 and sys.argv[1] == "cross-a":
        phase_cross_a(topic)
    elif len(sys.argv) > 1 and sys.argv[1] == "cross-b":
        phase_cross_b(topic)
    elif len(sys.argv) > 1 and sys.argv[1] == "assumption":
        phase_assumption_map(topic)
    elif len(sys.argv) > 1 and sys.argv[1] == "full":
        if mode not in ("quick", "medium", "deep"):
            print(f"Unknown mode: {mode}. Use quick, medium, or deep.")
            sys.exit(1)

        # Agent count scaling per mode
        if mode == "quick":
            default_agents = min(default_agents, 3)
        elif mode == "deep":
            default_agents = max(default_agents, 5)

        print(f"=== COUNCIL [{mode.upper()}] ===")
        print(f"Question: {topic}")
        print(f"Agents: {default_agents}")
        print(f"Phases: ", end="")

        phases = []
        if mode == "quick":
            phases = ["premortem", "position", "cross_a"]
        elif mode == "medium":
            phases = ["premortem", "position", "cross_a", "cross_b"]
        elif mode == "deep":
            phases = ["premortem", "position", "cross_a", "cross_b", "assumption_map"]
        print(" → ".join(phases))

        print("\n=== PHASE 0: COMPOSE ===")
        agents = phase_compose(topic, default_agents)
        if not agents:
            sys.exit(1)

        print("\n=== PHASE 0b: PREMORTEM ===")
        premortem = phase_premortem(topic)

        print("\n=== PHASE 1: POSITION ===")
        positions = phase_position(topic)

        print("\n=== PHASE 2a: CROSS-EXAMINATION (Probe Reasoning) ===")
        cross_a = phase_cross_a(topic)

        if mode in ("medium", "deep"):
            print("\n=== PHASE 2b: CROSS-EXAMINATION (Reflect & Update) ===")
            cross_b = phase_cross_b(topic)

        if mode == "deep":
            print("\n=== PHASE 3: ASSUMPTION MAPPING ===")
            assumption = phase_assumption_map(topic)

        print(f"\n=== ALL PHASES COMPLETE [{mode.upper()}] ===")
        print(f"State saved in {STATE_DIR}/")
    else:
        print(f"Usage: {sys.argv[0]} [compose|premortem|position|cross-a|cross-b|assumption|full]")
        print(f"  full: --mode quick|medium|deep --question '...' [--agents N]")
