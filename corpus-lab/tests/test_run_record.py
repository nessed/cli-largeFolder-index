"""Self-test for run_record.py (Plan E Phase 0.3).

Three things must hold, because three section-D promises rest on them:
  1. every section-D field is present in a started record;
  2. `finish` REFUSES when a declared output already existed at `start`
     (rule 15: nothing recorded is overwritten);
  3. `--supersedes` writes the `<old>.SUPERSEDED.md` sibling itself.

Everything runs in a temp dir. No corpus, no key, no private file is touched.
"""
import json
import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
RR = BIN / "run_record.py"


def run(*args, cwd=None):
    return subprocess.run([sys.executable, str(RR)] + [str(a) for a in args],
                          capture_output=True, text=True, cwd=cwd, timeout=300)


def test_start_writes_every_section_d_field(tmp_path):
    out = tmp_path / "rec"
    reads = tmp_path / "in.txt"
    reads.write_text("input", encoding="utf-8")
    r = run("start", "--id", "t1", "--out", out, "--cmd", "echo hi",
            "--reads", reads, "--writes", tmp_path / "out.json",
            "--rung", "corpus_500", "--models", "claude-sonnet-5",
            "--workers", "8", "--no-probe")
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads((out / "run_record.json").read_text(encoding="utf-8"))

    for k in ("id", "started_at", "finished_at", "command", "recorder_argv", "cwd",
              "git", "env_overrides", "runtime", "models", "rung", "spec",
              "inputs", "declared_outputs", "outputs_existed_at_start", "outputs",
              "notes", "conclusion", "adopted", "supersedes"):
        assert k in d, "missing top-level field %r" % k

    assert d["git"]["head"] and len(d["git"]["head"]) == 40
    assert d["git"]["branch"]
    assert isinstance(d["git"]["dirty"], bool)
    for k in ("python", "packages", "claude_exe", "workers",
              "OMP_NUM_THREADS", "PYTHONHASHSEED"):
        assert k in d["runtime"], "missing runtime field %r" % k
    for pkg in ("fastembed", "onnxruntime", "numpy", "pdfplumber"):
        assert pkg in d["runtime"]["packages"]
    assert d["models"]["embedding_model"] == "BAAI/bge-small-en-v1.5"
    assert d["models"]["embedding_model_files_sha256"]
    assert "CORPUS_LAB_ROOT" in d["env_overrides"]
    # the input's sha256 is recorded, not just its path
    assert len(d["inputs"][str(reads)]) == 64


def test_note_and_finish_close_the_record(tmp_path):
    out = tmp_path / "rec"
    w = tmp_path / "out.json"
    run("start", "--id", "t2", "--out", out, "--writes", w, "--no-probe")
    w.write_text("{}", encoding="utf-8")
    r = run("note", "t2", "--out", out, "something", "happened")
    assert r.returncode == 0, r.stdout + r.stderr
    r = run("finish", "t2", "--out", out, "--conclusion", "it worked",
            "--adopted", "yes")
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads((out / "run_record.json").read_text(encoding="utf-8"))
    assert d["finished_at"]
    assert d["conclusion"] == "it worked"
    assert d["adopted"] == "yes"
    assert len(d["notes"]) == 1
    assert len(d["outputs"][str(w)]) == 64


def test_finish_refuses_to_clobber(tmp_path):
    out = tmp_path / "rec"
    w = tmp_path / "already.json"
    w.write_text("old result", encoding="utf-8")   # exists BEFORE start
    run("start", "--id", "t3", "--out", out, "--writes", w, "--no-probe")
    r = run("finish", "t3", "--out", out)
    assert r.returncode != 0, "finish should have refused"
    assert "REFUSED" in (r.stdout + r.stderr)
    d = json.loads((out / "run_record.json").read_text(encoding="utf-8"))
    assert d["finished_at"] is None, "a refused finish must not close the record"


def test_supersedes_writes_the_sibling(tmp_path):
    out = tmp_path / "rec"
    old = tmp_path / "old_result.json"
    old.write_text("old result", encoding="utf-8")
    new = tmp_path / "new_result.json"
    run("start", "--id", "t4", "--out", out, "--writes", new, "--no-probe")
    new.write_text("new result", encoding="utf-8")
    r = run("finish", "t4", "--out", out, "--supersedes", old,
            "--conclusion", "recomputed with the corrected denominator",
            "--adopted", "yes")
    assert r.returncode == 0, r.stdout + r.stderr
    sib = tmp_path / "old_result.json.SUPERSEDED.md"
    assert sib.exists(), "the .SUPERSEDED.md sibling was not written"
    text = sib.read_text(encoding="utf-8")
    assert "t4" in text and "recomputed with the corrected denominator" in text
    assert old.read_text(encoding="utf-8") == "old result", "the old file was touched"
    d = json.loads((out / "run_record.json").read_text(encoding="utf-8"))
    assert d["supersedes"]["path"] == str(old)


def test_start_refuses_to_overwrite_a_finished_record(tmp_path):
    out = tmp_path / "rec"
    run("start", "--id", "t5", "--out", out, "--no-probe")
    run("finish", "t5", "--out", out, "--conclusion", "done")
    r = run("start", "--id", "t5b", "--out", out, "--no-probe")
    assert r.returncode != 0, "start should refuse to overwrite a finished record"
    d = json.loads((out / "run_record.json").read_text(encoding="utf-8"))
    assert d["id"] == "t5"


def test_spec_records_its_commit(tmp_path):
    """A spec inside the repo carries the commit that introduced it, so
    docs_check.py can prove the gate was written before the run started."""
    out = tmp_path / "rec"
    spec = Path(__file__).resolve().parent.parent.parent / "README.md"
    r = run("start", "--id", "t6", "--out", out, "--spec", spec, "--no-probe")
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads((out / "run_record.json").read_text(encoding="utf-8"))
    assert d["spec"]["sha256"] and len(d["spec"]["sha256"]) == 64
    assert d["spec"]["commit"], "a committed spec must resolve to a commit"
    assert d["spec"]["commit_author_date"]
