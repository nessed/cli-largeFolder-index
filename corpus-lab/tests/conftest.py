"""Keep pytest's scratch space inside the lab.

The system temp root (`%LOCALAPPDATA%\\Temp\\pytest-of-<user>`) is not always
writable for the account these runs execute under, and a test suite that cannot
start is indistinguishable from one that fails. Pointing TEMP at
`corpus-lab/99_scratch/pytest_tmp` makes

    .venv/Scripts/python.exe -m pytest corpus-lab/tests -q

work unchanged wherever the lab is checked out, which is the command every plan
and README quotes. 99_scratch is already git-ignored and is excluded from the
portable package.
"""
import os
import tempfile
from pathlib import Path

_TMP = Path(__file__).resolve().parent.parent / "99_scratch" / "pytest_tmp"
_TMP.mkdir(parents=True, exist_ok=True)
for _var in ("TMPDIR", "TEMP", "TMP"):
    os.environ[_var] = str(_TMP)
# tempfile caches the resolved directory on first use, which has already
# happened by the time a conftest is imported -- so the env vars alone are not
# enough and the cached value has to be replaced too.
tempfile.tempdir = str(_TMP)
