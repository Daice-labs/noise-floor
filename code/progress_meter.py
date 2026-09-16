#!/usr/bin/env python3
"""Live progress meter for RP-T02A / RP-T03 runs.

    python3 progress_meter.py <results_dir>              one-shot status
    python3 progress_meter.py <results_dir> --watch      live meter, refreshes every 10s
    python3 progress_meter.py <results_dir> --plot       write progress_over_time.png
    python3 progress_meter.py <results_dir> --watch -n 5 custom refresh seconds

Safe against a live run: opens the ledger read-only and only appends nothing.
"""
import sys, os, json, time, sqlite3, argparse

BAR_W = 40

def read_current(d):
    p = os.path.join(d, "progress.json")
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except Exception:
        return None

def read_series(d):
    p = os.path.join(d, "progress_log.jsonl")
    if not os.path.exists(p):
        return []
    rows = []
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows

def ledger_arms(d):
    led = os.path.join(d, "ledger.sqlite")
    if not os.path.exists(led):
        return []
    try:
        con = sqlite3.connect(f"file:{led}?mode=ro", uri=True)
        rows = list(con.execute(
            "SELECT arm, created FROM runs WHERE target='modeb' OR arm LIKE 'cm_%' "
            "OR arm LIKE 'mb_%' OR arm LIKE 'mbfl_%' ORDER BY created"))
        con.close()
        return rows
    except Exception:
        return []

def bar(frac, width=BAR_W):
    frac = max(0.0, min(1.0, frac))
    n = int(round(frac * width))
    return "[" + "#" * n + "." * (width - n) + f"] {frac*100:5.1f}%"

def fmt_status(d):
    cur = read_current(d)
    out = []
    if not cur:
        out.append("no progress.json yet: still in the synthetic validation track (no API calls),")
        out.append("or the run has not reached its API phase.")
        arms = ledger_arms(d)
        if arms:
            out.append(f"ledger shows {len(arms)} API arms already completed.")
        return "\n".join(out)

    age = time.time() - cur.get("updated", 0)
    alive = age < 180
    done, total = cur.get("done", 0), cur.get("total", 0) or 1
    loc = ""
    if cur.get("task_id"):
        loc = f"   [task {cur.get('task_index')} {cur.get('task_id')} rep {cur.get('replicate')} / {cur.get('phase')}]"
    out.append(f"arm: {cur.get('arm')}   {done}/{total} calls{loc}")
    out.append("  " + bar(done / total))
    out.append(f"  heartbeat age : {age:5.0f}s  ->  {'ALIVE' if alive else 'STALE (>3 min): check the process'}")

    # Whole-run accounting FIRST: the per-arm rate below cannot reveal a process that spent
    # most of its life not making calls, which is exactly how a Colab-killed run reads.
    if cur.get("run_elapsed_min") is not None:
        rem = cur["run_elapsed_min"]; duty = cur.get("duty_cycle")
        out.append(f"  WHOLE RUN     : {rem:.1f} min elapsed | "
                   f"{cur.get('arms_done_this_process', 0)} arms finished | "
                   f"{cur.get('calls_this_process', 0)} calls made")
        out.append(f"  duty cycle    : {duty} calls/s over the ENTIRE process lifetime")
        inarm = cur.get("rate_cum_per_s")
        if duty is not None and inarm and duty < 0.5 * inarm:
            out.append("                  ^^ far below the in-arm rate: this process was IDLE or")
            out.append("                     STOPPED for most of its life. Not a slowness problem.")
        out.append("")

    # legacy heartbeat (pre-instrumentation runs) only has rate_per_s; map it so older
    # in-flight runs still render instead of showing a wall of None.
    legacy = "rate_cum_per_s" not in cur
    rc = cur.get("rate_cum_per_s", cur.get("rate_per_s"))
    rr = cur.get("rate_recent_per_s")
    if legacy:
        out.append("  (legacy heartbeat: this run predates call-meter instrumentation, so")
        out.append("   latency and rate-limit counters are unavailable for it)")
    out.append(f"  throughput    : cumulative {rc}/s" + (f" | recent {rr}/s" if rr else ""))
    if rc and rr and rr < 0.4 * rc:
        out.append("                  ^ recent << cumulative: THROUGHPUT IS COLLAPSING")
    if not legacy:
        out.append(f"  latency       : p50 {cur.get('lat_p50')}s  p95 {cur.get('lat_p95')}s  max {cur.get('lat_max')}s")
        rl, er = cur.get("rate_limit_hits", 0), cur.get("errors", 0)
        flag = "  <-- THROTTLED" if rl else ""
        out.append(f"  rate limits   : {rl} 429s, {er} other errors, "
                   f"{cur.get('retry_sleep_min', 0)} min lost to backoff{flag}")
    st = cur.get("scorer_timeouts") or {}
    if st.get("candidate"):
        out.append(f"  scorer        : {st['candidate']} timeouts (non-terminating model code, scored 0)")
    eta = cur.get("eta_min")
    out.append(f"  ETA this arm  : {eta} min" if eta else "  ETA this arm  : (estimating)")

    arms = ledger_arms(d)
    if arms:
        out.append(f"  arms complete : {len(arms)}  (last: {arms[-1][0]})")
        if len(arms) >= 2:
            spans = [(arms[i][1] - arms[i-1][1]) / 60 for i in range(1, len(arms))]
            out.append(f"  mean arm time : {sum(spans)/len(spans):.1f} min")
    return "\n".join(out)

def plot(d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = read_series(d)
    if len(rows) < 2:
        print("not enough time-series data yet (need progress_log.jsonl with >=2 rows)")
        return
    t0 = rows[0]["updated"]
    mins = [(r["updated"] - t0) / 60 for r in rows]
    cum = [r.get("rate_cum_per_s") or 0 for r in rows]
    rec = [r.get("rate_recent_per_s") or 0 for r in rows]
    r429 = [r.get("rate_limit_hits") or 0 for r in rows]
    p95 = [r.get("lat_p95") or 0 for r in rows]

    fig, ax = plt.subplots(3, 1, figsize=(9, 8), sharex=True)
    ax[0].plot(mins, cum, label="cumulative calls/s", color="#888")
    ax[0].plot(mins, rec, label="recent calls/s", color="#2a7")
    ax[0].set_ylabel("calls / s"); ax[0].legend(fontsize=8)
    ax[0].set_title("Throughput over time (recent falling below cumulative = throttling)")
    ax[1].plot(mins, p95, color="#c33"); ax[1].set_ylabel("latency p95 (s)")
    ax[1].set_title("Per-call latency")
    ax[2].plot(mins, r429, color="#c33"); ax[2].set_ylabel("cumulative 429s")
    ax[2].set_xlabel("minutes since first heartbeat")
    ax[2].set_title("Rate-limit events")
    plt.tight_layout()
    out = os.path.join(d, "progress_over_time.png")
    plt.savefig(out, dpi=140)
    print("wrote", out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir", nargs="?",
                    default=os.environ.get("RPT03_RESULTS", os.environ.get("RPT02A_RESULTS", "rpt03_results")))
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--plot", action="store_true")
    ap.add_argument("-n", type=int, default=10, help="watch refresh seconds")
    a = ap.parse_args()
    d = os.path.abspath(a.results_dir)
    if not os.path.isdir(d):
        print("no such results dir:", d); sys.exit(1)
    if a.plot:
        plot(d); return
    if not a.watch:
        print(f"== {d} ==\n" + fmt_status(d)); return
    try:
        while True:
            os.system("clear" if os.name != "nt" else "cls")
            print(f"== {d} ==   {time.strftime('%H:%M:%S')}   (ctrl-c to exit)\n")
            print(fmt_status(d))
            time.sleep(a.n)
    except KeyboardInterrupt:
        print("\nstopped watching (the run is unaffected)")

if __name__ == "__main__":
    main()
