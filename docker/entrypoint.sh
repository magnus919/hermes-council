#!/bin/bash
set -e

# Entrypoint for Hermes Council Docker container.
# All configuration via environment variables — no secrets baked into the image.

COUNCIL_QUESTION="${COUNCIL_QUESTION:-Which has more power, love or fear?}"
COUNCIL_AGENTS="${COUNCIL_AGENTS:-5}"
PROVIDER="${PROVIDER:-deepseek}"
MODEL="${MODEL:-deepseek-v4-flash}"

# Generate Hermes config at runtime
mkdir -p /root/.hermes
cat > /root/.hermes/config.yaml << ENDCONFIG
model:
  provider: ${PROVIDER}
  default: ${MODEL}

auxiliary:
  council:
    provider: ${PROVIDER}
    model: ${MODEL}

delegation:
  provider: ${PROVIDER}
  model: ${MODEL}
ENDCONFIG

# Generate .env from PROVIDER_API_KEY
if [ -n "${PROVIDER_API_KEY}" ]; then
    cat > /root/.hermes/.env << ENDENV
DEEPSEEK_API_KEY=${PROVIDER_API_KEY}
ENDENV
else
    echo "ERROR: PROVIDER_API_KEY environment variable is required."
    echo "Run with: docker run -e PROVIDER_API_KEY=sk-... hermes-council"
    exit 1
fi

# Smoke test
echo "=== Hermes smoke test ==="
hermes -z "Return OK" 2>/dev/null || {
    echo "ERROR: Hermes oneshot mode failed. Check PROVIDER_API_KEY."
    exit 1
}

echo ""
echo "══════════════════════════════════════════════════"
echo "  Hermes Council — Demo Run"
echo "  Question: ${COUNCIL_QUESTION}"
echo "  Agents: ${COUNCIL_AGENTS}"
echo "  Provider: ${PROVIDER} / ${MODEL}"
echo "══════════════════════════════════════════════════"
echo ""

export COUNCIL_QUESTION
export COUNCIL_AGENTS
exec python3 /root/.hermes/skills/thinking/council/scripts/orchestrate.py full
