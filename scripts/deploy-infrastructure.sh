#!/bin/bash
# Deploy the agile-agent-team infrastructure to Kubernetes.
# Usage: ./scripts/deploy-infrastructure.sh [--namespace <ns>]
set -euo pipefail

NAMESPACE="${NAMESPACE:-agile-agents}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Allow namespace override via flag
while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace) NAMESPACE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

echo "==> Deploying to namespace: ${NAMESPACE}"

# 1. Ensure namespace exists
kubectl get namespace "${NAMESPACE}" &>/dev/null \
  || kubectl create namespace "${NAMESPACE}"

# 2. Ensure DB credentials secret exists (prompt if missing)
if ! kubectl get secret db-credentials -n "${NAMESPACE}" &>/dev/null; then
  echo "==> Creating db-credentials secret"
  read -rsp "Enter PostgreSQL password: " DB_PASS
  echo
  kubectl create secret generic db-credentials \
    --from-literal=username=postgres \
    --from-literal=password="${DB_PASS}" \
    -n "${NAMESPACE}"
fi

# 3. Apply manifests
echo "==> Applying services"
kubectl apply -f "${REPO_ROOT}/infrastructure/k8s/services.yaml"

echo "==> Applying deployments"
kubectl apply -f "${REPO_ROOT}/infrastructure/k8s/deployment.yaml"

# 4. Wait for all pods to be ready (5 minute timeout)
echo "==> Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod --all -n "${NAMESPACE}" --timeout=300s

echo "==> Done. Pod status:"
kubectl get pods -n "${NAMESPACE}"
