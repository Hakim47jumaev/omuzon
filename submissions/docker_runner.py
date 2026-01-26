# submissions/docker_runner.py
# ЛОКАЛЬНЫЙ RUNNER (БЕЗ DOCKER), контракт 1-в-1 с фронтом
# Формат результата:
# {
#   "status": "ok" | "compile_error" | "runtime_error" | "timeout" | "error",
#   "stdout": str,
#   "stderr": str,
#   "time": float,
#   "returncode": int
# }

import subprocess
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict
import resource

TIMEOUT = 2
MAX_OUTPUT = 64 * 1024  # 64 KB

CPU_SECONDS = 2
NPROC_LIMIT = 128
FSIZE_LIMIT = 10 * 1024 * 1024  # 10MB

# Memory limits per language (increase Dart/C# because VM/runtime needs mmap)
DEFAULT_MEMORY_BYTES = 256 * 1024 * 1024   # 256MB
DART_MEMORY_BYTES = 1024 * 1024 * 1024     # 1GB
CSHARP_MEMORY_BYTES = 1536 * 1024 * 1024   # 1.5GB


def _clip(s: str) -> str:
    return (s or "")[:MAX_OUTPUT]


def _limit_resources(mem_bytes: int):
    # CPU time
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))

    # Virtual memory limit (important for mmap; Dart needs more)
    if mem_bytes and mem_bytes > 0:
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

    # Process limit
    resource.setrlimit(resource.RLIMIT_NPROC, (NPROC_LIMIT, NPROC_LIMIT))

    # Max file size
    resource.setrlimit(resource.RLIMIT_FSIZE, (FSIZE_LIMIT, FSIZE_LIMIT))


def _run(cmd, input_data: str, cwd: Path, timeout: int, mem_bytes: int) -> Dict:
    start = time.time()
    try:
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd),
            text=True,
            preexec_fn=lambda: _limit_resources(mem_bytes),
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
        try:
            p.kill()
        except Exception:
            pass
        return {
            "status": "timeout",
            "stdout": "",
            "stderr": f"Execution timeout after {timeout}s",
            "time": round(time.time() - start, 3),
            "returncode": -1,
        }
    except Exception as e:
        return {
            "status": "error",
            "stdout": "",
            "stderr": str(e),
            "time": round(time.time() - start, 3),
            "returncode": -1,
        }


def run_python_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "main.py").write_text(code, encoding="utf-8")
        return _run(["python3", "main.py"], input_data, work, timeout, DEFAULT_MEMORY_BYTES)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_js_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "main.js").write_text(code, encoding="utf-8")
        return _run(["node", "main.js"], input_data, work, timeout, DEFAULT_MEMORY_BYTES)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_dart_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "main.dart").write_text(code, encoding="utf-8")
        # Dart VM needs more memory for mmap snapshots
        return _run(["dart", "run", "main.dart"], input_data, work, timeout, DART_MEMORY_BYTES)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_cpp_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    work = Path(tempfile.mkdtemp(prefix="code_run_"))
    try:
        (work / "main.cpp").write_text(code, encoding="utf-8")

        compile_res = _run(
            ["g++", "main.cpp", "-O2", "-std=c++17", "-o", "a.out"],
            "",
            work,
            timeout,
            DEFAULT_MEMORY_BYTES,
        )
        if compile_res["status"] != "ok":
            compile_res["status"] = "compile_error"
            return compile_res

        return _run(["./a.out"], input_data, work, timeout, DEFAULT_MEMORY_BYTES)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_csharp_in_docker(code: str, input_data: str = "", timeout: int = 20) -> Dict:
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
            "",
            work,
            timeout,
            CSHARP_MEMORY_BYTES,
        )
        if build["status"] != "ok":
            build["status"] = "compile_error"
            return build

        return _run(
            ["dotnet", "run", "-nologo", "--project", "App.csproj"],
            input_data,
            work,
            timeout,
            CSHARP_MEMORY_BYTES,
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
        return run_csharp_in_docker(code, input_data, timeout)

    return {
        "status": "error",
        "stdout": "",
        "stderr": f"Язык {lang} не поддерживается",
        "time": 0.0,
        "returncode": -1,
    }
