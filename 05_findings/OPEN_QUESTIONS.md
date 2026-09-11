# Open questions and next actions

Ranked. Top item first.

## Next session — in this order

1. **Fix the stream-json capture, re-run the harness battery.** (~1 h)
   Sessions answered correctly but returned plain text, so `files_opened[]` was empty and
   retrieval recall is unmeasured on the harness. Everything about answer *quality* depends
   on this. Reproduce with one call before re-running the battery.

2. **S1 policy-only A/B.** (~40 min)
   Install `CLAUDE.md` alone — no hook — and re-run the 13 canaries. This is the question
   the whole delivery debate turns on: **is telling the agent enough, or does it have to be
   forced?** Issue #47565 says telling is not enough; we have the rig to prove it either way
   on our own setup. `bin/stack.py setup --stack s1_policy` already does this.

3. **Degradation curve.** (~1.5 h) Same 20 questions at 500 / 2,000 / 5,000. The rungs are
   strict subsets with identical evidence at identical paths, so any change is corpus size
   and shadow density, not a different task.

4. **`SessionStart` incremental reconcile.** (~1 h) The refresh story is unbuilt. Hash-keyed
   so a moved file is a path update, not a silent miss. Fast-hash on size+mtime, full hash
   only on suspects.

5. **Plant the harness canaries.** (~30 min) `keys/canary_slots.json` has 20 slots;
   `generator/plant_canaries.py` is written and works. **Only 2 of the 20 slots exist below
   rung 15000** — plant at the top rung only. One slot is a scan with no text layer and is
   expected to fail without OCR; that failure is the point of the slot.

## Still genuinely unanswered

- **Same-series-across-years.** Untouched tonight. Nothing off the shelf does it; both
  round-two reports agree. Needs a hand-curated series registry keyed by content hash. This
  is days of work and the only part that does not compress with agents, because it is
  per-series judgement.
- **Sub-document addressing beyond page level.** We have `path + page_index`. We do not have
  table or bbox coordinates. `pdftotext -layout` preserves visual structure but not
  machine-readable table boundaries. Whether page-level is enough is an empirical question
  the harness can answer once #1 above is fixed.
- **Does semantic retrieval add anything over FTS5 for vague questions?** Unmeasured.
  Lexical got 92% on *findability*; trajectory questions are where it should fail. Do not
  buy the vector layer before the measurement shows the gap.
- **Cold-cache index build time.** Measured 589 s warm. Unknown cold.
- **Printed page label vs physical page index.** The index stores physical index only.
  Government reports have covers and roman-numeral front matter, so the two never match.
  The harness sidecars store both and can score this.

## Corrections to carry forward

- **#16043 does not reproduce here.** Do not cite it. The gitignore finding replaces it and
  is stronger.
- **#4486** (the ticket #16043 was closed as a duplicate of) is closed `not_planned`, has
  four bot comments and zero human triage, and is labelled `platform:macos`. The honest
  claim is *the class of defect is filed and unfixed*, never *his exact bug is filed*.
- **#12534 is the VS Code extension**, not the terminal CLI. Not sir's setup.
- **`deep-research-report (4).md` is a Bluetooth earbuds buying guide**, not a research pass.
  There are four passes, not five. Do not re-read it.

## Traps found the hard way (all cost real time tonight)

- `claude` on PATH is a shell wrapper; Python must invoke `C:\nvm4w\nodejs\claude.cmd`.
- `subprocess.run(timeout=)` kills `claude.cmd` but not its node grandchild, and
  `stderr=PIPE` then blocks forever. Use `Popen` + `taskkill /PID <pid> /T /F`, stderr to a
  file. **This silently ate 45 minutes.**
- `claude -p` waits 3 s for stdin unless given `</dev/null`.
- `--output-format stream-json` requires `--verbose`.
- **Hooks do not load from `--settings`.** Project `.claude/settings.json` only.
- `rg` in Git Bash is a Claude Code shim function using `ARGV0=`, which does not work on
  msys — it returns 0 results for everything. Real binary is under the Codex install.
- Installing the hook in a corpus root intercepts **any** Claude Code session in that
  directory, including your own working session.
