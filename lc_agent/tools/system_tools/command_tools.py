import os
import platform
import re
import subprocess
import threading
import time
from typing import Annotated

from lc_agent.tools.registry import tool
from lc_agent.tools.system_tools._config import get_command_config


# ---------------------------------------------------------------------------
# Background process manager
# ---------------------------------------------------------------------------

class _ProcessEntry:
    __slots__ = ("proc", "stdout_buf", "stderr_buf", "start_time", "command", "_lock")

    def __init__(self, proc: subprocess.Popen, command: str):
        self.proc = proc
        self.stdout_buf: list[str] = []
        self.stderr_buf: list[str] = []
        self.start_time = time.time()
        self.command = command
        self._lock = threading.Lock()

    def append_stdout(self, line: str):
        with self._lock:
            self.stdout_buf.append(line)

    def append_stderr(self, line: str):
        with self._lock:
            self.stderr_buf.append(line)

    def get_output(self, offset: int = 0) -> tuple[str, int]:
        """Return buffered output from offset. Returns (text, new_offset)."""
        with self._lock:
            all_lines = self.stdout_buf[offset:]
            new_offset = len(self.stdout_buf)
        return "".join(all_lines), new_offset

    def get_full_output(self) -> str:
        with self._lock:
            stdout = "".join(self.stdout_buf)
            stderr = "".join(self.stderr_buf)
        parts = []
        if stdout:
            parts.append(stdout)
        if stderr:
            parts.append(f"[stderr]\n{stderr}")
        return "\n".join(parts) if parts else "(no output)"


_processes: dict[int, _ProcessEntry] = {}
_MAX_BUFFER_LINES = 5000
_MAX_BG_PROCESSES = 10


def _reader_thread(entry: _ProcessEntry, stream, append_fn):
    """Background thread that reads lines from a process stream."""
    buffer_full = False
    try:
        for line in iter(stream.readline, ""):
            if not line:
                break
            if not buffer_full:
                append_fn(line)
                with entry._lock:
                    if len(entry.stdout_buf) + len(entry.stderr_buf) > _MAX_BUFFER_LINES:
                        buffer_full = True
                        append_fn("[output buffer full, further output discarded]\n")
    except (ValueError, OSError):
        pass
    finally:
        try:
            stream.close()
        except Exception:
            pass


def _reap_exited_processes():
    """Clean up entries for processes that have exited."""
    to_remove = []
    for pid, entry in _processes.items():
        if entry.proc.poll() is not None:
            try:
                entry.proc.wait(timeout=0)
            except Exception:
                pass
            to_remove.append(pid)
    for pid in to_remove:
        del _processes[pid]

def _get_subprocess_env() -> dict[str, str]:
    """Get environment dict that forces unbuffered output for common runtimes."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


_SHELL_SEPARATORS = re.compile(r"[;&|]|\|\||&&")
_SUBCOMMAND_PATTERN = re.compile(r"\$\(([^)]+)\)|`([^`]+)`")


def _extract_commands(command: str) -> list[str]:
    """Extract all command names from a potentially compound command string."""
    commands: list[str] = []

    for sub_match in _SUBCOMMAND_PATTERN.finditer(command):
        inner = sub_match.group(1) or sub_match.group(2)
        commands.extend(_extract_commands(inner))

    parts = _SHELL_SEPARATORS.split(command)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        for sub_match in _SUBCOMMAND_PATTERN.finditer(part):
            inner = sub_match.group(1) or sub_match.group(2)
            commands.extend(_extract_commands(inner))
        clean = _SUBCOMMAND_PATTERN.sub("", part).strip()
        if clean:
            cmd_name = clean.split()[0] if clean.split() else ""
            if cmd_name:
                commands.append(cmd_name)
    return commands


def _validate_command(command: str) -> str | None:
    """Check command against blocklist. Returns error message or None if allowed."""
    config = get_command_config()
    blocked = config.get("blocked_commands", [])
    if not blocked:
        return None

    extracted = _extract_commands(command)
    for cmd in extracted:
        cmd_lower = cmd.lower()
        for blocked_cmd in blocked:
            if cmd_lower == blocked_cmd.lower() or cmd_lower.endswith(f"/{blocked_cmd.lower()}") or cmd_lower.endswith(f"\\{blocked_cmd.lower()}"):
                return f"Command '{cmd}' is blocked by security configuration"
    return None


def _get_shell() -> list[str]:
    """Get the shell command prefix from config or system default."""
    config = get_command_config()
    shell = config.get("default_shell", "")

    if not shell:
        if platform.system() == "Windows":
            shell = "powershell"
        else:
            shell = os.environ.get("SHELL", "/bin/sh")

    shell_lower = shell.lower()
    if "powershell" in shell_lower or "pwsh" in shell_lower:
        return [shell, "-NoProfile", "-Command"]
    elif "cmd" in shell_lower:
        return [shell, "/c"]
    elif "bash" in shell_lower or "zsh" in shell_lower:
        return [shell, "-l", "-c"]
    else:
        return [shell, "-c"]


@tool(group="command", group_description="命令执行")
def run_command(
    command: Annotated[str, "Command string to execute"],
    max_run_ms: Annotated[
        int,
        "Maximum run time in milliseconds before force-killing the process (default 30000 = 30s)",
    ] = 30000,
    working_directory: Annotated[
        str | None,
        "Working directory for the command; defaults to the project root (project mode) or server working directory",
    ] = None,
) -> str:
    """
    You must first verify that your command is safe — never execute dangerous commands.
    Generate commands according to the user’s operating system — do not execute Linux-syntax commands on Windows.
    
    Execute a one-shot command and wait for it to finish; returns the full combined output. The process is force-killed on timeout.

    Uses PowerShell (-NoProfile -Command) on Windows and $SHELL (default: /bin/sh) on Linux/macOS.
    WARNING (Windows PowerShell 5.1): '&&' is not supported. Chain dependent commands with 'cmd1; if ($?) { cmd2 }' instead.

    Use for:  pip install, git status, build scripts, or any command that exits on its own.
    Do NOT use for: long-running servers (Flask, Celery, dev servers) — use start_background_process instead.
    """
    error = _validate_command(command)
    if error:
        return f"Error: {error}"

    config = get_command_config()
    if max_run_ms <= 0:
        max_run_ms = config.get("timeout_ms", 30000)
    timeout_s = max_run_ms / 1000.0

    shell_cmd = _get_shell()
    full_cmd = shell_cmd + [command]

    cwd = working_directory
    if not cwd:
        from lc_agent.tools.system_tools._config import get_active_project_root
        cwd = get_active_project_root()
    if cwd:
        cwd_path = os.path.expanduser(cwd)
        if not os.path.isdir(cwd_path):
            return f"Error: Working directory not found: {cwd}"
        cwd = cwd_path

    start = time.time()
    try:
        proc = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=_get_subprocess_env(),
            encoding="utf-8",
            errors="replace",
        )
    except Exception as e:
        return f"Error executing command: {e}"

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    timed_out = False
    stdout_done = threading.Event()
    _stdout = proc.stdout
    _stderr = proc.stderr
    assert _stdout is not None
    assert _stderr is not None

    def _read_stdout():
        try:
            for line in iter(_stdout.readline, ""):
                if not line:
                    break
                stdout_lines.append(line)
        except (ValueError, OSError):
            pass
        finally:
            try:
                _stdout.close()
            except Exception:
                pass
            stdout_done.set()

    def _read_stderr():
        try:
            for line in iter(_stderr.readline, ""):
                if not line:
                    break
                stderr_lines.append(line)
        except (ValueError, OSError):
            pass
        finally:
            try:
                _stderr.close()
            except Exception:
                pass

    stdout_thread = threading.Thread(target=_read_stdout, daemon=True)
    stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    deadline = time.time() + timeout_s
    last_emitted_len = 0
    poll_interval = 0.2

    while not stdout_done.wait(timeout=poll_interval):
        new_len = len(stdout_lines)
        if new_len > last_emitted_len:
            for line in stdout_lines[last_emitted_len:new_len]:
                _emit_output_chunk(line)
            last_emitted_len = new_len
        if time.time() >= deadline:
            timed_out = True
            proc.kill()
            break

    for line in stdout_lines[last_emitted_len:]:
        _emit_output_chunk(line)

    if not timed_out:
        try:
            remaining = max(0, deadline - time.time())
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
    else:
        try:
            proc.wait(timeout=5)
        except Exception:
            pass

    stdout_thread.join(timeout=3)
    stderr_thread.join(timeout=3)
    elapsed_ms = int((time.time() - start) * 1000)

    if timed_out:
        parts = [f"{''.join(stdout_lines)}"]
        if stderr_lines:
            parts.append(f"[stderr]\n{''.join(stderr_lines)}")
        parts.append(f"[Command timed out after {elapsed_ms}ms, process killed]")
        return "\n".join(parts)

    parts: list[str] = []
    if stdout_lines:
        parts.append("".join(stdout_lines))
    if stderr_lines:
        parts.append(f"[stderr]\n{''.join(stderr_lines)}")

    status = f"[exit_code={proc.returncode}, duration={elapsed_ms}ms]"
    parts.append(status)

    output = "\n".join(parts)
    max_output = 50000
    if len(output) > max_output:
        output = output[:max_output] + f"\n\n... [output truncated at {max_output} chars]"

    return output


def _emit_process_info(pid: int, command: str) -> None:
    """Emit process info event so frontend can show PID immediately."""
    try:
        from langchain_core.callbacks import dispatch_custom_event
        dispatch_custom_event("command_process_info", {"pid": pid, "command": command})
    except Exception:
        pass


_emit_failed_logged = False


def _emit_output_chunk(content: str) -> None:
    """Try to emit a real-time output chunk via LangChain's custom event system."""
    global _emit_failed_logged
    try:
        from langchain_core.callbacks import dispatch_custom_event
        dispatch_custom_event("command_output", {"content": content})
    except Exception:
        if not _emit_failed_logged:
            _emit_failed_logged = True
            import logging
            logging.getLogger(__name__).debug(
                "dispatch_custom_event unavailable, streaming output disabled",
                exc_info=True,
            )


@tool(group="command", group_description="命令执行")
def list_all_processes() -> str:
    """List all currently running system processes with their PID, name, and memory usage. Limited to the first 100 results."""
    system = platform.system()
    try:
        if system == "Windows":
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
            )
            if result.returncode != 0:
                return f"Error: tasklist failed: {result.stderr}"
            lines = result.stdout.strip().splitlines()
            output_lines = ["PID\tName\tMemory"]
            for line in lines[:100]:
                parts = [p.strip('"') for p in line.split('","')]
                if len(parts) >= 5:
                    output_lines.append(f"{parts[1]}\t{parts[0]}\t{parts[4]}")
            if len(lines) > 100:
                output_lines.append(f"... [{len(lines) - 100} more processes not shown]")
            return "\n".join(output_lines)
        else:
            result = subprocess.run(
                ["ps", "aux", "--sort=-rss"],
                capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
            )
            if result.returncode != 0:
                return f"Error: ps failed: {result.stderr}"
            lines = result.stdout.strip().splitlines()
            if len(lines) > 101:
                return "\n".join(lines[:101]) + f"\n... [{len(lines) - 101} more processes]"
            return result.stdout
    except Exception as e:
        return f"Error listing processes: {e}"


@tool(group="command", group_description="命令执行")
def list_agent_started_processes() -> str:
    """List all background processes started by start_background_process that are currently tracked in this session."""
    _reap_exited_processes()

    if not _processes:
        return "No tracked background processes."

    lines = ["PID\tStatus\tRunning For\tCommand"]
    for pid, entry in _processes.items():
        is_running = entry.proc.poll() is None
        status = "running" if is_running else f"exited({entry.proc.returncode})"
        elapsed = time.time() - entry.start_time
        lines.append(f"{pid}\t{status}\t{elapsed:.0f}s\t{entry.command}")
    return "\n".join(lines)


@tool(group="command", group_description="命令执行")
def kill_process(
    pid: Annotated[int, "PID of the process to terminate"],
) -> str:
    """Terminate a process by its PID using SIGKILL on Linux/macOS or taskkill /F on Windows."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return f"Error: Failed to kill process {pid}: {result.stderr.strip()}"
        else:
            import signal
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return f"Error: Process {pid} not found"
    except PermissionError:
        return f"Error: Permission denied to kill process {pid}"
    except Exception as e:
        return f"Error killing process {pid}: {e}"

    _processes.pop(pid, None)
    return f"Process {pid} terminated"


@tool(group="command", group_description="命令执行")
def start_background_process(
    command: Annotated[str, "Command string to execute in the background"],
    wait_ms: Annotated[
        int,
        "Milliseconds to wait for initial output (default 10000 = 10s). After the wait the process keeps running in the background.",
    ] = 10000,
    working_directory: Annotated[
        str | None,
        "Working directory for the command; defaults to the project root (project mode) or server working directory",
    ] = None,
) -> str:
    """
    Start a long-running process in the background and return its PID with initial output.
    Generate commands according to the user’s operating system — do not execute Linux-syntax commands on Windows.

    Use for: Flask/Django/FastAPI servers, Celery workers, webpack dev servers, or any daemon that doesn't exit on its own.
    Do NOT use for: one-shot commands that exit by themselves — use run_command instead.

    After starting, use read_process_output to poll subsequent output and kill_process to terminate.
    """
    _reap_exited_processes()

    if len(_processes) >= _MAX_BG_PROCESSES:
        return (
            f"Error: Maximum background processes ({_MAX_BG_PROCESSES}) reached. "
            f"Use kill_process to terminate unused processes first."
        )

    error = _validate_command(command)
    if error:
        return f"Error: {error}"

    shell_cmd = _get_shell()
    full_cmd = shell_cmd + [command]

    cwd = working_directory
    if not cwd:
        from lc_agent.tools.system_tools._config import get_active_project_root
        cwd = get_active_project_root()
    if cwd:
        cwd_path = os.path.expanduser(cwd)
        if not os.path.isdir(cwd_path):
            return f"Error: Working directory not found: {cwd}"
        cwd = cwd_path

    try:
        proc = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=_get_subprocess_env(),
            encoding="utf-8",
            errors="replace",
        )
    except Exception as e:
        return f"Error starting process: {e}"

    entry = _ProcessEntry(proc, command)
    _processes[proc.pid] = entry

    _emit_process_info(proc.pid, command)

    stdout_thread = threading.Thread(
        target=_reader_thread, args=(entry, proc.stdout, entry.append_stdout), daemon=True
    )
    stderr_thread = threading.Thread(
        target=_reader_thread, args=(entry, proc.stderr, entry.append_stderr), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()

    deadline = time.time() + wait_ms / 1000.0
    last_emitted_len = 0
    poll_interval = 0.2

    while time.time() < deadline:
        time.sleep(poll_interval)
        with entry._lock:
            current_len = len(entry.stdout_buf)
        if current_len > last_emitted_len:
            new_lines = entry.stdout_buf[last_emitted_len:current_len]
            for line in new_lines:
                _emit_output_chunk(line)
            last_emitted_len = current_len
        if proc.poll() is not None:
            time.sleep(0.3)
            break

    initial_output = entry.get_full_output()
    is_running = proc.poll() is None

    if is_running:
        status = "running"
    elif "[Process terminated by user]" in initial_output:
        status = "terminated by user"
    else:
        status = f"exited (code={proc.returncode})"

    return (
        f"PID: {proc.pid}\n"
        f"Status: {status}\n"
        f"Command: {command}\n"
        f"---\n"
        f"{initial_output}"
    )


@tool(group="command", group_description="命令执行")
def read_process_output(
    pid: Annotated[int, "PID of the background process (returned by start_background_process)"],
    tail: Annotated[
        int,
        "Number of tail lines to return (default 50). Set 0 to return all buffered output.",
    ] = 50,
) -> str:
    """Read buffered stdout/stderr from a tracked background process. Returns process status and recent output."""
    entry = _processes.get(pid)
    if entry is None:
        return f"Error: No tracked background process with PID {pid}. Use start_background_process to start one."

    is_running = entry.proc.poll() is None
    elapsed = time.time() - entry.start_time
    status = "running" if is_running else f"exited (code={entry.proc.returncode})"

    full_output = entry.get_full_output()
    if tail > 0:
        lines = full_output.splitlines()
        if len(lines) > tail:
            full_output = "\n".join(lines[-tail:])
            full_output = f"... [{len(lines) - tail} earlier lines omitted]\n{full_output}"

    return (
        f"PID: {pid}\n"
        f"Status: {status}\n"
        f"Running for: {elapsed:.1f}s\n"
        f"Command: {entry.command}\n"
        f"---\n"
        f"{full_output}"
    )
