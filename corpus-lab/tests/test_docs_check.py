"""Self-test for docs_check.py (Plan E Phase 0.4).

Gate D is docs_check's exit code, so a docs_check that cannot detect a defect is
worse than no gate at all -- it would certify a broken record as sound. Each test
builds a temp tree with exactly ONE deliberate omission and asserts the run fails
*and names that reason*. The last test builds a clean tree and asserts it passes,
so the suite also proves the checks are not simply always-fail.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
DC = BIN / "docs_check.py"

HEADINGS = ["Purpose", "Method", "Inputs", "Outputs", "Gate", "Result",
            "Adopted?", "Run record", "What this does not show"]


def run(root, snapshot=None, since=0.0):
    cmd = [sys.executable, str(DC), "--root", str(root), "--since", str(since)]
    if snapshot:
        cmd += ["--snapshot", str(snapshot)]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


def good_record(finished=True, spec=None):
    d = {
        "id": "x", "started_at": "2026-09-16T01:00:00",
        "finished_at": "2026-09-16T02:00:00" if finished else None,
        "command": "echo", "cwd": ".",
        "git": {"head": "a" * 40, "branch": "b", "dirty": False},
        "env_overrides": {"CORPUS_LAB_ROOT": None},
        "runtime": {"python": "3.11.5", "packages": {}, "workers": 8,
                    "OMP_NUM_THREADS": "4", "PYTHONHASHSEED": "0"},
        "models": {}, "inputs": {}, "declared_outputs": [], "outputs": {},
        "notes": [], "conclusion": "ok", "adopted": "yes", "supersedes": None,
    }
    if spec:
        d["spec"] = spec
    return d


def good_readme():
    return "\n".join("## %s\n\nplaceholder\n" % h for h in HEADINGS)


def build_tree(tmp_path, record=None, readme=None, snapshot_rows=(),
               state_files=(), scorer=None):
    """A minimal tree that passes every check, then mutated by the caller."""
    root = tmp_path / "tree"
    (root / "corpus-lab" / "state").mkdir(parents=True)
    (root / "corpus-lab" / "experiments" / "e1").mkdir(parents=True)
    (root / "_private" / "results" / "04_scores").mkdir(parents=True)

    rec_dir = root / "corpus-lab" / "state" / "rec"
    rec_dir.mkdir()
    (rec_dir / "run_record.json").write_text(
        json.dumps(record if record is not None else good_record()),
        encoding="utf-8")

    (root / "corpus-lab" / "experiments" / "e1" / "README.md").write_text(
        readme if readme is not None else good_readme(), encoding="utf-8")

    snap = root / "corpus-lab" / "state" / "phase10_preexisting_files.txt"
    snap.write_text("\n".join(snapshot_rows) + "\n", encoding="utf-8")

    for rel in state_files:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")

    if scorer is not None:
        (root / "corpus-lab" / "state" /
         "c_live_battery_v3__T.json").write_text(json.dumps(scorer),
                                                 encoding="utf-8")
    return root, snap


def test_clean_tree_passes(tmp_path):
    root, snap = build_tree(
        tmp_path, scorer={"scorer_version": "v3", "key_sha256": "d" * 64})
    r = run(root, snap)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "GATE D: PASS" in r.stdout


def test_A_missing_field_is_named(tmp_path):
    rec = good_record()
    del rec["env_overrides"]
    root, snap = build_tree(tmp_path, record=rec)
    r = run(root, snap)
    assert r.returncode == 1
    assert "missing section-D field" in r.stdout
    assert "env_overrides" in r.stdout


def test_A_unfinished_record_is_named(tmp_path):
    root, snap = build_tree(tmp_path, record=good_record(finished=False))
    r = run(root, snap)
    assert r.returncode == 1
    assert "never finished" in r.stdout


def test_A_missing_runtime_field_is_named(tmp_path):
    rec = good_record()
    del rec["runtime"]["PYTHONHASHSEED"]
    root, snap = build_tree(tmp_path, record=rec)
    r = run(root, snap)
    assert r.returncode == 1
    assert "runtime.PYTHONHASHSEED" in r.stdout


def test_B_missing_readme_heading_is_named(tmp_path):
    readme = "\n".join("## %s\n\nx\n" % h for h in HEADINGS if h != "Gate")
    root, snap = build_tree(tmp_path, readme=readme)
    r = run(root, snap)
    assert r.returncode == 1
    assert "missing the fixed heading" in r.stdout
    assert "Gate" in r.stdout


def test_B_missing_readme_entirely_is_named(tmp_path):
    root, snap = build_tree(tmp_path)
    (root / "corpus-lab" / "experiments" / "e1" / "README.md").unlink()
    r = run(root, snap)
    assert r.returncode == 1
    assert "has no README.md" in r.stdout


def test_C_spec_committed_after_the_run_is_named(tmp_path):
    """The mechanism behind 'gates are written before numbers exist'."""
    rec = good_record(spec={"path": "corpus-lab/state/gate_spec.md",
                            "sha256": "c" * 64,
                            "commit": "f" * 40,
                            "commit_author_date": "2026-09-16T05:00:00"})
    root, snap = build_tree(tmp_path, record=rec)   # run started 01:00
    r = run(root, snap)
    assert r.returncode == 1
    assert "was not pre-registered" in r.stdout


def test_C_spec_committed_before_the_run_passes(tmp_path):
    rec = good_record(spec={"path": "corpus-lab/state/gate_spec.md",
                            "sha256": "c" * 64,
                            "commit": "f" * 40,
                            "commit_author_date": "2026-09-15T22:00:00"})
    root, snap = build_tree(
        tmp_path, record=rec,
        scorer={"scorer_version": "v3", "key_sha256": "d" * 64})
    r = run(root, snap)
    assert r.returncode == 0, r.stdout + r.stderr


def test_D_overwriting_a_preexisting_result_is_named(tmp_path):
    rel = "corpus-lab/state/c_old_result.json"
    root, snap = build_tree(tmp_path, snapshot_rows=[rel], state_files=[rel])
    r = run(root, snap)
    assert r.returncode == 1
    assert "already existed before this run" in r.stdout
    assert "c_old_result.json" in r.stdout


def test_D_append_by_design_files_are_exempt(tmp_path):
    rel = "corpus-lab/state/progress.jsonl"
    root, snap = build_tree(
        tmp_path, snapshot_rows=[rel], state_files=[rel],
        scorer={"scorer_version": "v3", "key_sha256": "d" * 64})
    r = run(root, snap)
    assert r.returncode == 0, r.stdout + r.stderr


def test_D_missing_snapshot_is_named(tmp_path):
    root, snap = build_tree(tmp_path)
    snap.unlink()
    r = run(root, snap)
    assert r.returncode == 1
    assert "snapshot is missing" in r.stdout


def test_E_scorer_without_version_is_named(tmp_path):
    root, snap = build_tree(tmp_path, scorer={"key_sha256": "d" * 64})
    r = run(root, snap)
    assert r.returncode == 1
    assert "does not name its scorer_version" in r.stdout


def test_E_scorer_without_key_sha_is_named(tmp_path):
    root, snap = build_tree(tmp_path, scorer={"scorer_version": "v3"})
    r = run(root, snap)
    assert r.returncode == 1
    assert "does not name its key_sha256" in r.stdout


def test_since_excludes_files_from_before_the_run(tmp_path):
    """A defect in a record written BEFORE this run is not this run's failure."""
    rec = good_record(finished=False)
    root, snap = build_tree(tmp_path, record=rec)
    future = time.time() + 3600
    r = run(root, snap, since=future)
    assert r.returncode == 0, r.stdout + r.stderr
