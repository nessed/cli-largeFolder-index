"""The Gate R3 tracer must load, record, and not hang.

Two defects were found in it the expensive way -- each cost a full clean-room
install before it showed itself:

  1. `_note` opened the log through the traced `open`, recursing into a
     non-reentrant lock it already held. The install stopped dead and produced
     no log at all, which looks exactly like "no reads happened".
  2. The tracer's source is built as a string literal, so `\\t` in it was
     interpreted when p10_trace.py was parsed. The generated sitecustomize.py
     then contained a real tab inside a string literal, so it never loaded --
     and again, no log looks like no reads.

A tracer that silently records nothing is worse than no tracer, because Gate R3
would read its empty log as a pass. So: prove it parses, prove it records, and
prove a traced process finishes.
"""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
sys.path.insert(0, str(BIN))

import p10_trace as T          # noqa: E402


def test_generated_tracer_is_valid_python():
    ast.parse(T.SITECUSTOMIZE)


def test_generated_tracer_keeps_its_escapes():
    """A real tab or newline inside the generated source is the bug from #2."""
    for line in T.SITECUSTOMIZE.splitlines():
        if "_buf.append" in line:
            assert "\\t" in line and "\\n" in line, repr(line)
            assert "\t" not in line, "a REAL tab reached the generated source"
            break
    else:
        raise AssertionError("the buffering line is gone; update this test")


def test_tracer_records_and_terminates(tmp_path):
    """The whole point: a traced process finishes, and its reads are on disk."""
    (tmp_path / "sitecustomize.py").write_text(T.SITECUSTOMIZE, encoding="utf-8")
    log = tmp_path / "reads.log"
    probe = tmp_path / "probe.txt"
    probe.write_text("hello", encoding="utf-8")

    env = dict(os.environ)
    env["P10_READS_LOG"] = str(log)
    env["PYTHONPATH"] = str(tmp_path)

    code = (
        "import os, sqlite3, io\n"
        "open(%r).read()\n"
        "list(os.scandir(%r))\n"
        "os.listdir(%r)\n"
        "sqlite3.connect(':memory:')\n"
        "print('done')\n" % (str(probe), str(tmp_path), str(tmp_path))
    )
    # a generous timeout: the deadlock this guards against hung indefinitely
    p = subprocess.run([sys.executable, "-c", code], env=env, cwd=str(tmp_path),
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "done" in p.stdout

    assert log.exists(), "the tracer produced no log at all"
    lines = [ln for ln in log.read_text(encoding="utf-8").splitlines() if "\t" in ln]
    kinds = {ln.split("\t", 1)[0] for ln in lines}
    assert "open" in kinds
    assert "scandir" in kinds or "listdir" in kinds
    assert "sqlite" in kinds
    assert any(str(probe) in ln for ln in lines), "the probe file was not recorded"


def test_tracer_is_a_noop_without_the_env_var(tmp_path):
    """No P10_READS_LOG: hooks installed, nothing written, nothing broken."""
    (tmp_path / "sitecustomize.py").write_text(T.SITECUSTOMIZE, encoding="utf-8")
    env = dict(os.environ)
    env.pop("P10_READS_LOG", None)
    env["PYTHONPATH"] = str(tmp_path)
    p = subprocess.run([sys.executable, "-c", "open(__file__ if 0 else %r).read();print('ok')"
                        % str(tmp_path / "sitecustomize.py")],
                       env=env, cwd=str(tmp_path), capture_output=True, text=True,
                       timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "ok" in p.stdout
    assert not (tmp_path / "reads.log").exists()
