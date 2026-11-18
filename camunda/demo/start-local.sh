#!/usr/bin/env bash
# Run the Sprint 2 rehearsal on a dedicated, loopback-only Camunda instance.
set -euo pipefail

repo="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo"
runtime="${DESD_CAMUNDA_HOME:-$HOME/Desktop/DESD/.sprint2-local-runtime/camunda}"
java_home="${DESD_JAVA_HOME:-$HOME/Desktop/DESD/.sprint2-local-runtime/java/Contents/Home}"
out="$repo/camunda/runtime/sprint2"
engine="http://127.0.0.1:18080"
python3 camunda/demo/prepare_inventory.py

if [[ ! -x "$runtime/camunda-zeebe-8.9.28/bin/camunda" || ! -x "$java_home/bin/java" ]]; then
  printf '%s\n' 'Camunda 8.9.28 or Java 21 is missing. Set DESD_CAMUNDA_HOME and DESD_JAVA_HOME.'
  exit 1
fi
for port in 18080 18090 17650 17651 17652 19600; do
  if lsof -nP -sTCP:LISTEN -iTCP:"$port" >/dev/null 2>&1; then
    printf 'Port %s is already in use. Close the existing demo window before restarting.\n' "$port"
    exit 1
  fi
done

pids=()
cleanup() {
  if (( ${#pids[@]} )); then
    kill "${pids[@]}" 2>/dev/null || true
    wait 2>/dev/null || true
  fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM

(
  cd "$runtime"
  export JAVA_HOME="$java_home"
  export JAVA_OPTS='-Xms256m -Xmx2g'
  exec ./camunda-zeebe-8.9.28/bin/camunda \
    --spring.config.additional-location=file:./configuration/application.yaml \
    --server.address=127.0.0.1 --server.port=18080 \
    --management.server.address=127.0.0.1 --management.server.port=19600 \
    --camunda.api.grpc.address=127.0.0.1 --camunda.api.grpc.port=17650 \
    --camunda.cluster.network.host=127.0.0.1 --camunda.cluster.network.advertised-host=127.0.0.1 \
    --camunda.cluster.network.command-api.port=17651 --camunda.cluster.network.internal-api.port=17652 \
    --camunda.mcp.enabled=false
) >"$out/engine.log" 2>&1 &
pids+=("$!")
printf '%s\n' 'Starting local Camunda. This can take about 20 seconds.'
ready=false
for ((attempt=0; attempt<60; attempt++)); do
  if curl -fsS --max-time 2 "$engine/v2/topology" >"$out/topology.json" 2>/dev/null &&
     python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(not any(p["role"]=="leader" and p["health"]=="healthy" for b in d["brokers"] for p in b["partitions"]))' "$out/topology.json"; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  printf 'Camunda did not start. See %s/engine.log\n' "$out"
  exit 1
fi

curl -sS --fail-with-body --max-time 20 \
  -F 'resources=@models/validation.bpmn' \
  -F 'resources=@models/certification-verification.bpmn' \
  -F "resources=@$out/inventory-demo.bpmn" \
  -F "resources=@$out/ProducerRestockForm.form" \
  -F 'resources=@Forms 2/InvestigateInventoryError.form' \
  -F 'resources=@camunda/forms/SubmitProductDetails.form' \
  -F 'resources=@camunda/forms/CorrectProductDetails.form' \
  -F 'resources=@camunda/forms/ManualCertificationReview.form' \
  "$engine/v2/deployments" >"$out/deployment.json" || { cat "$out/deployment.json"; exit 1; }

# The local demo must never inherit a hosted tenant or credentials.
unset CAMUNDA_TENANT_ID CAMUNDA_TOKEN_URL CAMUNDA_CLIENT_ID CAMUNDA_CLIENT_SECRET CAMUNDA_BEARER_TOKEN
export CAMUNDA_REST_URL="$engine"
export CERTIFICATION_URL='http://127.0.0.1:18090/verify'
export CATALOGUE_DB="$out/catalogue.sqlite3"
python3 camunda/service-workers/mock_certification.py --port 18090 --allow-scenarios \
  --state-file camunda/examples/certification-registry.json >"$out/certification.log" 2>&1 &
pids+=("$!")
python3 camunda/service-workers/validation_worker.py worker >"$out/validation.log" 2>&1 &
pids+=("$!")
python3 camunda/service-workers/inventory_demo_worker.py --db "$CATALOGUE_DB" >"$out/inventory.log" 2>&1 &
pids+=("$!")

python3 camunda/demo/rehearse.py --db "$CATALOGUE_DB"
printf '\nOpen %s/operate and %s/tasklist with the local demo account.\n' "$engine" "$engine"
printf 'Re-run the connected checks with: python3 camunda/demo/rehearse.py --db "%s"\n' "$CATALOGUE_DB"
if [[ "${1:-}" != --check-only ]]; then
  printf '%s\n' 'Keep this window open during the demo. Press Control+C to stop it.'
  wait
fi
