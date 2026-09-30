#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

export TCC_SKILL_PATH="${TCC_SKILL_PATH:-../Skills/skills/tcc/scripts}"

python3 tools/run_phase1_v2_tcc_pipeline.py

if curl -fsS http://127.0.0.1:1234/v1/models >/tmp/llmec_models.json 2>/dev/null; then
  export LLM_PROVIDER="openai-compatible"
  export LLM_ENDPOINT="http://127.0.0.1:1234/v1"
  if [ -z "${LLM_MODEL:-}" ]; then
    export LLM_MODEL="$(python3 - <<'PY'
import json
x=json.load(open('/tmp/llmec_models.json'))
rows=x.get('data') or []
print(rows[0].get('id','') if rows else '')
PY
)"
  fi
elif curl -fsS http://127.0.0.1:11434/api/tags >/tmp/llmec_models.json 2>/dev/null; then
  export LLM_PROVIDER="ollama"
  export LLM_ENDPOINT="http://127.0.0.1:11434"
  if [ -z "${LLM_MODEL:-}" ]; then
    export LLM_MODEL="$(python3 - <<'PY'
import json
x=json.load(open('/tmp/llmec_models.json'))
rows=x.get('models') or []
print(rows[0].get('name','') if rows else '')
PY
)"
  fi
else
  echo "RESULT,LOCAL_LLM_ENDPOINT,BLOCKED"
  echo "Start LM Studio local server or Ollama, then run this same file again."
  exit 2
fi

if [ -z "${LLM_MODEL:-}" ]; then
  echo "RESULT,LOCAL_LLM_MODEL,BLOCKED"
  exit 2
fi

echo "LLM_PROVIDER=$LLM_PROVIDER"
echo "LLM_MODEL=$LLM_MODEL"
python3 tools/run_llm_s3_s4_cache.py
python3 tools/compare_s3_s4.py | tee results/phase1_c_vs_d_comparison.json

echo "RESULT,PHASE1_FIXED_CANDIDATE_COMPARISON,PASS"
