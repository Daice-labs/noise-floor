#!/usr/bin/env bash
# T03 Mode B launcher.  Usage:  ./run.sh sk-YOUR-OPENAI-KEY  [results_dir]
# Override the interpreter with:  PYTHON=/path/to/python ./run.sh ...
set -uo pipefail

NEEDED="nbconvert nbformat numpy pandas scipy matplotlib openai evalplus"

find_python() {
  for cand in ${PYTHON:-} python3 python /usr/bin/python3; do
    [ -z "$cand" ] && continue
    command -v "$cand" >/dev/null 2>&1 || continue
    if "$cand" - <<'PYEOF' >/dev/null 2>&1
import importlib, sys
for m in ["nbconvert","nbformat","numpy","pandas","scipy","matplotlib","openai","evalplus"]:
    importlib.import_module(m)
PYEOF
    then echo "$cand"; return 0; fi
  done
  return 1
}

PY="$(find_python)" || {
  echo "ERROR: no Python on this machine has the required packages."
  echo
  echo "You likely installed into one interpreter and are running another."
  echo "Interpreters found:"
  for cand in python3 python; do
    command -v "$cand" >/dev/null 2>&1 && \
      echo "   $cand -> $(command -v $cand)  ($($cand -V 2>&1))"
  done
  echo
  echo "Cleanest fix, a fresh virtual environment:"
  echo "   python3 -m venv .venv"
  echo "   source .venv/bin/activate"
  echo "   pip install -r requirements.txt"
  echo "   ./run.sh sk-YOUR-KEY"
  echo
  echo "Or install into the interpreter you are actually running:"
  echo "   python3 -m pip install -r requirements.txt"
  exit 1
}

KEY="${1:-${OPENAI_API_KEY:-}}"
if [ -z "$KEY" ]; then
  echo "usage: ./run.sh sk-YOUR-OPENAI-KEY [results_dir]"
  echo "   or: export OPENAI_API_KEY=sk-...  &&  ./run.sh"
  exit 1
fi
RESULTS="${2:-$(pwd)/rpt02a_results}"

export RPT02A_RESULTS="$RESULTS"
export RPT02A_RUN_MODE=api
export RPT02A_CONFIRM=1
export OPENAI_API_KEY="$KEY"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
export RPT02A_MODEL="${RPT02A_MODEL:-gpt-4o-mini-2024-07-18}"
export RPT02A_BENCH="${RPT02A_BENCH:-humaneval_plus}"
export MPLBACKEND=Agg

mkdir -p "$RESULTS"
echo "python    -> $PY  ($($PY -V 2>&1))"
echo "results   -> $RESULTS"
echo "model     -> $RPT02A_MODEL"
echo "benchmark -> $RPT02A_BENCH"
echo "expect    -> ~24,500 calls, about \$1.50, roughly 8 to 12 hours at laptop pace"
echo "monitor   -> $PY progress_meter.py \"$RESULTS\" --watch   (another terminal)"
echo "note      -> first ~3 min is synthetic validation, no API calls, no meter activity"
echo

"$PY" -m nbconvert --to notebook --execute \
  --ExecutePreprocessor.timeout=14400 \
  --output run_done.ipynb \
  RP-T02A-noise-floor-study.ipynb 2>&1 | tee run.log
STATUS=${PIPESTATUS[0]}

echo
if [ "$STATUS" -eq 0 ]; then
  echo "DONE. outputs in $RESULTS :"
  ls -1 "$RESULTS" | sed 's/^/   /'
else
  echo "run exited with status $STATUS. Completed arms are checkpointed."
  echo "Rerun the same command to resume: ./run.sh <key>"
  echo "See run.log for the traceback."
fi
