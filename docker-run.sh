#!/bin/bash
# Run the Hermes Council demo in Docker.
#
# Usage:
#   PROVIDER_API_KEY=sk-... ./docker-run.sh
#   PROVIDER_API_KEY=sk-... ./docker-run.sh "Your question here"
#
# Environment variables:
#   PROVIDER_API_KEY  — Required. API key for the LLM provider.
#   API_MODEL         — Model name (default: deepseek-v4-flash)
#   API_BASE_URL      — API base URL (default: https://api.deepseek.com/v1)
#   COUNCIL_AGENTS    — Number of agents (default: 5)

set -e

if [ -z "${PROVIDER_API_KEY}" ]; then
    echo "ERROR: PROVIDER_API_KEY is required."
    echo "Usage: PROVIDER_API_KEY=sk-... $0 [\"question\"]"
    exit 1
fi

QUESTION="${1:-Which has more power, love or fear?}"

cd "$(dirname "$0")"

echo "Building Docker image..."
docker build -t hermes-council . 2>&1 | tail -3

echo ""
echo "Running council on: ${QUESTION}"
echo ""

docker run --rm \
    -e PROVIDER_API_KEY \
    -e API_MODEL="${API_MODEL:-deepseek-v4-flash}" \
    -e API_BASE_URL="${API_BASE_URL:-https://api.deepseek.com/v1}" \
    -e COUNCIL_AGENTS="${COUNCIL_AGENTS:-5}" \
    -e COUNCIL_QUESTION="${QUESTION}" \
    hermes-council
