#!/usr/bin/env python3
"""
Council Orchestration Script — Hermes Council Debate Lifecycle Manager

Usage (via delegate_task or directly):
  python3 scripts/orchestrate.py compose "Should we migrate to Postgres?" --agents 4
  python3 scripts/orchestrate.py round --phase position --agents "agent1.json,agent2.json"

This script is optional. The SKILL.md workflow works without it using
delegate_task calls directly. The script exists for:
- Standardized JSON output parsing
- Consistent persona formatting across rounds
- Optional audit trail (save all round outputs to disk)

Orchestration follows the 5-phase pipeline:
  Compose → Position → Cross-examine → Converge → Synthesize

When invoked without arguments, reads from a state file at:
  /tmp/hermes-council-state.json
"""

import json, sys, os

STATE_FILE = "/tmp/hermes-council-state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"topic": "", "agents": [], "rounds": {}}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: orchestrate.py <compose|round|synthesize|status> [args]")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "compose":
        topic = sys.argv[2] if len(sys.argv) > 2 else "unknown"
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 4
        state = load_state()
        state["topic"] = topic
        state["agent_count"] = count
        save_state(state)
        print(json.dumps({"phase": "compose", "topic": topic, "agents_needed": count}))
    
    elif action == "status":
        state = load_state()
        print(json.dumps(state, indent=2))
    
    elif action == "reset":
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        print("State reset.")
    
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
