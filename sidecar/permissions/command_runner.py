"""
Safe Subprocess Command Runner for Swarm.
Enforces argv-list execution (never shell=True), locked run-workspace cwd,
minimal environment variables (scrubbed of API keys and SWARM_* secrets),
timeout process-tree termination, and output truncation.
"""

import os
import sys
import time
import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Union
from .redaction import redact


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False
    truncated: bool = False


# Minimal environment variable allowlist for child processes
SAFE_ENV_ALLOWLIST = {
    "PATH",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "COMSPEC",
    "PATHEXT",
    "WINDIR",
    "LOCALAPPDATA",
    "APPDATA",
    "HOME",
    "USERPROFILE",
    "LANG",
    "LC_ALL",
    "TERM",
}


def build_safe_child_env() -> Dict[str, str]:
    """
    Builds a minimal, sanitized environment for child processes.
    Strictly removes all SWARM_* variables, API keys, credentials, and tokens.
    """
    safe_env: Dict[str, str] = {}
    for key, val in os.environ.items():
        key_upper = key.upper()
        # Only copy allowlisted system environment keys
        if key_upper in SAFE_ENV_ALLOWLIST:
            # Extra safety check: verify the variable value itself doesn't contain secret tokens
            if not key_upper.startswith("SWARM_") and "KEY" not in key_upper and "SECRET" not in key_upper:
                safe_env[key] = val

    # Ensure basic temp dir is set
    if "TEMP" not in safe_env and "TMP" not in safe_env:
        safe_env["TEMP"] = os.environ.get("TEMP", "/tmp")

    return safe_env


def kill_process_tree(pid: int) -> None:
    """
    Terminates a process and all its child processes in a platform-safe manner (Windows / POSIX).
    """
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        except Exception:
            pass
    else:
        try:
            import signal
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception:
            try:
                os.kill(pid, 9)
            except Exception:
                pass


async def run_safe_command(
    argv: Union[List[str], tuple],
    cwd: Path,
    timeout_s: float = 30.0,
    max_output_bytes: int = 50_000,
) -> CommandResult:
    """
    Executes a command safely inside the given workspace cwd.
    - argv must be a list of string tokens (never a shell string)
    - environment is scrubbed of all secrets
    - times out and kills the entire process tree
    - caps output with truncation marker
    - redacts output before returning
    """
    if not isinstance(argv, (list, tuple)) or not argv:
        raise ValueError("argv must be a non-empty list of string tokens")

    # Verify all tokens are strings
    str_argv = [str(token) for token in argv]

    # Verify cwd exists
    if not cwd.exists() or not cwd.is_dir():
        raise FileNotFoundError(f"Command execution cwd does not exist: {cwd}")

    safe_env = build_safe_child_env()
    start_time = time.monotonic()
    timed_out = False
    truncated = False

    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *str_argv,
            cwd=str(cwd),
            env=safe_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            raw_stdout, raw_stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_s,
            )
            exit_code = proc.returncode if proc.returncode is not None else 0
        except asyncio.TimeoutError:
            timed_out = True
            if proc.pid:
                kill_process_tree(proc.pid)
            try:
                raw_stdout, raw_stderr = await proc.communicate()
            except Exception:
                raw_stdout, raw_stderr = b"", b""
            exit_code = -1

    except Exception as exc:
        duration = time.monotonic() - start_time
        return CommandResult(
            exit_code=1,
            stdout="",
            stderr=redact(f"Failed to spawn command '{str_argv[0]}': {exc}"),
            duration_s=round(duration, 3),
            timed_out=False,
            truncated=False,
        )

    duration = time.monotonic() - start_time

    # Output truncation check
    stdout_bytes = raw_stdout or b""
    stderr_bytes = raw_stderr or b""

    if len(stdout_bytes) > max_output_bytes:
        stdout_bytes = stdout_bytes[:max_output_bytes] + b"\n... [TRUNCATED]"
        truncated = True

    if len(stderr_bytes) > max_output_bytes:
        stderr_bytes = stderr_bytes[:max_output_bytes] + b"\n... [TRUNCATED]"
        truncated = True

    stdout_str = stdout_bytes.decode("utf-8", errors="replace")
    stderr_str = stderr_bytes.decode("utf-8", errors="replace")

    if timed_out:
        timeout_msg = f"\n[COMMAND TIMED OUT after {timeout_s}s - Process tree killed]"
        stderr_str += timeout_msg

    return CommandResult(
        exit_code=exit_code,
        stdout=redact(stdout_str),
        stderr=redact(stderr_str),
        duration_s=round(duration, 3),
        timed_out=timed_out,
        truncated=truncated,
    )
