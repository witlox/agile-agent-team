#!/bin/bash
# Run the full qualification test suite against all agents.
# Usage: ./scripts/qualify-all-agents.sh [--vllm-endpoint <url>] [--mock]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VLLM_ENDPOINT=""
MOCK=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vllm-endpoint) VLLM_ENDPOINT="$2"; shift 2 ;;
    --mock) MOCK=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# Activate virtualenv if present
if [[ -f "${REPO_ROOT}/.venv/bin/activate" ]]; then
  source "${REPO_ROOT}/.venv/bin/activate"
elif [[ -f "${REPO_ROOT}/venv/bin/activate" ]]; then
  source "${REPO_ROOT}/venv/bin/activate"
fi

# Determine LLM mode
if [[ "${MOCK}" == true ]] || [[ -z "${VLLM_ENDPOINT}" ]]; then
  echo "==> Running in MOCK mode (no live vLLM required)"
  export MOCK_LLM=true
else
  echo "==> Running against live vLLM endpoint: ${VLLM_ENDPOINT}"
  export VLLM_ENDPOINT="${VLLM_ENDPOINT}"
  unset MOCK_LLM
fi

echo "==> Qualification tests"
python -m pytest "${REPO_ROOT}/tests/qualification/" -v --tb=short

echo ""
echo "==> Integration tests"
python -m pytest "${REPO_ROOT}/tests/integration/" -v --tb=short

echo ""
echo "==> Unit tests"
python -m pytest "${REPO_ROOT}/tests/unit/" -v --tb=short

echo ""
echo "==> All qualification checks passed."
