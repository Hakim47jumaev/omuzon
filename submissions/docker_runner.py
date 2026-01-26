# submissions/docker_runner.py
# Local runner (NO Docker). Keeps the same function names + return format used by your current views/tasks.
#
# Result format:
# {
#   "status": "ok" | "compile_error" | "runtime_error" | "timeout" | "error",
#   "stdout": str,
#   "stderr": str,
#   "time": float,
#   "returncode": int
# }
#
# Notes:
# - We do NOT use RLIMIT_AS for Node/Dart/C# because it often crashes V8/Dart VM/.NET with "Failed to reserve virtual memory".
# - For Node we limit memory via V8 flag --max-old-space-size.
# - We use process groups so timeout kills child processes too.

import os
import signal
import subprocess
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, Optional
import resource

TIMEOUT = 2
MAX_OUTPUT = 64 * 1024  # 64KB

# Limits (Linux)
CPU_SECONDS = 2
NPROC_LIMIT = 128
NOFILE_LIMIT = 128
FSIZE_LIMIT = 10 * 1024 * 1024  # 10MB

# RLIMIT_AS used only where safe
PY_MEMORY_BYTES = 256 * 1024 * 1024      # 256MB
CPP_RUN_MEMORY_BYTES = 256 * 1024 * 1024 # 256MB
CPP_COMPILE_MEMORY_BYTES = 768 * 1024 * 1024  # 768MB (compiling may need more)

# Node memory limit (V8 old space, MB)
NODE_MAX_OLD_SPACE_MB = 128

# Dotnet: prefer no RLIMIT_AS (it can crash on reserve); rely on timeout + CPU + NPROC
# Dart: prefer no RLIMIT_AS (snapshot mmap / coderange reserve issues); rely on timeout + CPU + NPROC


def _clip(s: str) -> str:
    return (s or "")[:MAX_OUTPUT]


def _set_limits(mem_bytes: Optional[int]) -> None:
    # Kill CPU hogs
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))

    # Virtual memory limit (OPTIONAL: do not set for Node/Dart/.NET to avoid reserve/mmap crashes)
    if mem_bytes is not None:
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

    # Process / files limits
    resource.setrlimit(resource.RLIMIT_NPROC, (NPROC_LIMIT, NPROC_LIMIT))
    resource.setrlimit(resource.RLIMIT_NOFILE, (NOFILE_LIMIT, NOFILE_LIMIT))
    resource.setrlimit(resource.RLIMIT_FSIZE, (FSIZE_LIMIT, FSIZE_LIMIT))


def _preexec(mem_bytes: Optional[int]) -> None:
    # New process group => kill children on timeout
    os.setsid()
    _set_limits(mem_bytes)


def _run(cmd, input_data: str, cwd: Path, timeout: int, mem_bytes: Optional[int]) -> Dict:
    start = time.time()
    p = None
    try:
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd),
            text=True,
            preexec_fn=lambda: _preexec(mem_bytes),
        )

        stdout, stderr = p.communicate(input=input_data or "", timeout=timeout)
        elapsed = round(time.time() - start, 3)

        stdout = _clip(stdout).strip()
        stderr = _clip(stderr).strip()

        if p.returncode == 0:
            return {"status": "ok", "stdout": stdout, "stderr": stderr, "time": elapsed, "returncode": 0}

        return {
            "status": "runtime_error",
            "stdout": stdout,
            "stderr": stderr,
            "time": elapsed,
            "returncode": p.returncode,
        }

    except subprocess.TimeoutExpired:
        elapsed = round(time.time() - start, 3)
        try:
            if p and p.pid:
                os.killpg(p.pid, signal.SIGKILL)
        except Exception:
            try:
                if p:
                    p.kill()
            except Exception:
                pass

        return {
            "status": "timeout",
            "stdout": "",
            "stderr": f"Execution timeout after {timeout}s",
            "time": elapsed,
            "returncode": -1,
        }

    except FileNotFoundError as e:
        # e.g. 'dart' not found, 'node' not found, etc.
        elapsed = round(time.time() - start, 3)
        return {
            "status": "error",
            "stdout": "",
            "stderr": str(e),
            "time": elapsed,
            "returncode": -1,
        }

    except Exception as e:
        elapsed = round(time.time() - start, 3)
        return {
            "status": "error",
            "stdout": "",
            "stderr": str(e),
            "time": elapsed,
            "returncode": -1,
        }


def run_python_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "main.py").write_text(code, encoding="utf-8")
        return _run(["python3", "main.py"], input_data, work, timeout, mem_bytes=PY_MEMORY_BYTES)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_js_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "main.js").write_text(code, encoding="utf-8")
        # IMPORTANT: no RLIMIT_AS for Node, use V8 heap limit instead
        return _run(
            ["node", f"--max-old-space-size={NODE_MAX_OLD_SPACE_MB}", "main.js"],
            input_data,
            work,
            timeout,
            mem_bytes=None,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_dart_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "main.dart").write_text(code, encoding="utf-8")
        # IMPORTANT: no RLIMIT_AS for Dart (snapshot mmap / coderange reserve issues)
        return _run(["dart", "run", "main.dart"], input_data, work, timeout, mem_bytes=None)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_cpp_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "main.cpp").write_text(code, encoding="utf-8")

        # Compile (more memory)
        compile_res = _run(
            ["g++", "main.cpp", "-O2", "-std=c++17", "-o", "a.out"],
            input_data="",
            cwd=work,
            timeout=timeout,
            mem_bytes=CPP_COMPILE_MEMORY_BYTES,
        )
        if compile_res["status"] != "ok":
            compile_res["status"] = "compile_error"
            return compile_res

        # Run (less memory)
        return _run(["./a.out"], input_data, work, timeout, mem_bytes=CPP_RUN_MEMORY_BYTES)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_csharp_in_docker(code: str, input_data: str = "", timeout: int = 20) -> Dict:
    """
    Expects full Program.cs.
    IMPORTANT: no RLIMIT_AS for .NET (often fails to reserve).
    """
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "Program.cs").write_text(code, encoding="utf-8")
        (work / "App.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
</Project>
""",
            encoding="utf-8",
        )

        build = _run(
            ["dotnet", "build", "-nologo", "-v:q", "App.csproj"],
            input_data="",
            cwd=work,
            timeout=timeout,
            mem_bytes=None,
        )
        if build["status"] != "ok":
            build["status"] = "compile_error"
            return build

        # Pass stdin to dotnet run (works for Console.ReadLine)
        return _run(
            ["dotnet", "run", "-nologo", "--project", "App.csproj"],
            input_data=input_data,
            cwd=work,
            timeout=timeout,
            mem_bytes=None,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_code_in_docker(code: str, lang: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    lang = (lang or "").lower().strip()

    if lang in ("python", "py"):
        return run_python_in_docker(code, input_data, timeout)

    if lang in ("javascript", "js", "node"):
        return run_js_in_docker(code, input_data, timeout)

    if lang == "dart":
        return run_dart_in_docker(code, input_data, timeout)

    if lang in ("cpp", "c++"):
        return run_cpp_in_docker(code, input_data, timeout)

    if lang in ("csharp", "c#", "cs"):
        return run_csharp_in_docker(code, input_data, timeout if timeout else 20)

    return {
        "status": "error",
        "stdout": "",
        "stderr": f"Язык {lang} не поддерживается",
        "time": 0.0,
        "returncode": -1,
    }
