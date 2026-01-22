"""
docker_runner.py

Безопасный запуск кода в Docker (python/js/dart/cpp/csharp)

Особенности:
- Код пишется в /work (tmpfs), затем запускается.
- stdin (input_data) работает для всех языков.
- Ограничения: no network, read-only root, tmpfs /work, лимиты CPU/RAM.
- Единый формат результата:
  {
    "status": "ok" | "compile_error" | "runtime_error" | "timeout" | "error",
    "stdout": str,
    "stderr": str,
    "time": float,
    "returncode": int
  }
"""
import subprocess
import time
import logging
from typing import Dict

logger = logging.getLogger(__name__)

DOCKER_IMAGES = {
    "python": "code-runner-python",
    "py": "code-runner-python",

    "javascript": "code-runner-node",
    "js": "code-runner-node",
    "node": "code-runner-node",

    "dart": "code-runner-dart",

    "cpp": "code-runner-cpp",
    "c++": "code-runner-cpp",

    "csharp": "code-runner-csharp",
    "c#": "code-runner-csharp",
    "cs": "code-runner-csharp",
}

TIMEOUT = 2  # seconds
MAX_OUTPUT = 64 * 1024  # 64 KB
MAX_MEMORY = "256m"
MAX_CPUS = "0.5"
WORK_SIZE = "200m"
TMP_SIZE = "100m"

_docker_available = None


def _check_docker_available() -> bool:
    global _docker_available
    if _docker_available is not None:
        return _docker_available

    try:
        r1 = subprocess.run(
            ["docker", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )
        if r1.returncode != 0:
            _docker_available = False
            return _docker_available

        r2 = subprocess.run(
            ["docker", "ps"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )
        _docker_available = (r2.returncode == 0)
        return _docker_available
    except Exception as e:
        logger.warning(f"Docker check failed: {e}")
        _docker_available = False
        return _docker_available


def _clip(s: str) -> str:
    s = s or ""
    if len(s) > MAX_OUTPUT:
        return s[:MAX_OUTPUT]
    return s


def _docker_run_sh(image: str, sh_script: str, input_data: str, timeout: int) -> Dict:
    """
    Запуск sh-скрипта внутри контейнера.
    /work writable (tmpfs) и EXECUTABLE (без noexec), иначе C++/C# не запустятся.
    """
    docker_cmd = [
        "docker", "run", "--rm", "-i",
        "--network=none",
        "--read-only",
        f"--tmpfs=/work:rw,nosuid,nodev,size={WORK_SIZE}",             # <-- без noexec
        f"--tmpfs=/tmp:rw,nosuid,nodev,noexec,size={TMP_SIZE}",
        f"--memory={MAX_MEMORY}",
        f"--cpus={MAX_CPUS}",
        "--pids-limit=128",
        "--user=runner",
        "-w", "/work",
        image,
        "sh", "-lc", sh_script,
    ]

    start_time = time.time()
    try:
        res = subprocess.run(
            docker_cmd,
            input=(input_data or ""),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
        )
        elapsed = round(time.time() - start_time, 3)

        stdout = _clip((res.stdout or "").strip())
        stderr = _clip((res.stderr or "").strip())

        if res.returncode == 0:
            return {
                "status": "ok",
                "stdout": stdout,
                "stderr": stderr,
                "time": elapsed,
                "returncode": res.returncode,
            }

        # Специальные коды: compile_error для C++/C#
        if res.returncode in (100, 101):
            return {
                "status": "compile_error",
                "stdout": stdout,
                "stderr": stderr,
                "time": elapsed,
                "returncode": res.returncode,
            }

        return {
            "status": "runtime_error",
            "stdout": stdout,
            "stderr": stderr,
            "time": elapsed,
            "returncode": res.returncode,
        }

    except subprocess.TimeoutExpired:
        elapsed = round(time.time() - start_time, 3)
        return {
            "status": "timeout",
            "stdout": "",
            "stderr": f"Execution timeout after {timeout}s",
            "time": elapsed,
            "returncode": -1,
        }
    except FileNotFoundError:
        elapsed = round(time.time() - start_time, 3)
        return {
            "status": "error",
            "stdout": "",
            "stderr": "Docker не установлен или не найден в PATH",
            "time": elapsed,
            "returncode": -1,
        }
    except Exception as e:
        elapsed = round(time.time() - start_time, 3)
        logger.error(f"Docker execution error: {e}", exc_info=True)
        return {
            "status": "error",
            "stdout": "",
            "stderr": f"Ошибка выполнения: {str(e)}",
            "time": elapsed,
            "returncode": -1,
        }


def run_python_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    script = f"""\
cat > /work/main.py <<'PYEOF'
{code}
PYEOF
python3 /work/main.py
"""
    return _docker_run_sh(DOCKER_IMAGES["python"], script, input_data, timeout)


def run_js_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    script = f"""\
cat > /work/main.js <<'JSEOF'
{code}
JSEOF
node /work/main.js
"""
    return _docker_run_sh(DOCKER_IMAGES["javascript"], script, input_data, timeout)


def run_dart_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    script = f"""\
cat > /work/main.dart <<'DARTEOF'
{code}
DARTEOF
dart run /work/main.dart
"""
    return _docker_run_sh(DOCKER_IMAGES["dart"], script, input_data, timeout)


def run_cpp_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    # returncode=100 -> compile_error
    script = f"""\
cat > /work/main.cpp <<'CPPEOF'
{code}
CPPEOF
g++ /work/main.cpp -O2 -std=c++17 -o /work/a.out || exit 100
/work/a.out
"""
    return _docker_run_sh(DOCKER_IMAGES["cpp"], script, input_data, timeout)


def run_csharp_in_docker(code: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    """
    Ожидается полный Program.cs.
    returncode=101 -> compile_error (dotnet build failed)
    """
    script = f"""\
export DOTNET_CLI_HOME=/work/dotnet
export NUGET_PACKAGES=/work/nuget
export HOME=/work

cat > /work/Program.cs <<'CSEOF'
{code}
CSEOF

cat > /work/App.csproj <<'CSPROJEOF'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
</Project>
CSPROJEOF

dotnet build -nologo -v:q /work/App.csproj || exit 101
dotnet run -nologo --project /work/App.csproj
"""
    return _docker_run_sh(DOCKER_IMAGES["csharp"], script, input_data, timeout)


def run_code_in_docker(code: str, lang: str, input_data: str = "", timeout: int = TIMEOUT) -> Dict:
    """
    Универсальная точка входа.
    """
    lang = (lang or "").lower().strip()

    if not _check_docker_available():
        return {
            "status": "error",
            "stdout": "",
            "stderr": "Docker недоступен. Убедитесь, что Docker запущен и доступен.",
            "time": 0.0,
            "returncode": -1,
        }

    if lang not in DOCKER_IMAGES:
        return {
            "status": "error",
            "stdout": "",
            "stderr": f"Язык {lang} не поддерживается",
            "time": 0.0,
            "returncode": -1,
        }

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
