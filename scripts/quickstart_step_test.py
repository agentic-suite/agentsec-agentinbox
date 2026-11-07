#!/usr/bin/env python3
"""Replay the quickstart exactly (M23 item 23.1): install → init → ask → answer → verify.

The answer step runs through a pseudo-terminal because the terminal channel is interactive by
design; a scripted answer must never approve. Exit 0 only when the record is approved in < 300 s.
"""

from __future__ import annotations

import getpass
import json
import os
import pty
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PY = sys.executable
COMMAND = [PY, "-m", "agentinbox"]
LIMIT_SECONDS = 300.0


def run(args: list[str], *, home: Path, timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*COMMAND, "--home", str(home), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def wait_for_ask(home: Path, deadline: float) -> str:
    while time.monotonic() < deadline:
        listing = run(["--json", "inbox"], home=home)
        if listing.returncode == 5 and listing.stdout.strip():
            asks = json.loads(listing.stdout)
            if asks:
                return str(asks[0]["ask_id"])
        time.sleep(0.1)
    raise RuntimeError("no pending ask appeared")


def answer_interactively(home: Path, ask_id: str) -> subprocess.CompletedProcess[str]:
    master, slave = pty.openpty()
    try:
        process = subprocess.Popen(
            [*COMMAND, "--home", str(home), "answer", ask_id],
            stdin=slave,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        os.close(slave)
        slave = -1
        os.write(master, b"a\n")
        time.sleep(0.2)
        os.write(master, b"run_command\n")
        stdout, stderr = process.communicate(timeout=30)
        return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
    finally:
        if slave >= 0:
            os.close(slave)
        os.close(master)


def main() -> int:
    started = time.monotonic()
    home = Path(tempfile.mkdtemp(prefix="agentinbox-quickstart-"))
    try:
        init = run(["init"], home=home)
        if init.returncode != 0:
            print(init.stdout, init.stderr, file=sys.stderr)
            return 1

        config = home / "config.toml"
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                'terminal = ["alice"]', f'terminal = ["{getpass.getuser()}"]'
            ),
            encoding="utf-8",
        )
        doctor = run(["doctor"], home=home)
        if doctor.returncode != 0:
            print(doctor.stdout, doctor.stderr, file=sys.stderr)
            return 1

        ask = subprocess.Popen(
            [
                *COMMAND,
                "--home",
                str(home),
                "ask",
                "--exec",
                "echo hello",
                "--timeout",
                "120",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        ask_id = wait_for_ask(home, deadline=time.monotonic() + 20)
        answered = answer_interactively(home, ask_id)
        ask_stdout, ask_stderr = ask.communicate(timeout=30)

        problems = []
        if answered.returncode != 0:
            problems.append(f"answer exit {answered.returncode}: {answered.stderr}")
        if ask.returncode != 0:
            problems.append(f"ask exit {ask.returncode}: {ask_stderr}")
        if "hello" not in ask_stdout:
            problems.append("the approved command did not run")
        if run(["verify-log"], home=home).returncode != 0:
            problems.append("verify-log failed")
        report = run(["report", "--json"], home=home)
        if report.returncode != 0 or json.loads(report.stdout)["total_asks"] != 1:
            problems.append("report did not see the ask")
        elapsed = time.monotonic() - started
        if elapsed >= LIMIT_SECONDS:
            problems.append(f"took {elapsed:.1f}s (limit {LIMIT_SECONDS:.0f}s)")

        if problems:
            print("quickstart FAILED:", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 1
        print(f"quickstart ok: first approval recorded in {elapsed:.1f}s")
        return 0
    finally:
        shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
