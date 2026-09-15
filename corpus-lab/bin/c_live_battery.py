#!/usr/bin/env python
"""c_live_battery.py -- launches the 2026-09-15 live battery.

Why this exists rather than run_harness.py, recorded as a deviation.
run_harness.py is a frozen instrument and it cannot produce the session
configuration this battery is defined over: it appends
"Cite the exact file paths (and page numbers for PDFs) you used." to every
question, and it does not forward --disallowed, so its sessions would run with
ask.py's default Write,Edit,NotebookEdit rather than the specified list. The
master prompt fixes the session configuration as identical for every question
and fixes the prompt as the question text alone, and the absence comparison
spans the frozen 3 and the extra 12, so the two groups must be run the same
way. This driver therefore calls ask.py per question with exactly the specified
arguments, at --parallel 2, and touches run_harness.py not at all.

  python -u corpus-lab/bin/c_live_battery.py --group frozen20 --model <id>
  python -u corpus-lab/bin/c_live_battery.py --group extra_abs --model <id>
  python -u corpus-lab/bin/c_live_battery.py --probe auth --model <id>

Phase 10.1.3 adds `--capture full` (default `last`, unchanged). The harness keeps
the LAST assistant message, so a session the Stop guard challenged records only
the confirmation reply and the real answer is lost. With `--capture full` the
record gains two fields beside the untouched `answer_text`:
`answer_text_last` (what was always stored) and `answer_text_full` (the
reconstruction). The reconstruction is `c_score_live_v3.reconstruct_full_answer`
-- the SAME function the scorer uses on recorded sessions, so the live path and
the re-scoring path cannot drift apart.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

STACK = "s7_shelf"
CORPUS_LABEL = "h15000"
DISALLOWED = "Write,Edit,NotebookEdit,Agent,WebFetch,WebSearch"
MAX_TURNS = 25
TIMEOUT = 300
PERMISSION_MODE = "bypassPermissions"


def rung():
    return (L.HARNESS / "corpus_15000").resolve()


def ask_cmd(phase, qid, question, model, max_turns=MAX_TURNS, timeout=TIMEOUT):
    return [sys.executable, str(L.ASK),
            "--phase", phase, "--stack", STACK,
            "--corpus", str(rung()), "--corpus-label", CORPUS_LABEL,
            "--qid", qid, "--question", question,
            "--model", model,
            "--max-turns", str(max_turns), "--timeout", str(timeout),
            "--permission-mode", PERMISSION_MODE,
            "--disallowed", DISALLOWED]


def run_one(phase, qid, question, model, max_turns=MAX_TURNS, timeout=TIMEOUT):
    env = dict(os.environ)
    env.pop("CANARY_MANIFEST", None)
    p = subprocess.run(ask_cmd(phase, qid, question, model, max_turns, timeout),
                       capture_output=True, text=True, errors="replace", env=env)
    return qid, p.returncode, (p.stdout or "").strip()[-300:], (p.stderr or "")[-300:]


def load_questions():
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in key["questions"]}
    sample = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    frozen = sorted(sample["q_ids"])
    extra_abs = sorted(q["q_id"] for q in key["questions"]
                       if q["type"] == "absence" and q["q_id"] not in set(frozen))[:12]
    return qs_by_id, frozen, extra_abs


def add_full_capture(phase, qid):
    """Attach the reconstructed answer to a finished session's record.

    Additive only: `answer_text` is never rewritten, so every scorer that reads
    the old field reads exactly what it read before.
    """
    import c_score_live_v3 as V3
    base = L.RUNS / phase / ("%s__%s__%s" % (STACK, CORPUS_LABEL, qid))
    rj, jl = base.with_suffix(".json"), base.with_suffix(".jsonl")
    if not rj.exists() or not jl.exists():
        return None
    try:
        rec = json.loads(rj.read_text(encoding="utf-8"))
        recon = V3.reconstruct_full_answer(jl)
        rec["answer_text_last"] = recon["answer_text_last"]
        rec["answer_text_full"] = recon["answer_text_full"]
        rec["answer_was_fragment"] = recon["was_fragment"]
        rec["n_hook_blocks"] = recon["n_hook_blocks"]
        rec["capture"] = "full"
        rj.write_text(json.dumps(rec, indent=1), encoding="utf-8")
        return recon
    except Exception as e:
        print("  CAPTURE_FULL_FAILED %s: %s" % (qid, e), file=sys.stderr)
        return None


def result_exists(phase, qid):
    return (L.RUNS / phase / ("%s__%s__%s.json" % (STACK, CORPUS_LABEL, qid))).exists()


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", choices=["frozen20", "extra_abs"])
    ap.add_argument("--probe", choices=["auth", "iso1", "iso2", "guard"])
    ap.add_argument("--probe-question", default=None)
    ap.add_argument("--model", required=True)
    ap.add_argument("--parallel", type=int, default=2)
    # Phase 9.3.4. The professor has neither a turn cap nor a 300s clock; 1-5 of
    # every 17 sessions in P5-P8 ended with no answer text at all because one of
    # these fired, and every one of those was scored a miss. Defaults are the
    # frozen values, so every recorded battery still reproduces.
    ap.add_argument("--max-turns", dest="max_turns", type=int, default=MAX_TURNS)
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    ap.add_argument("--capture", choices=["last", "full"], default="last",
                    help="full: also store answer_text_full, reconstructed across "
                         "a guard interruption (adds fields; changes none)")
    ap.add_argument("--phase-tag", dest="phase_tag", default="P5",
                    help="phase prefix; a re-battery uses a NEW tag so ask.py's "
                         "stale-result guard is respected instead of forced")
    a = ap.parse_args(argv)

    if a.probe:
        phase = a.phase_tag + "_probe"
        qid = "probe_" + a.probe
        mt = 1 if a.probe == "auth" else (6 if a.probe == "guard" else 4)
        qid_, rc, so, se = run_one(phase, qid, a.probe_question, a.model,
                                   max_turns=mt, timeout=a.timeout)
        print("PROBE %s rc=%d %s" % (a.probe, rc, so))
        if se.strip():
            print("stderr: %s" % se.strip()[:200], file=sys.stderr)
        return 0 if rc == 0 else 1

    qs_by_id, frozen, extra_abs = load_questions()
    if a.group == "frozen20":
        phase, ids = a.phase_tag + "_live", frozen
    else:
        phase, ids = a.phase_tag + "_live_abs", extra_abs

    todo = [i for i in ids if not result_exists(phase, i)]
    print("group=%s phase=%s total=%d todo=%d" % (a.group, phase, len(ids), len(todo)),
          flush=True)

    t0 = time.monotonic()
    done = 0
    with ThreadPoolExecutor(max_workers=a.parallel) as ex:
        futs = [ex.submit(run_one, phase, qid, qs_by_id[qid]["question"], a.model,
                          a.max_turns, a.timeout)
                for qid in todo]
        for f in futs:
            qid, rc, so, se = f.result()
            done += 1
            note = ""
            if a.capture == "full":
                recon = add_full_capture(phase, qid)
                if recon and recon["was_fragment"]:
                    note = "  [FRAGMENT recovered %d -> %d chars]" % (
                        len(recon["answer_text_last"]), len(recon["answer_text_full"]))
            print("[%s] rc=%d %s%s" % (qid, rc, so, note), flush=True)
            if done % 5 == 0 or done == len(todo):
                cost, n = 0.0, 0
                for i in ids:
                    p = L.RUNS / phase / ("%s__%s__%s.json" % (STACK, CORPUS_LABEL, i))
                    if p.exists():
                        d = json.loads(p.read_text(encoding="utf-8"))
                        if d.get("cost_usd") is not None:
                            cost += d["cost_usd"]
                            n += 1
                to = sum(1 for i in ids
                         if (L.RUNS / phase / ("%s__%s__%s.json" % (STACK, CORPUS_LABEL, i))).exists()
                         and json.loads((L.RUNS / phase / ("%s__%s__%s.json" % (STACK, CORPUS_LABEL, i))).read_text(encoding="utf-8")).get("timed_out"))
                print("  PROGRESS n_done=%d/%d cost_usd=%.4f (n=%d) timeouts=%d"
                      % (done, len(todo), cost, n, to), flush=True)
    print("battery wall %.0fs" % (time.monotonic() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
