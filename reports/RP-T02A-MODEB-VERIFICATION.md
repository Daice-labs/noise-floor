# RP-T02A Mode B Verification Report (Arm 1: HumanEval-Plus, hosted endpoint)

**Verdict: all six adjudication rows reproduce from the raw ledger.** Method: the study's own
estimator functions (`per_task_stats`, `within_var`, `decompose`, `cluster_bootstrap`,
`runs_to_detect`) were extracted verbatim from the run bundle and executed against
`ledger.sqlite` directly, so no transcription of formulas was involved.

## Shipped vs recomputed

| Row | Shipped | Recomputed | Status |
|---|---|---|---|
| H1 provider component | 0.0301 | 0.0301 (batch 2; see below) | exact |
| H1 harness / judge | 0.0000 / 0.0000 | 0.0000 / 0.0000 | exact |
| H2 harness CI lower | 0.0000 (FAIL) | (0.0, 0.0) seeded bootstrap, 200 iters | exact |
| H3 runs-to-detect | L0=6, L2=1, ratio 6.0 | 6, 1, 6.0 (batch 2) | exact |
| H4 within(L1) | 0.01329 | 0.01329 | exact to 5 dp |
| H6 retry_on_vs_off | delta 0.03, disagreement 0.167 | 0.0300, 0.167 | exact |
| H6 prodtemp_vs_temp0 | delta 0.0183, disagreement 0.333 | 0.0183, 0.333 | exact |

## The dual-batch finding (resolved)

The ledger contains **two complete 20-replicate mb_L0 batches** ~15 h apart, the checkpoint-resume
fingerprint: `e803a86a` (pre-resume) and `24f5f5a6` (post-resume). The shipped adjudication used the
in-memory post-resume batch; pooling both gives provider 0.0312 and runs-to-detect 7. Resolution:
adjudication provenance is batch `24f5f5a6`. Interpretation upgrade: the two batches are
**independent measurements of within(L0)**, 0.0321 vs 0.0301, identical verdicts under both
(H1 PASS, H3 ratio 6.0 or 7.0 vs threshold 2.0), i.e., a free replication showing the provider
component is stable across a 15-hour gap on a live endpoint.

## Reading the results

- **H1 (PASS):** provider variance 0.0301 with harness and judge at exactly zero: on this
  benchmark x model, the provider is not merely the largest component, it is the only detectable
  one. Replay + either scorer is byte-stable (within(L2) = within(L2_rule) = 0).
- **H2 (FAIL, pre-registered):** the harness CI is (0.0, 0.0) under the seeded cluster bootstrap:
  the harness component is zero to bootstrap precision. An honest negative result that
  strengthens the ladder story rather than weakening it.
- **H3 (PASS):** one pinned run detects the surveyed-median delta that takes six unpinned runs
  (prediction was 3.0; reality is better). Scope caveat as printed: catalog injection on real
  scaffolds remains the repo-scale experiment.
- **H4 (PASS):** hosted temperature-0 leaves residual within-variance 0.0133 > 0.
- **H6 (REPORTED x2):** realized deltas 0.030 / 0.018 with pair disagreement 16.7% / 33.3%;
  adjudication correctly deferred to the surveyed-delta bins locked at G2.

## Caveats carried forward

1. Scorer timeouts: 631 candidate-side timeouts in the final process were scored under the
   timeout-as-fail cap policy; this is uniform across rungs (differences, not levels, are the
   estimands) but should be stated in the paper's Limitations.
2. Scope: one benchmark x model. The paper's own aggregation rule requires >= 2 of 3 benchmarks
   for confirmatory verdicts; arm 2 (MBPP-Plus) is the gating item.
3. H6 verdicts await the EXP5/G2 surveyed-delta lock (current 0.02 is the declared placeholder).
4. between-task variance (L3): 0.2108. Fallbacks: 26,172 recorded, all in the validation track's
   2,205 synthetic runs where fault injection is designed behavior; every empirical run (matrix,
   Mode B, all 48 flip arms) recorded zero fallbacks, so replay integrity holds where the
   harness-zero claim depends on it.

## Context

2,314 runs; 6,097,284 observations total in the ledger (matrix + Mode B + flip); Mode B block
164 tasks x 20 replicates x 4 arms plus 48 flip arms; final process: 12,238 calls, 0 errors,
0 rate-limit hits.
