# RP-T02A Arm 2 Verification + Cross-Benchmark Aggregation

**Arm 2 (MBPP-Plus, same hosted model as arm 1): all rows reproduce exactly from the raw
ledger** using the study's own estimator functions executed against `ledger.sqlite`. Components
match to six decimals (provider 0.013237, harness 0.001105, judge 0.000000), within-variances by
rung match, both flip rows match to the digit, and the seeded cluster bootstrap reproduces. The
ledger is clean: every empirical arm ran exactly once (the duplicate rows are all
validation-track arms, which re-run in-process on every launch by design, at zero API cost);
empirical fallbacks are zero, so replay integrity holds.

## Arm 2 verdicts (recomputed)

| Row | Measured | Verdict |
|---|---|---|
| H1 provider largest | provider 0.0132 vs harness 0.0011, judge 0.0000 | PASS |
| H2 harness CI excludes zero | CI (0.0, 0.00187): includes zero | FAIL (pre-registered) |
| H3 detection ratio >= 2.0 | runs-to-detect L0=3, L2=1, ratio 3.00 | PASS |
| H4 hosted temp-0 residual variance | within(L1) = 0.0075 > 0 | PASS |
| H6 winner instability (retry pair) | delta 0.025, disagreement 0.167 | REPORTED (awaits G2) |
| H6 winner instability (temp pair) | delta 0.023, disagreement 0.167 | REPORTED (awaits G2) |

## Cross-benchmark aggregation (the paper's >= 2-of-3 rule, two benchmarks run)

| Hypothesis | HumanEval-Plus | MBPP-Plus | Aggregate |
|---|---|---|---|
| H1 provider largest component | PASS (0.0301; only detectable) | PASS (0.0132; 92% of decomposed) | **CONFIRMATORY PASS** |
| H2 harness component nonzero | FAIL (identically 0) | FAIL (CI includes 0; <= 0.0019 at 95%) | **CONFIRMATORY FAIL** (the strong negative) |
| H3 pinned-run detection ratio >= 2 | PASS (6.0) | PASS (3.0; matches synthetic prediction) | **CONFIRMATORY PASS** |
| H4 hosted temp-0 not deterministic | PASS (0.0133) | PASS (0.0075) | **CONFIRMATORY PASS** |
| H6 winner instability | REPORTED (0.167/0.333) | REPORTED (0.167/0.167) | REPORTED, pending G2 delta lock |

## Cross-benchmark structure worth the paper's attention

1. **The negative result is the headline.** On both benchmarks the harness contributes nothing
   detectable to run-to-run variance: exactly zero on HumanEval-Plus, bounded below 0.0019 on
   MBPP-Plus. The "flaky evals" folk wisdom attributes noise to harnesses; measurement attributes
   essentially all of it to the provider.
2. **The noise floor is benchmark-dependent by about 2x** (provider component 0.030 vs 0.013),
   and the detection economics track it: the same surveyed-median effect needs 6 unpinned runs on
   HumanEval-Plus but 3 on MBPP-Plus, versus 1 pinned run on either.
3. **Temperature-attributable variance is now separable on MBPP** (L0 minus L1 = 0.0067 of the
   0.0142 total), giving the ladder its cleanest per-rung story yet.
4. Scorer timeout caveat carries forward (845 candidate timeouts this arm, uniform across rungs;
   differences are the estimands). H6's final verdicts await the surveyed-delta lock at G2;
   current deltas 0.018 to 0.030 with disagreement 0.167 to 0.333 across four natural pairs.

## Provenance

Arm 2: 560 runs, 1,378,300 observations; Mode B at N=200 x R=20 x 4 rungs plus 48 flip arms;
22,731 calls this process, 0 errors, 0 rate limits; two interruptions (sleep, 4-hour nbconvert
cell timeout, subsequently patched to unlimited) with no empirical-arm duplication. Seed 20260710
both arms; same model both arms.
