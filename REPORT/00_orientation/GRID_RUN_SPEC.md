# GRID RUN — full spec, phase 0 to deliverable

You are running this unattended overnight. Ali is asleep. Do not wait for approval at any point except the HARD STOPS listed at the end. Everything else is decided here.

Work the phases in order. Each phase ends with a gate. If a gate fails: log it, write what you know, and move to the next phase that doesn't depend on it. Do not improvise past a failed gate and do not silently narrow the task to make a gate pass.

Nothing in this run regenerates any part of the harness. Determinism failed its check (6,060 of 6,064 content files reproduced), so regeneration is a risk, not a fallback. If you find yourself about to regenerate, that is a hard stop.

## Progress log — the one file that matters if the laptop sleeps

Append one JSON line to `state\progress.jsonl` after every step from phase 0 onward. Append mode only. One object per line. Never rewrite the whole file. Fields: `ts`, `phase`, `step`, `status` (started / done / failed / skipped), `note`, and any numbers produced.

Ali will `tail` this file in the morning. If it's empty, the night was wasted regardless of what else exists.

Also: `05_findings\FINDINGS_LIVE.md` gets a dated paragraph appended at the end of every phase. Written as you go, not composed at the end from memory. Night 1's write-up was composed at the end and the sleep cost the whole thing.

---

## Subagents — who does what, and what must never be delegated

You are the orchestrator. **You hold the state, the progress log, and the phase sequence for the entire night, in one continuous context.** Do not split the phases across agents and do not hand the sequence to anyone. Both research passes independently warned against splitting work by branch, and the same logic applies here: several agents each owning a phase is several chances at silent partial completion, which is the exact failure this whole run exists to measure.

**Delegate to a fresh-context subagent:**

- **Phase 3 planting.** The single best case. The planting work necessarily loads every phrase and every target path into context, and that context is an answer key. A subagent does the planting and returns only: count planted, coverage matrix path, manifest path, checksum file path, and any slots it skipped with reasons. **It never returns a phrase to you.** Run it with cwd `_private\canaries\` so its transcript lands under a project key no test session shares.
- **Phase 6.2 stream-json diagnosis**, if the probe fails. Open-ended hunt across two corpus roots for a startup-config difference. Give it the symptom, the two roots, and a 30-minute cap. It returns the cause and the fix, or "not found, here's what I ruled out." Keeps you from burning the window on a side quest — that is precisely what ate 45 minutes of night 1.
- **Phase 0 script fixes**, optionally, one subagent per independent fix, but only if you give each one the exact file and change. Do not let a subagent decide what to fix. Verify each returned diff yourself before committing.

**Never delegate:**

- **Scoring.** The scoring step runs in a process that has the manifest. Never give a subagent both a manifest and a battery result, and never let a session that has seen one battery's results touch another's.
- **The progress log.** You write every line. A subagent reporting "done" is not the same as a step being logged, and if the laptop sleeps mid-subagent, you need your own record of where you were.
- **Gate decisions.** A subagent reports; you decide whether a gate passed. A subagent that grades its own gate will pass it.
- **Anything that writes to ra-ship.**

**The trap:** subagent transcripts land in the same `.claude\projects\` key as the parent session. So a subagent that saw phrases leaves them on disk under that key. This is fine for the phase 1 move, which changes the key for batteries, but it is why phase 3 planting must run from `_private\canaries\` — a different cwd, a different key, out of reach of every test session.

**Measurement sessions are already isolated and must stay that way.** `ask.py` spawns one headless session per question. That is what makes recall mean anything — if questions shared context, question 5 would benefit from what question 2 found. Never batch questions into one session to save time.

---

## Claims discipline — the failure that wasted night 1

Night 1 found, fourteen minutes in, that ra-ship's `.gitignore` excludes every document directory. Real, deterministic, reproduces in three seconds. It then organised the entire write-up around that finding and recommended a demo built on it.

**It does not transfer.** Sir's tree is a plain folder with no git and no `.gitignore`, so on his machine `grep` and `grep --no-ignore` are the same command and the finding describes nothing. A root cause was promoted to a thesis without anyone checking whether the condition it depends on exists in the target environment.

Rules for this run:

- **Every finding names the condition it depends on.** Before it goes in the findings file, state what has to be true for it to hold: a git repo, a venv present, a file over N pages, Windows, a specific tool version. If you can't name the condition, you don't understand the finding yet.
- **Then check that condition against the target.** Target is: plain folder directory, no git, ~100 folders, ~10k files, PDF-heavy, Windows, terminal Claude Code. A finding whose condition is absent there gets logged as **fixture-specific** and is barred from the headline, the grid summary, and any recommendation. It can still appear as a note.
- **ra-ship is a fixture, not the target.** It is a git repo with a deliberate `.gitignore`, 175k of its 217k files are venvs and model caches, and 94 files are tracked. Every one of those is a property of this test tree. Results measured there are evidence about the stack, not about sir's problem, unless the harness agrees.
- **When harness and ra-ship disagree, the harness is the one that counts** and the disagreement itself is a finding worth writing down. The harness was built to simulate sir's drive — no git anywhere in it.
- **A single-cause explanation is a warning sign, not a result.** If one condition appears to explain most of a gap, go looking for what else is in play before writing it up. Night 1's own table showed `grep --no-ignore` recovering 10 of 13 canaries, which meant the index was buying two canaries over a one-flag fix — and that table was in the document underneath the headline that contradicted it.
- **Don't stop investigating because you found something clean.** The first clean root cause is when to widen, not when to write up.

---

## PHASE 0 — fix the instruments

Each one independently invalidates the numbers. None are optional.

**0.1 — git init corpus-lab first.** `git init`, commit everything as-is. Then commit after every phase. Night 1's stream-json break couldn't be diagnosed because ask.py had no history.

**0.2 — Scorer.** `run_canaries.py` scores a hit when the answer contains the bare filename (`found = exp in ans or (base in ans and len(base) > 8)`). One canary's file is `readme.md` — any answer mentioning any README in a 217k-file tree scores as a find. Require the full relative path, or at minimum the last two path segments. Then **re-score the existing night-1 results** (`03_runs\P2_s0_baseline`, `03_runs\P5_s2_canaries`) with the fixed scorer and log what 6/13 and 12/13 actually become. That number goes in the findings.

**0.3 — Corpus write protection.** Sessions run `--permission-mode bypassPermissions` with Write, Edit and unrestricted Bash on the corpus. One session editing a file permanently alters the tree for every later stack and nothing detects it. Pass `--disallowedTools "Write,Edit,NotebookEdit"` on every measurement session. Add a checksum manifest of every planted file, computed before and after every battery. Battery fails loudly if any hash moved.

**0.4 — Baseline installs nothing.** `stack.py setup --stack s0_baseline` currently writes CLAUDE.md, so night 1's S0 and S2 differed by two things. Baseline means untouched corpus, no CLAUDE.md, no `.claude/settings.json`.

**0.5 — Policy-only asserts no hook.** `s1_policy` writes CLAUDE.md and must assert `.claude/settings.json` is absent before running. Abort if present. Otherwise a leftover install silently turns the telling-vs-forcing test into a forcing test.

**0.6 — Timing.** `wall_s` uses `time.time()` and counts laptop sleep — that's the 6.5-hour canary. Switch to `time.monotonic()`. Record a `suspended: true` flag when wall time exceeds summed inter-event time by more than 60 s. Suspended sessions are excluded from timing stats and reported separately.

**0.7 — Cost.** Timed-out sessions report `cost_usd: null` and get dropped from the sum, which biases every total toward whichever stack flailed more. Report cost as total plus explicit n-of-m. Never compare two totals with different n without saying so.

**0.8 — stack.py state and backups.** State file is written last, so a crash mid-install leaves a live policy or hook with no record. Write state first, then mutate. Backups are named by basename in one shared scratch dir, so two corpora with a CLAUDE.md collide and teardown restores the wrong bytes into the wrong tree. Key backups by corpus.

**0.9 — Hook log per run.** `hook_frontdoor.py` appends to one shared file with no run separation. Evidence from every stack interleaves and the file becomes a phrase list. One log per (stack, corpus), path via env var.

**0.10 — Never skip silently.** `ask.py` skips any (stack, corpus, qid) that already has a result unless `--force`. Change the skip to print in red and count skipped questions in the battery summary. A reused label returning stale numbers must be impossible to miss.

**Gate 0:** all ten done, committed, and re-scored night-1 numbers logged.

---

## PHASE 1 — tidy and move

**1.1 — Fix hardcoded absolute paths before moving anything.** Thirteen of them:
- `bin\stack.py:19` and `:105`
- `bin\run_canaries.py:11`, `:12`, `:13`
- `bin\run_harness.py:20`, `:21`
- `bin\hook_frontdoor.py:16`, `:18`
- `bin\ask.py:14`
- `bin\corpus_search.py:16`
- `harness\generator\agent_layer.py:27`, `:30` and `sediment.py:28`

Derive everything from one `CORPUS_LAB_ROOT` env var with a sensible default. Verify each script runs from a scratch cwd with no path errors.

**1.2 — Consolidate.** One parent folder, `C:\Users\Ali\Desktop\retrieval-lab\`, containing `corpus-lab\`, `harness\`, and a `_private\` subfolder (see phase 2). Leave ra-ship exactly where it is — it's the corpus under test and its git state is the baseline.

**1.3 — Quarantine agent-harness.** `Desktop\agent-harness\` is an unrelated repo whose `install.py` merges SessionStart / UserPromptSubmit / PreToolUse / Stop hooks into any target's `.claude/settings.json`. Move it to `Desktop\_unrelated\agent-harness\`. Never run it near a corpus.

**1.4 — Confirm the project key changed.** After moving, the `.claude\projects\` dir name for the harness cwd must be new. This is intentional: the old project dir holds transcripts containing canary phrases and their planted paths, and a fresh key puts them out of a test session's reach.

**1.5 — Generator venv.** `harness\generator\.venv` has absolute paths baked into `pyvenv.cfg` and console-script shebangs. Don't fix it. It only matters for regeneration, which is banned.

**Gate 1:** every script runs from the new location. Old transcripts not reachable from the new cwd. Committed.

---

## PHASE 2 — close every route to the answers

The test must have no way to read the canaries or the answer key. Close each of these, then prove it.

**2.1 — Move `harness\keys\` out of the harness tree** to `retrieval-lab\_private\harness_keys\`. Sessions run with cwd inside a rung and `answer_key.json` is currently one `..` up, denied by nothing.

**2.2 — Move the manifest, companion and backups** to `retrieval-lab\_private\canaries\`. The companion md is the worst leak — it's the full answer key in prose with `file:///` links to every planted path.

**2.3 — Scoring script.** `run_canaries.py` hardcodes the manifest path, so reading the script hands over the key's location, and it sits in the same `bin\` sessions are told to use. Move the manifest path to an env var `CANARY_MANIFEST` that only the scoring invocation sets.

**2.4 — Results and archive.** `04_scores\*.json` and `03_runs\P*\*.json` contain phrase, expected path and answer for all 13 ra-ship canaries. `03_runs\_session_archive\` holds 57 transcripts with the same. All of it lives inside the directory the hook actively points the agent at. Move `04_scores\` and `03_runs\` to `retrieval-lab\_private\results\`. Scripts write there via the env var; test sessions never get a name for it.

**2.5 — Backstop deny.** In every stack's `.claude/settings.json` (including a minimal one for S0, containing only this deny and nothing else) add:
```
"permissions": { "deny": ["Read(**/_private/**)", "Bash(*_private*)", "Bash(*canary*)", "Bash(*answer_key*)"] }
```

**2.6 — Prove it.** Start a session rooted at rung 15000 and at ra-ship. Try: Read on each moved file by absolute path, `cat` via Bash, `..` traversal to keys, and a corpus_search query for a known phrase. Every attempt must be refused or return nothing. Log the refusals verbatim in FINDINGS_LIVE.

**Gate 2:** all six closed with evidence. If any attempt in 2.6 succeeds, fix it before proceeding — this gate does not get skipped.

---

## PHASE 3 — plant pass-2 canaries, rung 15000 only

**3.1 — Fix `plant_canaries.py` first.** Three bugs:
- `plant_text`: the newline condition is inverted. A file that doesn't end in `\n` gets the phrase glued onto the end of its last line. Always write `\n{phrase}\n` after `rstrip("\n")`.
- JSON: `json.dumps(obj, indent=1)` re-serialises the whole file so every line diffs. Read the file, detect its existing indent, append the canary key with the same indent, and confirm the diff is one hunk.
- `.html` is not in `TEXTY`. Add it.

Also: `--restore` only copies backups back and never deletes created files. Record in the manifest which rows are created vs injected so unplanting created files can be done by hand.

**3.2 — Plant at rung 15000 only.** Rungs are independent hard copies, not linked. 500, 2000 and 5000 stay untouched.

**3.3 — Phrases.** 15–20. Grep the rung for each before planting, confirm zero hits. No shared token. **No shared structural shape** — pass 1 ended with 11 of 13 matching `<prefix>-<8hex>-<6digits>`, so one regex swept the set. Mix forms: a plausible-looking SRO number, a fake series ID, a person's name that doesn't exist, a mis-typed agency acronym, a numeric value with a specific unit, a lowercase slug. If any subset shares a shape, say so in the companion.

**3.4 — Placement.** Use `canary_slots.json` as the starting list. Mandatory coverage: at least one deep in a 200+ page PDF (record physical page index AND printed page label separately — they differ), one in a DOCX, one in an XLSX cell, one in a CSV row, one in a JSON, one in a markdown README that is *stale* (describes a folder that no longer looks like that), one inside a zip, one at depth 6+, one at the top level, one in a folder with 300+ files, one in a file whose name lies about its content. Two canaries must be in files that are near-duplicates of each other so only one copy has it.

**3.5 — Created files must match their neighbours.** Same extension, plausible name, plausible size, nothing in the filename naming the experiment. Set mtime to match neighbours. A file found for being the odd one out proves nothing.

**3.6 — Back up every touched file** to `_private\canaries\plant_backups_pass2\`, record and restore mtimes.

**3.7 — Manifest** at `_private\canaries\canary_manifest_pass2.csv`: phrase, absolute path, rung, cases covered, injected-or-created, backup path, original mtime, page_index, printed_page_label, sha256_after_plant, blank pass_fail. Companion md alongside with the coverage matrix.

**3.8 — Delegate this whole phase to a fresh-context subagent, run with cwd `_private\canaries\`.** Two reasons: the work loads every phrase and target path into context, and that context is an answer key; and its transcript lands under a project key no test session shares.

Brief it with: the rung path, the slot list, the coverage requirements in 3.4, the phrase rules in 3.3, the backup and manifest destinations, and the three script bugs in 3.1 to fix first.

**Its return contract — and it returns nothing else:** count planted, manifest path, companion path, backup dir path, checksum file path, the coverage matrix as a table of case-covered / not-covered, and any slots skipped with reasons. **No phrases. No target paths.** If it returns a phrase, discard the message and note it in FINDINGS_LIVE as a leak that has to be handled before phase 7 — your own context is now contaminated and the batteries you orchestrate are reading from a session that knows the answers.

You verify its work by checking that the manifest exists, has the expected row count, and that every `sha256_after_plant` is populated — not by reading the phrases.

**Gate 3:** coverage matrix logged, naming what got a canary and what didn't. Checksums of all planted files recorded.

---

## PHASE 4 — build the indexes once

The databases were deleted in cleanup. Build once, up front, never between stacks — rebuilding mid-run is changing the instrument.

**4.1** — `index_build.py` against rung 15000 → `02_stacks\s2_fts5\harness_15000.db`.
**4.2** — `index_build.py` against ra-ship → `02_stacks\s2_fts5\raship.db` (~10 min).
**4.3** — Log for each: discovered / indexed_ok / failed / unsupported / excluded / pages / seconds / bytes. Coverage identity must close: discovered = indexed + failed + excluded + unsupported.
**4.4** — Confirm that a corpus_search for one pass-2 phrase and one pass-1 phrase returns the right file and page. If it doesn't, the index is broken, not the stack — fix before continuing.

**Gate 4:** both identities close, both smoke queries hit.

---

## PHASE 5 — the stacks (defined; do not re-derive)

Read `01_reports\TOOL_MATRIX.md` for reference. Do not re-read the four research reports; the list below is the distillation and it is final for this run.

**Rules that apply to every stack:**
- pip is allowed, **inside `retrieval-lab\.venv` only**, never system python. Create it once with `python -m venv`. Log every install with its output.
- No GPU, no Docker, no WSL, no cargo. Anything that needs them is dead on this machine.
- **Install gate:** install → run ONE canary through `ask.py` → confirm the result parses and `files_opened[]` is non-empty. Only then run the battery. A stack that won't install gets a grid cell containing the exact error output, and the run moves on. An install failure costs ten minutes, not the night.
- Every stack gets a unique `--stack` label. Never reuse.

**S0 — baseline.** Stock Claude Code, nothing installed, no CLAUDE.md, no hook. `.claude/settings.json` contains only the phase-2 backstop deny. Note in findings that the machine's global settings set effortLevel high, load the i-have-adhd plugin skill, and register a herdr hook — so "stock" means "stock on this machine," and say so.

**S1 — policy only.** CLAUDE.md tells the agent the index exists at `corpus_search.py` and to use it before Grep/Glob. No hook. Asserts no `settings.json` hook block exists before running. This answers whether *telling* is enough or *forcing* is required — highest-value unmeasured question from round two.

**S2 — index + front-door hook.** Already built. FTS5 page index, PreToolUse deny on Grep/Glob/Bash-crawls, redirect to `corpus_search.py`. The thing night 1 measured.

**S3 — hybrid: FTS5 + local embeddings, LanceDB.** Round-one GPT's preferred fully-local build, minus Docling (pdftotext instead — full-tree layout extraction is ruled out). `pip install lancedb fastembed`. Embed every page from the FTS5 index with `BAAI/bge-small-en-v1.5` via fastembed (ONNX, CPU, no torch download). Store in LanceDB with the same page rows; LanceDB does BM25 + vector + hybrid natively. Front door is a modified `corpus_search.py` that runs hybrid with RRF. Same hook as S2. **This is the only stack that can answer a vague question where the words don't match the table.** Record embedding build time as the setup-cost cell — that's a scored dimension.

**S4 — pdf-mcp.** Off-the-shelf comparison. `pip install pdf-mcp` then `claude mcp add pdf-mcp -- pdf-mcp` in the corpus. Use its `pdf_corpus_warm` on the tree, then let the agent use `pdf_corpus_search` / `pdf_read_pages`. Same PreToolUse deny on Grep/Glob/Bash-crawls so it has to use the MCP. **Known limits, record them in the cell:** PDF-only so non-PDF canaries will miss by design, and #33106 means the hook can't deny MCP calls, only built-ins. Warm time is the setup-cost cell. This tells us whether writing our own was worth it.

**S5 — Recoll (stretch, run only if S0–S4 are all done and it's before 05:00).** Windows installer, not pip. Report 5 rates it highly; its trap is that files that failed extraction are never retried without `recollindex -k`, so run that and record the count. Front door is `recollq -a`. If the installer needs a click, it's dead — log it and skip.

**Dead, do not attempt:** ripgrep-all (no cargo), ColQwen / visual page retrieval (no GPU), Qdrant / Elasticsearch / Datashare / Aleph / paperless-ngx (Docker), full-tree Docling (ruled out on silent-corruption risk and build time), Marker (licence), GraphRAG (cost).

**S3 and S4 are the only stacks that can answer harness questions where the answer is a table and the question is vague.** If both fail the install gate, the night still produces S0/S1/S2 on both trees, which is more than night 1 did.

---

## PHASE 6 — probe before any battery

**6.1 — stream-json probe, both trees.** Night 1's break was NOT the `--verbose` flag — it was already there. Same script produced valid stream-json on ra-ship at 01:05 and 01:43 and plain prose on corpus_500 at 01:34. It correlates with the corpus root and is undiagnosed. Run:
```
python bin\ask.py --phase T_probe --stack probe --corpus "<rung 15000>" --corpus-label h15k --qid verbose_check --question "Read the file <a known top-level file> and reply with only its first line." --max-turns 3 --timeout 90 --force
```
then identical against ra-ship. Pass: `.jsonl` starts with `{`, `.json` shows `n_files_opened >= 1`, `answer_text` non-null.

**6.2 — If the harness probe fails and ra-ship passes:** you have isolated it to the corpus root. **Delegate the hunt to a fresh-context subagent** — this is an open-ended search with a one-line answer, and doing it inline is how night 1 lost 45 minutes.

Brief it with: the symptom (same script, same flags, valid stream-json on one root, plain prose on the other, returncode 0, empty stderr), both root paths, the two probe result files, and a **30-minute hard cap**. Tell it to compare anything Claude Code reads at startup — `.claude\` at any depth, `CLAUDE.md`, `.mcp.json`, `settings.local.json`, `.git` presence, any `commands\` dir — and to check whether the invocation differs in cwd handling. Note that one night-1 answer said PDF extraction was "blocked by permissions," which should be impossible under `bypassPermissions`, so something about how that invocation launched differed from what `ask.py` does now.

It returns: cause and fix, or "not found — here's what I ruled out." Nothing else.

**Do not run a harness battery that can't record what it opened.** If the cap expires with no fix, run ra-ship batteries first and come back to harness at the end.

**6.3 — Memory check.** List every `memory\` dir under `~\.claude\projects\` for the two test project keys. Must be empty or absent. Record.

**Gate 6:** both probes pass, memory dirs clean. Delete `03_runs\T_probe` afterwards so it doesn't get scored.

---

## PHASE 7 — run the grid

**7.1 — Order.** Harness rung 15000 first, all stacks. Then ra-ship, all stacks. If the laptop dies, the harness number is the one that matters — it's the tree that matches the real target.

**7.2 — Per stack, per tree:**
1. `stack.py teardown` (even if nothing is installed)
2. Verify planted-file checksums match phase 3 / pass 1 records. **Verify, don't restore** — restore only if verification fails, and log that it failed.
3. Confirm no stray `CLAUDE.md` or hook block in `.claude/settings.json` from a previous stack
4. Memory dir check
5. `stack.py setup --stack <label>`
6. Install gate (one canary)
7. Canary battery — all pass-2 canaries on harness, all 13 pass-1 on ra-ship
8. Harness question battery — the frozen 20 from `question_sample.json`, harness only
9. Teardown
10. Checksums again. Memory dir again.
11. Append summary line to progress.jsonl

**7.3 — Scoring.** Fixed scorer from phase 0. Retrieval scored separately from answers — `files_opened[]` vs the expected path, not just answer text. For harness questions, score against `answer_key.json` at page and table level where the key has it.

**7.4 — sig-328120.** Lives under `site-packages`, which `index_build.py` excludes by design. Every index-based stack has a hard ceiling there while grep-based S0 can find it. Score it as a separate row — "excluded by design" — not in the headline, on every stack.

**7.5 — Time budget.** Each battery gets a wall-clock cap of 45 minutes. If it's not done, kill it, log partial results as partial, move on. A partial grid with honest cells beats a full grid that never finishes.

**7.6 — No `--force` in battery commands.** Fresh labels only.

---

## PHASE 8 — the deliverable

`05_findings\GRID.md`. A table:

| stack | harness-15k canary recall | harness-15k question recall | ra-ship canary recall | cost (n/m) | tool calls | wall-clock (excl. suspended) | setup time | notes |

Every cell has a number, "not run — <reason>", or "install failed — <error>". No empty cells.

**A required section, above the per-stack paragraphs: "Fixture-specific — does not transfer."** Every finding whose condition doesn't hold on sir's setup goes here, with the condition named. If this section is empty, say so explicitly — an empty section is a claim that everything measured transfers, and that claim should be made on purpose rather than by omission.

**Every claim in the per-stack paragraphs carries its condition.** Not "the index finds 3x more" but "the index finds 3x more on trees where binary formats hold the answer" — because the first version is what produced night 1's write-up.

Below the table, per stack, one paragraph: what it did on vague questions specifically, since that's the failure sir actually has. Then one paragraph on S1 vs S2 — did telling work, or did it need forcing.

**No recommendation section.** Ali reads the grid and decides. If you have an opinion, put it in a section titled "What I'd look at first" with the evidence, and keep it to five lines.

Then update `RESUME.md` so a fresh session knows what exists and what's next. Commit.

---

## HARD STOPS — the only reasons to halt and wait

1. Anything wants to write to ra-ship outside the documented `stack.py` install (CLAUDE.md and `.claude/settings.json` only).
2. Anything is about to regenerate any part of the harness.
3. Phase 2's proof (2.6) shows a test session can reach an answer key and you can't close it.
4. A planted-file checksum fails verification and restore also fails.
5. A subagent returns canary phrases or target paths to you despite its return contract, and you have already started phase 7. Before phase 7 it's recoverable — note it and continue. After batteries have started, the orchestrator's context knows the answers and the remaining cells are suspect.

Everything else: log it, decide, keep moving.
