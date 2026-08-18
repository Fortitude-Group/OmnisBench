# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def run_python(code: str, timeout_s: float) -> tuple[int, str]:
    """Run untrusted Python in a fresh subprocess. Returns (returncode, output).

    Isolation in v0: fresh interpreter, throwaway temp CWD, hard timeout, no shell.
    (Network egress hardening / seccomp is a v1 item; see spec risk table.)
    """
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "prog.py"
        script.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(script)],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
            return proc.returncode, (proc.stdout + proc.stderr)
        except subprocess.TimeoutExpired:
            return 124, "TIMEOUT"
