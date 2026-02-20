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
#
# IMPORTANT FIXES FOR C# (.NET):
# - RLIMIT_CPU=2 was killing dotnet build/run silently -> added per-command cpu_seconds
# - dotnet build with -v:q hides errors -> removed -v:q
# - dotnet uses many files/temp outputs -> increased NOFILE and FSIZE for dotnet calls
# - Always merge stdout+stderr for compile errors

import os
import sys
import signal
import subprocess
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, Optional

# resource module is Unix-only
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

TIMEOUT = 2
MAX_OUTPUT = 64 * 1024  # 64KB

# Limits (Linux)
CPU_SECONDS = 2
NPROC_LIMIT = 128
NOFILE_LIMIT = 128
FSIZE_LIMIT = 10 * 1024 * 1024  # 10MB

# RLIMIT_AS used only where safe
PY_MEMORY_BYTES = 256 * 1024 * 1024       # 256MB
CPP_RUN_MEMORY_BYTES = 256 * 1024 * 1024  # 256MB
CPP_COMPILE_MEMORY_BYTES = 768 * 1024 * 1024  # 768MB (compiling may need more)

# Node memory limit (V8 old space, MB)
NODE_MAX_OLD_SPACE_MB = 128

# Dotnet: prefer no RLIMIT_AS (it can crash on reserve); rely on timeout + CPU + NPROC
# Dart: prefer no RLIMIT_AS (snapshot mmap / coderange reserve issues); rely on timeout + CPU + NPROC

# Dotnet needs higher file/output limits
DOTNET_CPU_SECONDS = 15
DOTNET_NOFILE_LIMIT = 1024
DOTNET_FSIZE_LIMIT = 200 * 1024 * 1024  # 200MB


def _clip(s: str) -> str:
    return (s or "")[:MAX_OUTPUT]


def _set_limits(
    mem_bytes: Optional[int],
    cpu_seconds: int,
    nproc_limit: int,
    nofile_limit: int,
    fsize_limit: int,
) -> None:
    if not HAS_RESOURCE:
        # Windows doesn't support resource limits
        return
    
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))

    if mem_bytes is not None:
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

    resource.setrlimit(resource.RLIMIT_NPROC, (nproc_limit, nproc_limit))
    resource.setrlimit(resource.RLIMIT_NOFILE, (nofile_limit, nofile_limit))
    resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_limit, fsize_limit))


def _preexec(
    mem_bytes: Optional[int],
    cpu_seconds: int,
    nproc_limit: int,
    nofile_limit: int,
    fsize_limit: int,
) -> None:
    if sys.platform != 'win32':
        os.setsid()
    _set_limits(mem_bytes, cpu_seconds, nproc_limit, nofile_limit, fsize_limit)


def _run(
    cmd,
    input_data: str,
    cwd: Path,
    timeout: int,
    mem_bytes: Optional[int],
    env=None,
    cpu_seconds: int = CPU_SECONDS,
    nproc_limit: int = NPROC_LIMIT,
    nofile_limit: int = NOFILE_LIMIT,
    fsize_limit: int = FSIZE_LIMIT,
) -> Dict:
    start = time.time()
    p = None
    try:
        popen_kwargs = {
            'args': cmd,
            'stdin': subprocess.PIPE,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'cwd': str(cwd),
            'text': True,
            'env': env,
        }
        # preexec_fn is Unix-only
        if sys.platform != 'win32':
            popen_kwargs['preexec_fn'] = lambda: _preexec(mem_bytes, cpu_seconds, nproc_limit, nofile_limit, fsize_limit)
        
        p = subprocess.Popen(**popen_kwargs)

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
                if sys.platform != 'win32':
                    # Unix: kill process group
                    os.killpg(p.pid, signal.SIGKILL)
                else:
                    # Windows: kill process directly
                    p.kill()
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
        elapsed = round(time.time() - start, 3)
        return {"status": "error", "stdout": "", "stderr": str(e), "time": elapsed, "returncode": -1}

    except Exception as e:
        elapsed = round(time.time() - start, 3)
        return {"status": "error", "stdout": "", "stderr": str(e), "time": elapsed, "returncode": -1}


def _merge_out_err(res: Dict) -> Dict:
    """Ensure compile errors always contain message."""
    out = (res.get("stdout") or "").strip()
    err = (res.get("stderr") or "").strip()
    merged = (err + ("\n" + out if out else "")).strip()
    res["stdout"] = ""
    res["stderr"] = merged
    return res


# ----------------------------- C# WRAPPER (NO MAIN FROM STUDENT) -----------------------------

def wrap_csharp_code(student_code: str) -> str:
    """
    Accept student code WITHOUT Main / class / using.
    If student already provided Main / class / namespace / using => keep as-is (avoid double wrapping).
    """
    code = (student_code or "").strip()

    suspicious_tokens = ("Main(", "class ", "namespace ", "using ")
    if any(tok in code for tok in suspicious_tokens):
        return student_code

    indented = "\n".join(("        " + line) if line.strip() else "" for line in student_code.splitlines())

    return f"""using System;

class Program
{{
    static void Main(string[] args)
    {{
{indented}
    }}
}}
"""


# ---------------------------------- RUNNERS ----------------------------------

def run_python_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "main.py").write_text(code, encoding="utf-8")
        return _run(
            ["python3", "main.py"],
            input_data=input_data,
            cwd=work,
            timeout=timeout,
            mem_bytes=PY_MEMORY_BYTES,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_js_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "main.js").write_text(code, encoding="utf-8")
        return _run(
            ["node", f"--max-old-space-size={NODE_MAX_OLD_SPACE_MB}", "main.js"],
            input_data=input_data,
            cwd=work,
            timeout=timeout,
            mem_bytes=None,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_dart_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "main.dart").write_text(code, encoding="utf-8")
        return _run(
            ["dart", "run", "main.dart"],
            input_data=input_data,
            cwd=work,
            timeout=timeout,
            mem_bytes=None,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_cpp_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "main.cpp").write_text(code, encoding="utf-8")

        compile_res = _run(
            ["g++", "main.cpp", "-O2", "-std=c++17", "-o", "a.out"],
            input_data="",
            cwd=work,
            timeout=timeout,
            mem_bytes=CPP_COMPILE_MEMORY_BYTES,
        )
        if compile_res["status"] != "ok":
            compile_res["status"] = "compile_error"
            return _merge_out_err(compile_res)

        return _run(
            ["./a.out"],
            input_data=input_data,
            cwd=work,
            timeout=timeout,
            mem_bytes=CPP_RUN_MEMORY_BYTES,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_csharp_in_docker(code: str, input_data: str = "", timeout: int = 20) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        final_code = wrap_csharp_code(code)

        (work / "Program.cs").write_text(final_code, encoding="utf-8")
        (work / "App.csproj").write_text(
            """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net9.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
</Project>
""",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["DOTNET_CLI_HOME"] = "/tmp/dotnet_cli_home"
        env["NUGET_PACKAGES"] = "/tmp/nuget_packages"
        env["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
        env["DOTNET_NOLOGO"] = "1"
        env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"

        # build (NO -v:q !)
        build = _run(
            ["dotnet", "build", "-nologo", "App.csproj"],
            input_data="",
            cwd=work,
            timeout=timeout,
            mem_bytes=None,
            env=env,
            cpu_seconds=DOTNET_CPU_SECONDS,
            nofile_limit=DOTNET_NOFILE_LIMIT,
            fsize_limit=DOTNET_FSIZE_LIMIT,
        )
        if build["status"] != "ok":
            build["status"] = "compile_error"
            return _merge_out_err(build)

        # run
        return _run(
            ["dotnet", "run", "-nologo", "--project", "App.csproj"],
            input_data=input_data,
            cwd=work,
            timeout=timeout,
            mem_bytes=None,
            env=env,
            cpu_seconds=DOTNET_CPU_SECONDS,
            nofile_limit=DOTNET_NOFILE_LIMIT,
            fsize_limit=DOTNET_FSIZE_LIMIT,
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
