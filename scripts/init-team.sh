#!/bin/bash
# Initialize the team: verify agent profiles, load config, and seed the DB schema.
# Usage: ./scripts/init-team.sh [--config <path>] [--db-url <url>]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG="${CONFIG:-${REPO_ROOT}/config.yaml}"
DB_URL="${DB_URL:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --db-url) DB_URL="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

echo "==> Config: ${CONFIG}"

# 1. Activate virtualenv if present
if [[ -f "${REPO_ROOT}/.venv/bin/activate" ]]; then
  source "${REPO_ROOT}/.venv/bin/activate"
elif [[ -f "${REPO_ROOT}/venv/bin/activate" ]]; then
  source "${REPO_ROOT}/venv/bin/activate"
fi

# 2. Verify all 11 agent profiles exist
echo "==> Checking agent profiles..."
PROFILES_DIR="${REPO_ROOT}/team_config/02_individuals"
PROFILE_COUNT=$(find "${PROFILES_DIR}" -name "*.md" | wc -l | tr -d ' ')
if [[ "${PROFILE_COUNT}" -ne 11 ]]; then
  echo "ERROR: Expected 11 agent profiles in ${PROFILES_DIR}, found ${PROFILE_COUNT}" >&2
  exit 1
fi
echo "    Found ${PROFILE_COUNT} profiles: OK"

# 3. Verify required base/archetype files exist
echo "==> Checking base and archetype configs..."
for f in \
  "team_config/00_base/base_agent.md" \
  "team_config/01_role_archetypes/developer.md" \
  "team_config/01_role_archetypes/tester.md" \
  "team_config/01_role_archetypes/leader.md"
do
  if [[ ! -f "${REPO_ROOT}/${f}" ]]; then
    echo "ERROR: Missing required file: ${f}" >&2
    exit 1
  fi
done
echo "    Base and archetype files: OK"

# 4. Initialize database schema
echo "==> Initializing database schema..."
if [[ -n "${DB_URL}" ]]; then
  python - <<PYEOF
import asyncio, sys
sys.path.insert(0, "${REPO_ROOT}")
from src.tools.shared_context import SharedContextDB

async def main():
    db = SharedContextDB("${DB_URL}")
    await db.initialize()
    print("    Database schema initialized: OK")

asyncio.run(main())
PYEOF
else
  echo "    No --db-url provided; skipping DB init (use mock:// for local dev)"
fi

# 5. Quick qualification smoke-test (mock mode)
echo "==> Running agent qualification smoke-test..."
MOCK_LLM=true python -m pytest "${REPO_ROOT}/tests/qualification/" -q --tb=short

echo ""
echo "==> Team initialization complete."
