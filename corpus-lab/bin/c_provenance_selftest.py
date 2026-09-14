#!/usr/bin/env python
"""c_provenance_selftest.py -- 2026-09-15 evening, Phase 2.

Two production changes earned by passed gates, each with a self-test:

  1. B2c (F55) is the CLI default for `inside` and `series`. The Python
     defaults stay None, so every recorded measurement still reproduces with
     explicit flags. Confirmed by driving the CLI as a SUBPROCESS on three
     questions' worth of evidence addresses and checking the pages it returns
     are the ones the in-process dense_first call returns.

  2. `note` refuses a citation whose page was not opened under the same slug.
     The two batteries measured 5 and then 8 answers citing a file the session
     never opened, with the instruction to open first sitting in CLAUDE.md the
     whole time. This moves it from prose into the tool.

  python -u corpus-lab/bin/c_provenance_selftest.py
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402

DB = str(L.STACKS / "s2_fts5" / "harness_15000.db")
SHELF = str(L.STACKS / "s7_shelf" / "shelf.db")
SHELF_PY = str(L.BIN / "c_shelf.py")


def run_cli(args):
    return subprocess.run([sys.executable, SHELF_PY, "--db", DB, "--shelf", SHELF] + args,
                          capture_output=True, text=True, errors="replace")


def main():
    checks = []

    def chk(name, cond, **extra):
        checks.append(dict(check=name, **{"pass": bool(cond)}, **extra))

    ctx = CSH.get_ctx(DB, SHELF)
    _qs, ids, per_q, _ = G.load_frozen(ctx)

    # ---- 1. the CLI default reproduces the in-process dense_first numbers ----
    n_addr = n_match = 0
    for qid in ids[:3]:
        pq = per_q[qid]
        terms = G.row_words_from_question(pq["question"])
        for a in pq["page_addresses"][:4]:
            n_addr += 1
            want = [h["page_index"] for h in CSH.do_inside(
                ctx, a["rel"], terms, k=8, caption_channel="dense_first")["hits"]]
            cp = run_cli(["inside", a["rel"], terms, "--k", "8"])
            got = []
            for line in (cp.stdout or "").splitlines():
                s = line.strip()
                if s.startswith("p") and "|" in s:
                    try:
                        got.append(int(s.split()[0][1:]))
                    except ValueError:
                        pass
            if got == want:
                n_match += 1
    chk("cli_default_reproduces_dense_first", n_addr > 0 and n_match == n_addr,
        n_addresses=n_addr, n_matching=n_match)

    # ---- 2. note requires open ------------------------------------------
    slug = "provtest%d" % int(time.time())
    rel = next(r for r in ctx.rel_to_row if r.lower().endswith(".pdf"))
    page = 0

    r = CSH.do_note(ctx, slug, "a line with no citation tail")
    chk("note_without_tail_refused", r.get("error") == "NOTE_REFUSED_NO_CITATION",
        error=r.get("error"))

    txt = 'the row reads 1 | %s | p%d' % (rel, page)
    r = CSH.do_note(ctx, slug, txt)
    chk("note_before_open_refused", r.get("error") == "NOTE_REFUSED_PAGE_NOT_OPENED",
        error=r.get("error"))

    nd = CSH._notes_dir(ctx.root)
    notes_log = nd / ("%s_notes.jsonl" % slug)
    chk("refused_note_recorded_nothing", not notes_log.exists())

    CSH.do_open(ctx, rel, page, slug=slug)
    r = CSH.do_note(ctx, slug, txt)
    chk("note_after_open_accepted", r.get("ok") is True, error=r.get("error"))
    chk("accepted_note_recorded", notes_log.exists()
        and len(notes_log.read_text(encoding="utf-8").strip().splitlines()) == 1)

    r = CSH.do_note(ctx, slug, 'other page | %s | p%d' % (rel, page + 500))
    chk("note_for_other_page_refused", r.get("error") == "NOTE_REFUSED_PAGE_NOT_OPENED")

    # the CLI surfaces the refusal with exit 3 and records nothing
    cp = run_cli(["note", "--slug", slug, 'x | %s | p%d' % (rel, page + 501)])
    chk("cli_note_refusal_exit_3", cp.returncode == 3, rc=cp.returncode)
    chk("cli_note_refusal_message",
        "NOTE_REFUSED_PAGE_NOT_OPENED" in (cp.stderr or ""))

    # notes output itself is unchanged
    nt = CSH.do_notes(ctx, slug)
    chk("notes_output_unchanged", set(nt.keys()) == {"slug", "opened", "notes"}
        and len(nt["notes"]) == 1 and len(nt["opened"]) >= 1)

    # clean up this test's own logs
    for f in (notes_log, nd / ("%s_opened.jsonl" % slug)):
        if f.exists():
            f.unlink()

    ok = all(c["pass"] for c in checks)
    rec = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "n_checks": len(checks), "n_passed": sum(1 for c in checks if c["pass"]),
           "all_pass": ok, "checks": checks}
    (L.STATE / "c_provenance_selftest.json").write_text(json.dumps(rec, indent=1),
                                                        encoding="utf-8")
    print(json.dumps({k: v for k, v in rec.items() if k != "checks"}, indent=1))
    for c in checks:
        if not c["pass"]:
            print("FAILED: %s  %s" % (c["check"], {k: v for k, v in c.items()
                                                   if k not in ("check", "pass")}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
