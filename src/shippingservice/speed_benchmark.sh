#!/usr/bin/env bash
set -euo pipefail

# SPEED helper for running shippingservice LKW/RIP benchmarks reliably.
# Usage:
#   ./speed_benchmark.sh run
#   ./speed_benchmark.sh full
#   ./speed_benchmark.sh fast
#   ./speed_benchmark.sh status
#   ./speed_benchmark.sh stop
#   ./speed_benchmark.sh tail

CMD="${1:-run}"
MODE="full"

if [[ "${CMD}" == "fast" ]]; then
  MODE="fast"
fi

HOSTNAME_NOW="$(hostname || true)"
SPEED_ROOT="/speed-scratch/${USER}"
WORKDIR="${SPEED_ROOT}/LLM-MAS/src/shippingservice"
LOG_DIR="${SPEED_ROOT}/benchmark_logs"
RESULT_DIR="${SPEED_ROOT}/benchmark_results"
OLLAMA_DIR_DEFAULT="${SPEED_ROOT}/tools/ollama"
OLLAMA_BIN="${OLLAMA_BIN:-${OLLAMA_DIR_DEFAULT}/bin/ollama}"

export OLLAMA_MODELS="${OLLAMA_MODELS:-${SPEED_ROOT}/ollama-models}"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
export LLAMA_BASE_URL="${LLAMA_BASE_URL:-http://127.0.0.1:11434/v1}"
export LLAMA_MODEL="${LLAMA_MODEL:-llama3.2:1b}"
export LLAMA_CONNECT_TIMEOUT="${LLAMA_CONNECT_TIMEOUT:-60}"
export LLAMA_READ_TIMEOUT="${LLAMA_READ_TIMEOUT:-900}"
export MAX_TOKENS="${MAX_TOKENS:-64}"
export MAX_ITERATIONS="${MAX_ITERATIONS:-2}"
export OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-1}"
export OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS:-1}"

mkdir -p "${LOG_DIR}" "${RESULT_DIR}" "${OLLAMA_MODELS}"

latest_log_file() {
  ls -1t "${LOG_DIR}"/lkw_run_*.log 2>/dev/null | head -n1 || true
}

require_compute_node() {
  case "${HOSTNAME_NOW}" in
    speed-submit*|speed-submit1|speed-submit2)
      echo "ERROR: You are on submit node (${HOSTNAME_NOW}). Run on compute node after salloc + srun." >&2
      exit 1
      ;;
  esac
}

check_workdir() {
  if [[ ! -d "${WORKDIR}" ]]; then
    echo "ERROR: Workdir not found: ${WORKDIR}" >&2
    echo "Clone your repo first under ${SPEED_ROOT}." >&2
    exit 1
  fi
}

check_venv() {
  if [[ ! -f "${WORKDIR}/.venv/bin/activate" ]]; then
    echo "ERROR: venv not found at ${WORKDIR}/.venv" >&2
    echo "Create it: python3 -m venv .venv ; source .venv/bin/activate ; pip install -r requirements.txt" >&2
    exit 1
  fi
}

start_ollama_if_needed() {
  if [[ ! -x "${OLLAMA_BIN}" ]]; then
    echo "ERROR: Ollama binary not found/executable: ${OLLAMA_BIN}" >&2
    exit 1
  fi

  if curl -s "http://${OLLAMA_HOST}/v1/models" >/dev/null 2>&1; then
    echo "Ollama already running at ${OLLAMA_HOST}".
  else
    echo "Starting Ollama on ${OLLAMA_HOST} ..."
    nohup "${OLLAMA_BIN}" serve > "${SPEED_ROOT}/ollama-serve.log" 2>&1 &
    sleep 5
  fi

  if ! curl -s "http://${OLLAMA_HOST}/v1/models" >/dev/null 2>&1; then
    echo "ERROR: Ollama did not start. Check ${SPEED_ROOT}/ollama-serve.log" >&2
    exit 1
  fi

  if ! curl -s "http://${OLLAMA_HOST}/v1/models" | grep -q "${LLAMA_MODEL}"; then
    echo "Pulling model ${LLAMA_MODEL} ..."
    "${OLLAMA_BIN}" pull "${LLAMA_MODEL}"
  fi

  echo "Warming up model ${LLAMA_MODEL} ..."
  curl -s --max-time 180 "http://${OLLAMA_HOST}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${LLAMA_MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with OK\"}],\"max_tokens\":8,\"temperature\":0}" \
    >/dev/null 2>&1 || echo "WARN: warmup request timed out; continuing anyway"
}

run_benchmark() {
  require_compute_node
  check_workdir
  check_venv
  start_ollama_if_needed

  timestamp="$(date +%Y%m%d_%H%M%S)"
  run_log="${LOG_DIR}/lkw_run_${timestamp}.log"

  echo "Running benchmark on ${HOSTNAME_NOW}"
  echo "Log: ${run_log}"
  echo "Model: ${LLAMA_MODEL}"
  echo "LLAMA_BASE_URL: ${LLAMA_BASE_URL}"
  echo "LLAMA_CONNECT_TIMEOUT=${LLAMA_CONNECT_TIMEOUT} LLAMA_READ_TIMEOUT=${LLAMA_READ_TIMEOUT}"
  echo "MAX_TOKENS=${MAX_TOKENS} MAX_ITERATIONS=${MAX_ITERATIONS}"
  echo "FAULTS_TO_TEST=${FAULTS_TO_TEST:-<all defaults from runner>}"

  (
    cd "${WORKDIR}"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    python -u lkw_rip_runner.py
  ) > "${run_log}" 2>&1

  if [[ -f "${WORKDIR}/lkw_rip_results.json" ]]; then
    cp "${WORKDIR}/lkw_rip_results.json" "${RESULT_DIR}/lkw_rip_results_${timestamp}.json"
    echo "Saved results: ${RESULT_DIR}/lkw_rip_results_${timestamp}.json"
  else
    echo "WARNING: lkw_rip_results.json not found after run"
  fi

  echo "Done. Tail log with: ./speed_benchmark.sh tail"
}

run_full_benchmark() {
  export LLAMA_MODEL="${FULL_MODEL:-llama3.2:1b}"
  export MAX_TOKENS="${FULL_MAX_TOKENS:-192}"
  export MAX_ITERATIONS="${FULL_MAX_ITERATIONS:-4}"
  export LLAMA_CONNECT_TIMEOUT="${FULL_CONNECT_TIMEOUT:-60}"
  export LLAMA_READ_TIMEOUT="${FULL_READ_TIMEOUT:-1200}"
  export LLAMA_CALL_RETRIES="${FULL_CALL_RETRIES:-1}"
  export LLAMA_RETRY_BACKOFF="${FULL_RETRY_BACKOFF:-2}"

  # Full mode should use the runner's complete default fault list unless overridden.
  if [[ -n "${FULL_FAULTS_TO_TEST:-}" ]]; then
    export FAULTS_TO_TEST="${FULL_FAULTS_TO_TEST}"
  else
    unset FAULTS_TO_TEST || true
  fi

  echo "FULL MODE enabled"
  run_benchmark
}

run_fast_benchmark() {
  export LLAMA_MODEL="${FAST_MODEL:-qwen2.5:0.5b}"
  export MAX_TOKENS="${FAST_MAX_TOKENS:-96}"
  export MAX_ITERATIONS="${FAST_MAX_ITERATIONS:-2}"
  export FAULTS_TO_TEST="${FAST_FAULTS_TO_TEST:-NONE,FM_3_1}"

  echo "FAST MODE enabled"
  echo "FAULTS_TO_TEST=${FAULTS_TO_TEST}"
  run_benchmark
}

show_status() {
  echo "Host: ${HOSTNAME_NOW}"
  echo "OLLAMA_HOST=${OLLAMA_HOST}"
  echo "LLAMA_MODEL=${LLAMA_MODEL}"
  echo "Workdir=${WORKDIR}"
  echo "Latest run log: $(latest_log_file)"
  echo
  echo "Processes:"
  ps -ef | grep -E "ollama|lkw_rip_runner" | grep -v grep || true
  echo
  echo "Models endpoint:"
  curl -s "http://${OLLAMA_HOST}/v1/models" || echo "unreachable"
}

stop_all() {
  pkill -f lkw_rip_runner.py || true
  pkill -f "ollama serve" || true
  echo "Stopped lkw_rip_runner and ollama serve (if running)."
}

follow_latest_log() {
  log="$(latest_log_file)"
  if [[ -z "${log}" ]]; then
    echo "No benchmark logs found in ${LOG_DIR}" >&2
    exit 1
  fi
  echo "Tailing ${log}"
  tail -f "${log}"
}

case "${CMD}" in
  run)
    run_full_benchmark
    ;;
  full)
    run_full_benchmark
    ;;
  fast)
    run_fast_benchmark
    ;;
  status)
    show_status
    ;;
  stop)
    stop_all
    ;;
  tail)
    follow_latest_log
    ;;
  *)
    echo "Unknown command: ${CMD}" >&2
    echo "Usage: $0 {run|full|fast|status|stop|tail}" >&2
    exit 2
    ;;
esac
