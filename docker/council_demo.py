#!/usr/bin/env python3
"""
Hermes Council — Standalone Demo Runner

Self-contained script for the Docker demo. Makes direct API calls to the
configured LLM provider using the same prompts as the Hermes Council
orchestrator. No Hermes install needed — just the openai library.

Usage:
  PROVIDER_API_KEY=sk-... python3 council_demo.py
"""

import json, os, threading, time, sys
from openai import OpenAI

QUESTION = os.environ.get("COUNCIL_QUESTION", "Which has more power, love or fear?")
AGENT_COUNT = int(os.environ.get("COUNCIL_AGENTS", "5"))
API_KEY = os.environ.get("PROVIDER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = os.environ.get("API_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.environ.get("API_MODEL", "deepseek-v4-flash")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def strip_and_parse_json(text: str):
    """Strip markdown fences and parse JSON, with lenient handling for LLM output."""
    text = text.strip()
    # Remove code fences
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p and (p[0] in ("[", "{")):
                text = p
                break
    
    # Try parsing with strict=False
    import json as _json
    try:
        return _json.loads(text)
    except _json.JSONDecodeError:
        pass
    
    # Find outermost array/object brackets and extract
    for bracket_pair in [("[", "]"), ("{", "}")]:
        open_b, close_b = bracket_pair
        if open_b in text and close_b in text:
            depth = 0
            start = -1
            for i, c in enumerate(text):
                if c == open_b:
                    if depth == 0:
                        start = i
                    depth += 1
                elif c == close_b:
                    depth -= 1
                    if depth == 0 and start >= 0:
                        candidate = text[start:i+1]
                        try:
                            return _json.loads(candidate)
                        except _json.JSONDecodeError:
                            # Try to fix unescaped newlines in strings
                            fixed = candidate.replace('\n', '\\n').replace('\r', '\\r')
                            fixed = fixed.replace('\\n', '\\\\n') if '\\\\n' not in fixed else fixed
                            try:
                                return _json.loads(fixed)
                            except:
                                # Last resort: try the strict=False parser
                                from json import loads as json_loads_strict
                                try:
                                    return json_loads_strict(candidate)
                                except:
                                    pass
        raise _json.JSONDecodeError("Could not parse JSON output", text, 0)


def call_llm(system_prompt, user_prompt, timeout=90, max_tokens=4000):
    """Make an LLM API call and return the response text."""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return json.dumps({"error": str(e)})


def phase_compose() -> list:
    """Generate the agent roster."""
    print("── PHASE 1: COMPOSE ──")
    prompt = (
        f'Design {AGENT_COUNT} expert debating agents for the question: "{QUESTION}"\n\n'
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
    result = call_llm("You are an expert at designing debate panels.", prompt, timeout=180, max_tokens=8000)
    
    try:
        agents = strip_and_parse_json(result)
        print(f"  Composed {len(agents)} agents:\n")
        for a in agents:
            print(f"    {a['name']} — {a['expertise'][:70]}...")
            print(f"    {a['analytical_approach'][:80]}...")
            print()
        return agents
    except json.JSONDecodeError as e:
        print(f"  PARSE ERROR: {e}")
        print(f"  Raw: {result[:500]}")
        sys.exit(1)


def phase_position(agents: list) -> dict:
    """Each agent forms an independent initial position."""
    print("── PHASE 2: POSITIONS ──")
    results = {}
    threads = []
    lock = threading.Lock()
    
    def run(a):
        prompt = (
            f"You are {a['name']}.\n\n"
            f"BACKGROUND: {a['background']}\n"
            f"EXPERTISE: {a['expertise']}\n"
            f"APPROACH: {a['analytical_approach']}\n"
            f"BIAS: {a['bias']}\n\n"
            f"Question: {QUESTION}\n\n"
            f"Form your initial position on this question. Be specific and grounded in "
            f"your experience. Return JSON only: "
            f'{{"position": "...", "reasoning": ["...",], "concerns": ["..."], '
            f'"confidence": 0.0-1.0, '
            f'"evidence_needed": "Single piece of evidence that would change your mind"}}'
        )
        result = call_llm(
            f"You are {a['name']}, a debate panelist with the expertise and bias described below.",
            prompt
        )
        
        with lock:
            results[a["name"]] = result
            try:
                data = strip_and_parse_json(result)
                print(f"\n  === {a['name']} === (confidence: {data.get('confidence', '?')})")
                print(f"  Position: {data.get('position', 'N/A')[:200]}")
                print(f"  Would change mind if: {data.get('evidence_needed', 'N/A')}")
            except:
                print(f"\n  === {a['name']} === (raw)")
                print(f"  {result[:300]}")
    
    for a in agents:
        t = threading.Thread(target=run, args=(a,))
        threads.append(t)
        t.start()
        time.sleep(0.5)
    
    for t in threads:
        t.join()
    
    return results


def phase_cross(agents: list, positions: dict):
    """Cross-examination — each agent reads all others and responds."""
    print("\n\n── PHASE 3: CROSS-EXAMINATION ──")
    threads = []
    lock = threading.Lock()
    
    def run(a):
        # Build other agents' positions summary
        others = ""
        for a2 in agents:
            if a2["name"] == a["name"]:
                continue
            pos_raw = positions.get(a2["name"], "{}")
            try:
                pos = json.loads(pos_raw)
                others += f"\n--- {a2['name']} ---\n"
                others += f"Position: {pos.get('position', 'N/A')}\n"
                for r in pos.get("reasoning", []):
                    others += f"  - {r}\n"
                others += f"Confidence: {pos.get('confidence', 'N/A')}\n"
                others += f"Would change mind: {pos.get('evidence_needed', 'N/A')}\n"
            except:
                others += f"\n--- {a2['name']} --- (unparseable)\n"
        
        prompt = (
            f"You are {a['name']}.\n\n"
            f"BACKGROUND: {a['background']}\n"
            f"EXPERTISE: {a['expertise']}\n"
            f"APPROACH: {a['analytical_approach']}\n"
            f"BIAS: {a['bias']}\n\n"
            f"Question: {QUESTION}\n\n"
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
        result = call_llm(
            f"You are {a['name']}, a debate panelist. You have read the other panelists' positions and now respond.",
            prompt,
            timeout=120,
        )
        
        with lock:
            try:
                data = strip_and_parse_json(result)
                print(f"\n  === {a['name']} === (confidence: {data.get('updated_confidence', '?')})")
                print(f"  Revised: {data.get('revised_position', 'N/A')[:200]}")
                if data.get("conceded_to"):
                    for c in data["conceded_to"]:
                        print(f"  → Conceded to {c.get('agent', '?')}: {c.get('point', '')[:100]}")
                if data.get("disagrees_with"):
                    for d in data["disagrees_with"]:
                        print(f"  → Still disagrees with {d.get('agent', '?')}: {d.get('point', '')[:100]}")
                if data.get("new_insights"):
                    for ins in data["new_insights"]:
                        print(f"  → New insight: {ins[:120]}")
            except:
                print(f"\n  === {a['name']} === (raw)")
                print(f"  {result[:400]}")
    
    for a in agents:
        t = threading.Thread(target=run, args=(a,))
        threads.append(t)
        t.start()
        time.sleep(0.5)
    
    for t in threads:
        t.join()


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════╗")
    print("║         Hermes Council — Demo Run               ║")
    print("╠══════════════════════════════════════════════════╣")
    print(f"║  Question: {QUESTION}")
    print(f"║  Agents: {AGENT_COUNT}  •  Model: {MODEL}")
    print("╚══════════════════════════════════════════════════╝")
    print()
    
    agents = phase_compose()
    if not agents:
        sys.exit(1)
    
    positions = phase_position(agents)
    
    cross = phase_cross(agents, positions)
    
    print("\n\n── DEBATE COMPLETE ──")
    print("Full outputs saved to debate_output.json")
    
    # Save full output
    output = {
        "question": QUESTION,
        "agents": agents,
        "positions": positions,
        "cross_examination": {a["name"]: positions.get(a["name"], "{}") for a in agents},
    }
    # Try to get cross outputs too
    import glob
    cross_files = glob.glob("/tmp/hermes-council/cross/*.json")
    if cross_files:
        cross_data = {}
        for cf in cross_files:
            with open(cf) as f:
                name = cf.split("/")[-1].replace(".json", "")
                cross_data[name] = f.read()
        output["cross_examination"] = cross_data
    
    with open("debate_output.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
