# RP-T02A Mode B: run bundle

The Noise Floor study against a real model. This is the big one: expect roughly **24,500 calls,
about $1.50, and 8 to 12 hours at laptop pace**. Run it overnight.

Contents: the notebook, `run.sh`, `progress_meter.py`, `requirements.txt`.

## Setup (identical to the T03 bundle)

```bash
unzip rpt02a-run.zip && cd rpt02a-run
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you already have the T03 bundle's venv, one addition covers this study:
`pip install rapidfuzz` inside that venv, then run from this folder.

## The three runs this bundle supports

**Run 1, OpenAI on HumanEval-Plus (do this first):**
```bash
caffeinate -i ./run.sh sk-YOUR-OPENAI-KEY
```

**Run 2, OpenAI on MBPP-Plus (second benchmark, H1's two-of-three rule):**
```bash
RPT02A_BENCH=mbpp_plus caffeinate -i ./run.sh sk-YOUR-OPENAI-KEY ./rpt02a_results_mbpp
```

**Run 3, Anthropic arm (provider replication for H4), optional:**
```bash
OPENAI_BASE_URL=https://api.anthropic.com/v1/ RPT02A_MODEL=<dated-claude-snapshot> \
caffeinate -i ./run.sh sk-ant-YOUR-KEY ./rpt02a_results_anthropic
```

Run them **one at a time**, each with its own results directory as shown. Two studies or two runs on
the same key at once saturate token-per-minute limits and slow everything by an order of magnitude.

Monitor from a second terminal:
```bash
python progress_meter.py ./rpt02a_results --watch
```

## What to expect

1. **First few minutes, silent:** the synthetic validation track (Gate G0) makes no API calls.
2. **Golden recording pass:** ~330 calls, a few minutes, heartbeat active.
3. **The long middle:** the confirmatory matrix, Mode B decomposition, and flip protocol. Per-cell
   lines print with scorer-timeout counts. The meter is the real-time view; nbconvert buffers
   console output until the end.
4. **Scoring and export:** ~15 minutes of local compute at the end.

## Interruptions are cheap now

The api phase checkpoints as it goes: the **golden recording is persisted to disk** and reloaded on
restart (saving ~330 calls and keeping replay rungs consistent across restarts), and **each completed
matrix cell is checkpointed**. If the run dies, rerun the same command into the same results
directory: it prints `RESUMING: ...` and skips what is done. A config change (model, benchmark,
grids) invalidates checkpoints via the signature, so incompatible arms can never mix.

To force a clean run, use a fresh results directory.

## Scorer timeouts

Model-generated code sometimes never terminates (the T03 run measured ~4 percent of generations).
Every candidate execution runs under a 10-second wall-clock cap and scores 0 on timeout, which is the
correct verdict for non-halting code. Counts appear on each cell line and in the meter; expect a few
hundred across the full run. If the count is far higher, tell me before trusting the pass rates.

## Reduced configurations (if 8 to 12 hours is too long)

Edit the config cell (code cell 2) before running:

| config | calls | cost | rough time |
|---|---|---|---|
| default `N_grid=(50,200)`, `R=(1,5,20)` | ~24,500 | ~$1.40 | 8 to 12 h |
| `CFG.N_grid=(200,)`, `CFG.replicates_grid=(1,5,10)` | ~13,500 | ~$0.75 | 5 to 7 h |
| `CFG.N_grid=(50,)`, `CFG.replicates_grid=(1,5,10)` | ~9,100 | ~$0.50 | 3 to 5 h |

Cut N before R: the replicate count is what buys the within-task variance estimates the study exists
to measure.

## What to send back

The whole results directory, or at minimum: `summary.json`, `confirmatory_decomposition.csv`,
`modeb_decomposition.json`, `modeb_flip.csv`, `adjudication_final.csv`, `progress_log.jsonl`.

## Troubleshooting

Same notes as the T03 bundle: `python -m pip` if bare pip resolves elsewhere; upgrade
`typing_extensions>=4.15.0` on the Sentinel ImportError; the meter, not the console, is the live
view; do not run alongside any other study on the same key.
