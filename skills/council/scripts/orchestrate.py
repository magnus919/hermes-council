#!/usr/bin/env python3
"""
Council Orchestrator — runs the full debate pipeline using Hermes oneshot (-z) agents.

Each agent runs as a fully independent Hermes process, avoiding the stale
CLI_CONFIG issue that blocks delegate_task. Each process loads fresh config.

Pipeline:
  1. compose  — generate agent roster
  2. position — each agent forms initial position (parallel, file-based coordination)
  3. cross    — each agent reads all positions and responds (parallel)
  4. converge — each agent identifies consensus/red-lines (parallel, optional)
  5. synth    — main agent reads all outputs, produces final analysis

Usage:
  python3 orchestrate.py compose "topic" [N agents]
  python3 orchestrate.py position <agents.json> <topic>
  python3 orchestrate.py cross <agents.json> <positions_dir> <topic>
  python3 orchestrate.py converge <agents.json> <cross_dir> <topic>
"""

import json, os, subprocess, sys, time, glob, threading
from pathlib import Path

HERMES = str(Path.home() / ".local/bin" / ".hermes-real")
ENV_FILE = str(Path.home() / ".hermes" / ".env")
STATE_DIR = "/tmp/hermes-council"

def _source_env():
    """Load .env into process environment."""
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

def _spawn_agent(prompt: str, timeout: int = 90) -> str:
    """Spawn a Hermes oneshot agent and return its output."""
    _source_env()
    cmd = [HERMES, "-z", prompt, "--provider", "deepseek", "-m", "deepseek-v4-flash"]
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


def phase_compose(topic: str, n_agents: int = 4):
    """Phase 1: Generate expert agent roster."""
    prompt = (
        f'Design {n_agents} expert debating agents for the question: "{topic}"\\n\\n'
        f"For each agent provide: name (first and last), background paragraph, "
        f"expertise, analytical_approach, bias, confidence_calibration (0.0-1.0).\\n\\n"
        f"Design them to create productive friction — real disagreement grounded "
        f"in real experience, not caricatures.\\n\\n"
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
        print(f"COMPOSED {len(agents)} agents:")
        for a in agents:
            print(f"  {a['name']} ({a['expertise'][:50]}...) [{a.get('confidence_calibration','?')}]")
    except json.JSONDecodeError as e:
        print(f"PARSE ERROR: {e}")
        print(f"RAW OUTPUT:\\n{result[:500]}")
        return None
    return agents


def phase_position(topic: str):
    """Phase 2: Each agent forms initial position."""
    with open(f"{STATE_DIR}/agents.json") as f:
        agents = json.load(f)
    
    threads = []
    for agent in agents:
        prompt = (
            f"You are {agent['name']}.\\n\\n"
            f"BACKGROUND: {agent['background']}\\n"
            f"EXPERTISE: {agent['expertise']}\\n"
            f"APPROACH: {agent['analytical_approach']}\\n"
            f"BIAS: {agent['bias']}\\n\\n"
            f"Question: {topic}\\n\\n"
            f"Form your initial position on this question. Return JSON only: "
            f'{{"position": "...", "reasoning": ["...",], "concerns": ["..."], '
            f'"confidence": 0.0-1.0, "evidence_needed": ["..."]}}'
        )
        def run(a):
            result = _spawn_agent(prompt, timeout=120)
            result = _strip_fences(result)
            _save_round("position", a["name"], result)
            try:
                data = json.loads(result)
                print(f"  {a['name']}: confidence={data.get('confidence','?')}")
            except:
                print(f"  {a['name']}: PARSE ERROR — {result[:100]}")
        
        t = threading.Thread(target=run, args=(agent,))
        threads.append(t)
        t.start()
        time.sleep(1)  # stagger to avoid thundering herd
    
    for t in threads:
        t.join()
    
    positions = _load_round("position")
    print(f"\\nPOSITIONS COMPLETE: {len(positions)} agents responded")
    return positions


def phase_cross(topic: str):
    """Phase 3: Cross-examination — each agent reads all others' positions."""
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
            f"You are {agent['name']}.\\n\\n"
            f"BACKGROUND: {agent['background']}\\n"
            f"EXPERTISE: {agent['expertise']}\\n"
            f"APPROACH: {agent['analytical_approach']}\\n"
            f"BIAS: {agent['bias']}\\n\\n"
            f"Question: {topic}\\n\\n"
            f"Here are the positions of the other council members:\\n{others}\\n\\n"
            f"Respond to their positions. What do you concede? What do you disagree with? "
            f"Has your position changed?\\n\\n"
            f"Return JSON only: "
            f'{{"revised_position": "...", "conceded_to": [{{"agent":"name","point":"..."}}], '
            f'"disagrees_with": [{{"agent":"name","point":"..."}}], '
            f'"new_insights": ["..."], "updated_confidence": 0.0-1.0}}'
        )
        def run(a):
            result = _spawn_agent(prompt, timeout=150)
            result = _strip_fences(result)
            _save_round("cross", a["name"], result)
            try:
                data = json.loads(result)
                print(f"  {a['name']}: confidence={data.get('updated_confidence','?')}")
            except:
                print(f"  {a['name']}: PARSE ERROR — {result[:150]}")
        
        t = threading.Thread(target=run, args=(agent,))
        threads.append(t)
        t.start()
        time.sleep(1)
    
    for t in threads:
        t.join()
    
    cross = _load_round("cross")
    print(f"\\nCROSS-EXAMINATION COMPLETE: {len(cross)} agents responded")
    return cross


if __name__ == "__main__":
    _source_env()
    topic = "Should we use WebSockets or Server-Sent Events for real-time notifications in a web application?"
    
    if len(sys.argv) > 1 and sys.argv[1] == "compose":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
        phase_compose(topic, n)
    elif len(sys.argv) > 1 and sys.argv[1] == "position":
        phase_position(topic)
    elif len(sys.argv) > 1 and sys.argv[1] == "cross":
        phase_cross(topic)
    elif len(sys.argv) > 1 and sys.argv[1] == "full":
        print("=== PHASE 1: COMPOSE ===")
        agents = phase_compose(topic, 4)
        if not agents:
            sys.exit(1)
        print("\\n=== PHASE 2: POSITION ===")
        positions = phase_position(topic)
        print("\\n=== PHASE 3: CROSS-EXAMINATION ===")
        cross = phase_cross(topic)
        print("\\n=== ALL PHASES COMPLETE ===")
        print(f"State saved in {STATE_DIR}/")
    else:
        print(f"Usage: {sys.argv[0]} [compose|position|cross|full]")
