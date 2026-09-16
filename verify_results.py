#!/usr/bin/env python3
"""Verify the shipped T02A ledgers against the expected-output manifest.
Extracts the study's own estimator functions from the notebook in code/ and
executes them against both arms' raw SQLite ledgers, reproducing the Mode B
decomposition, the harness confidence interval, detection economics, hosted
temperature-zero variance, and both natural-pair flip experiments."""
import json, re, sqlite3, sys, math
import numpy as np, pandas as pd
import scipy.stats as st
from collections import defaultdict

nb = json.load(open("code/RP-T02A-noise-floor-study.ipynb"))
src = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
def grab(name):
    i = src.find(f"def {name}"); j = src.find("\ndef ", i + 1)
    return src[i:j if j > 0 else i + 2500]
exec("\n".join(grab(n) for n in ["z", "per_task_stats", "within_var", "between_var",
                                 "decompose", "cluster_bootstrap", "mde",
                                 "detection_power", "runs_to_detect"]))

exp = json.load(open("expected_outputs.json")); fail = []
def check(name, got, want, tol=1e-4):
    ok = (abs(got - want) <= tol) if isinstance(want, float) else (got == want)
    print(("  OK   " if ok else "  FAIL ") + f"{name}: {round(got,6) if isinstance(got,float) else got} (expected {want})")
    if not ok: fail.append(name)

class Cfg: master_seed = 20260710; bootstrap_iters = 400

def arm_frames(dbpath, l0_run=None):
    db = sqlite3.connect(dbpath)
    def get(arm, run=None):
        if run:
            return pd.read_sql_query(
                "SELECT task_id, family_id, replicate, outcome FROM obs WHERE run_id=?", db, params=(run,))
        return pd.read_sql_query(
            """SELECT o.task_id, o.family_id, o.replicate, o.outcome FROM obs o
               JOIN runs r ON o.run_id = r.run_id WHERE r.arm = ?""", db, params=(arm,))
    rb = {"L0": get("mb_L0", l0_run), "L1": get("mb_L1"), "L2": get("mb_L2"), "L2_rule": get("mb_L2r")}
    rb["L3"] = rb["L2_rule"]
    return db, rb

print("--- Arm 1: HumanEval-Plus (adjudication batch L0:mb_L0:24f5f5a6) ---")
db1, rb1 = arm_frames("results_arm1/ledger.sqlite", "L0:mb_L0:24f5f5a6")
e1 = decompose(rb1); w1 = e1["_within_by_rung"]
check("arm1_provider", e1["provider"], exp["arm1"]["provider"], 5e-4)
check("arm1_harness", e1["harness"], 0.0, 1e-9)
check("arm1_judge", e1["judge"], 0.0, 1e-9)
check("arm1_within_L1", w1["L1"], exp["arm1"]["within_L1"], 5e-5)
check("arm1_runs_ratio", runs_to_detect(0.02, w1["L0"], 200) / runs_to_detect(0.02, w1["L2"], 200), exp["arm1"]["ratio"], 0.01)
prev = pd.read_sql_query("SELECT task_id, family_id, replicate, outcome FROM obs WHERE run_id='L0:mb_L0:e803a86a'", db1)
check("arm1_free_replication_batch1_within", within_var(prev), exp["arm1"]["batch1_within"], 5e-4)

print("--- Arm 2: MBPP-Plus ---")
db2, rb2 = arm_frames("results_arm2/ledger.sqlite")
e2 = decompose(rb2); w2 = e2["_within_by_rung"]
check("arm2_provider", e2["provider"], exp["arm2"]["provider"], 5e-5)
check("arm2_harness", e2["harness"], exp["arm2"]["harness"], 5e-5)
check("arm2_judge", e2["judge"], 0.0, 1e-9)
ci = cluster_bootstrap(rb2, Cfg, iters=200)
check("arm2_harness_CI_includes_zero", ci["harness"][0] <= 1e-12, True)
check("arm2_harness_CI_upper", float(ci["harness"][1]), exp["arm2"]["harness_ci_hi"], 5e-4)
check("arm2_within_L1", w2["L1"], exp["arm2"]["within_L1"], 5e-5)
check("arm2_temp_attributable", w2["L0"] - w2["L1"], exp["arm2"]["temp_attr"], 5e-5)
check("arm2_runs_ratio", runs_to_detect(0.02, w2["L0"], 200) / runs_to_detect(0.02, w2["L2"], 200), exp["arm2"]["ratio"], 0.01)

for dbx, armtag, pairs in ((db1, "arm1", exp["arm1"]["flips"]), (db2, "arm2", exp["arm2"]["flips"])):
    for label, (want_d, want_dis) in pairs.items():
        realized, disagree = [], 0
        for p_ in range(6):
            signs = []
            for rerun in ("a", "b"):
                def mean_of(a):
                    return pd.read_sql_query(
                        """SELECT AVG(o.outcome) v FROM obs o JOIN runs r ON o.run_id = r.run_id
                           WHERE r.arm = ?""", dbx, params=(a,)).v[0]
                d = mean_of(f"mbfl_{label}_{p_}_{rerun}_A") - mean_of(f"mbfl_{label}_{p_}_{rerun}_B")
                realized.append(d); signs.append(np.sign(d) if d != 0 else 1.0)
            disagree += int(signs[0] != signs[1])
        check(f"{armtag}_flip_{label}_delta", float(np.mean(realized)), want_d, 1e-3)
        check(f"{armtag}_flip_{label}_disagreement", disagree / 6, want_dis, 1e-3)

print("\n" + ("ALL CHECKS PASSED" if not fail else f"{len(fail)} CHECK(S) FAILED"))
sys.exit(0 if not fail else 1)
