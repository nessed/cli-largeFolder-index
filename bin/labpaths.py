#!/usr/bin/env python
"""labpaths.py - the ONE place any lab script learns where anything lives.

Phase 1.1 of the grid run: thirteen hardcoded absolute paths across seven scripts
meant the lab could not be moved. Everything now derives from CORPUS_LAB_ROOT,
which itself defaults to the parent of this file's directory -- so the tree is
relocatable with no env var set at all.

Env overrides, all optional:
  CORPUS_LAB_ROOT     the corpus-lab dir            (default: parent of bin/)
  RETRIEVAL_LAB_ROOT  the umbrella dir              (default: parent of corpus-lab)
  LAB_PRIVATE         answer-key quarantine         (default: <retrieval-lab>/_private)
  HARNESS_ROOT        harness corpora + generator   (default: <retrieval-lab>/harness)
  RASHIP_ROOT         the ra-ship fixture corpus
  RUNS_ROOT           per-session result json/jsonl (default: <private>/results/03_runs)
  SCORES_ROOT         scored batteries              (default: <private>/results/04_scores)
  CANARY_MANIFEST     phase 2.3: scoring-only, NEVER defaulted. Absent = not scoring.
  HARNESS_KEYS        answer_key.json + slots       (default: <private>/harness_keys)
  CLAUDE_CMD          claude.cmd; PATH `claude` is a shell wrapper CreateProcess can't run

_first_existing() lets the same code run before and after the phase 1/2 moves:
a candidate that exists wins, otherwise the post-move location is returned so
that mkdir(parents=True) puts new output in the right place.
"""
import os
from pathlib import Path


def _env_path(name):
    v = os.environ.get(name)
    return Path(v).resolve() if v else None


def _first_existing(*cands):
    """Return the first candidate that exists; else the first candidate."""
    cands = [c for c in cands if c is not None]
    for c in cands:
        if c.exists():
            return c
    return cands[0]


# --- anchors -----------------------------------------------------------------
CORPUS_LAB = _env_path("CORPUS_LAB_ROOT") or Path(__file__).resolve().parent.parent
RETRIEVAL_LAB = _env_path("RETRIEVAL_LAB_ROOT") or CORPUS_LAB.parent

# Back-compat: pre-move, `harness` and `corpus-lab` are Desktop siblings; post-move
# they are siblings inside retrieval-lab. Both resolve to RETRIEVAL_LAB/harness.
PRIVATE = _env_path("LAB_PRIVATE") or (RETRIEVAL_LAB / "_private")
HARNESS = _env_path("HARNESS_ROOT") or _first_existing(
    RETRIEVAL_LAB / "harness",
    Path(r"C:\Users\Ali\Desktop\harness"),
)
RASHIP = _env_path("RASHIP_ROOT") or Path(r"C:\Users\Ali\Desktop\Projects\Code\ra-ship")

# --- derived dirs ------------------------------------------------------------
BIN = CORPUS_LAB / "bin"
SCRATCH = CORPUS_LAB / "99_scratch"
STATE = CORPUS_LAB / "state"
FINDINGS = CORPUS_LAB / "05_findings"
STACKS = CORPUS_LAB / "02_stacks"

RUNS = _env_path("RUNS_ROOT") or _first_existing(
    PRIVATE / "results" / "03_runs", CORPUS_LAB / "03_runs")
SCORES = _env_path("SCORES_ROOT") or _first_existing(
    PRIVATE / "results" / "04_scores", CORPUS_LAB / "04_scores")
HARNESS_KEYS = _env_path("HARNESS_KEYS") or _first_existing(
    PRIVATE / "harness_keys", HARNESS / "keys")
CANARY_DIR = PRIVATE / "canaries"

# --- files -------------------------------------------------------------------
HOOK = BIN / "hook_frontdoor.py"
SEARCH = BIN / "corpus_search.py"
ASK = BIN / "ask.py"
PLOG = BIN / "plog.py"
ANSWER_KEY = HARNESS_KEYS / "answer_key.json"
CANARY_SLOTS = HARNESS_KEYS / "canary_slots.json"
QUESTION_SAMPLE = SCORES / "question_sample.json"

CLAUDE = os.environ.get("CLAUDE_CMD", r"C:\nvm4w\nodejs\claude.cmd")


def canary_manifest(required=True):
    """Phase 2.3: the pass-1 manifest location is a secret the scripts must not
    carry. Only the scoring invocation sets CANARY_MANIFEST; a test session that
    reads this file learns the name of an env var and nothing else."""
    v = os.environ.get("CANARY_MANIFEST")
    if not v:
        if required:
            raise SystemExit(
                "CANARY_MANIFEST is not set. The canary manifest path is deliberately "
                "not hardcoded (grid-run phase 2.3). Set it for scoring invocations only.")
        return None
    return Path(v)


def rung(n):
    return HARNESS / f"corpus_{n}"


def hook_log(stack, corpus_label):
    """Phase 0.9: one log per (stack, corpus). A single shared log interleaves
    evidence from every stack and becomes a de-facto phrase list."""
    p = RUNS / "hooks" / f"{stack}__{corpus_label}.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def describe():
    return {k: str(v) for k, v in sorted(globals().items())
            if isinstance(v, Path) and not k.startswith("_")}


if __name__ == "__main__":
    import json
    d = describe()
    d["CLAUDE"] = CLAUDE
    d["CANARY_MANIFEST(env)"] = os.environ.get("CANARY_MANIFEST", "<unset>")
    print(json.dumps(d, indent=1))
