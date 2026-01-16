"""
Модуль для безопасного выполнения кода в Docker контейнерах
"""
import subprocess
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Настройки
DOCKER_IMAGES = {
    'python': 'code-runner-python',
    'javascript': 'code-runner-node',  # нужно будет создать
    'cpp': 'code-runner-cpp',  # нужно будет создать
    'c++': 'code-runner-cpp',
}

TIMEOUT = 2  # секунды
MAX_OUTPUT = 64 * 1024  # 64 KB
MAX_MEMORY = "256m"
MAX_CPUS = "0.5"

# Кэш для проверки доступности Docker
_docker_available = None


def _check_docker_available() -> bool:
    """
    Проверяет доступность Docker и кэширует результат
    """
    global _docker_available
    if _docker_available is not None:
        return _docker_available
    
    try:
        result = subprocess.run(
            ['docker', '--version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2
        )
        if result.returncode == 0:
            # Дополнительная проверка - попытка выполнить простую команду
            result = subprocess.run(
                ['docker', 'ps'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2
            )
            _docker_available = result.returncode == 0
        else:
            _docker_available = False
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.warning(f"Docker check failed: {e}")
        _docker_available = False
    
    return _docker_available


def run_code_in_docker(
    code: str,
    lang: str,
    input_data: str = "",
    timeout: int = TIMEOUT
) -> Dict:
    """
    Выполняет код в изолированном Docker контейнере
    
    Args:
        code: Код для выполнения
        lang: Язык программирования (python, javascript, cpp)
        input_data: Входные данные для программы
        timeout: Таймаут выполнения в секундах
    
    Returns:
        Словарь с результатами:
        {
            'status': 'ok' | 'runtime_error' | 'timeout' | 'error',
            'stdout': str,
            'stderr': str,
            'time': float,
            'returncode': int
        }
    """
    lang = lang.lower()
    
    # Проверяем доступность Docker
    if not _check_docker_available():
        return {
            'status': 'error',
            'stdout': '',
            'stderr': 'Docker недоступен. Убедитесь, что Docker запущен и доступен.',
            'time': 0.0,
            'returncode': -1
        }
    
    # Определяем образ Docker
    image = DOCKER_IMAGES.get(lang)
    if not image:
        return {
            'status': 'error',
            'stdout': '',
            'stderr': f'Язык {lang} не поддерживается',
            'time': 0.0,
            'returncode': -1
        }
    
    # Формируем команду для Docker
    if lang == 'python':
        cmd = ['python3', '-c', code]
    elif lang == 'javascript':
        cmd = ['node', '-e', code]
    elif lang in ('cpp', 'c++'):
        # Для C++ нужно сначала скомпилировать, потом запустить
        # Это будет обработано отдельно
        return {
            'status': 'error',
            'stdout': '',
            'stderr': 'C++ требует отдельной обработки (компиляция)',
            'time': 0.0,
            'returncode': -1
        }
    else:
        return {
            'status': 'error',
            'stdout': '',
            'stderr': f'Язык {lang} не поддерживается',
            'time': 0.0,
            'returncode': -1
        }
    
    # Docker команда с ограничениями безопасности
    docker_cmd = [
        'docker', 'run', '--rm', '-i',
        '--network=none',  # нет сети
        '--read-only',  # только чтение
        '--tmpfs=/tmp:rw,noexec,nosuid,size=100m',  # временная файловая система для /tmp
        f'--memory={MAX_MEMORY}',  # лимит памяти
        f'--cpus={MAX_CPUS}',  # лимит CPU
        '--user=runner',  # непривилегированный пользователь
        image
    ] + cmd
    
    start_time = time.time()
    
    try:
        logger.debug(f"Running Docker command for lang={lang}, timeout={timeout}")
        result = subprocess.run(
            docker_cmd,
            input=input_data.encode() if input_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        
        elapsed = round(time.time() - start_time, 3)
        
        stdout = result.stdout[:MAX_OUTPUT].decode(errors='ignore').strip()
        stderr = result.stderr[:MAX_OUTPUT].decode(errors='ignore').strip()
        
        if result.returncode != 0:
            logger.warning(f"Docker execution failed: returncode={result.returncode}, stderr={stderr[:100]}")
            return {
                'status': 'runtime_error',
                'stdout': stdout,
                'stderr': stderr,
                'time': elapsed,
                'returncode': result.returncode
            }
        
        logger.debug(f"Docker execution successful: elapsed={elapsed}s")
        return {
            'status': 'ok',
            'stdout': stdout,
            'stderr': stderr,
            'time': elapsed,
            'returncode': result.returncode
        }
        
    except subprocess.TimeoutExpired as e:
        elapsed = round(time.time() - start_time, 3)
        logger.warning(f"Docker execution timeout after {elapsed}s")
        # Пытаемся убить зависший процесс
        try:
            if hasattr(e, 'process') and e.process:
                e.process.kill()
                # Ждем немного, чтобы процесс завершился
                try:
                    e.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    # Если процесс не завершился, принудительно убиваем
                    e.process.terminate()
                    try:
                        e.process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        pass
        except Exception as kill_error:
            logger.warning(f"Error killing process: {kill_error}")
        return {
            'status': 'timeout',
            'stdout': '',
            'stderr': f'Execution timeout after {timeout}s',
            'time': elapsed,
            'returncode': -1
        }
    except FileNotFoundError:
        elapsed = round(time.time() - start_time, 3)
        logger.error("Docker command not found")
        return {
            'status': 'error',
            'stdout': '',
            'stderr': 'Docker не установлен или не найден в PATH',
            'time': elapsed,
            'returncode': -1
        }
    except Exception as e:
        elapsed = round(time.time() - start_time, 3)
        logger.error(f"Docker execution error: {e}", exc_info=True)
        return {
            'status': 'error',
            'stdout': '',
            'stderr': f'Ошибка выполнения: {str(e)}',
            'time': elapsed,
            'returncode': -1
        }


def run_cpp_in_docker(
    code: str,
    input_data: str = "",
    timeout: int = TIMEOUT
) -> Dict:
    """
    Выполняет C++ код в Docker контейнере
    Сначала компилирует, потом запускает
    Использует временную директорию внутри контейнера
    """
    # Проверяем доступность Docker
    if not _check_docker_available():
        return {
            'status': 'error',
            'stdout': '',
            'stderr': 'Docker недоступен. Убедитесь, что Docker запущен и доступен.',
            'time': 0.0,
            'returncode': -1
        }
    
    image = DOCKER_IMAGES.get('cpp')
    if not image:
        return {
            'status': 'error',
            'stdout': '',
            'stderr': 'C++ образ не найден',
            'time': 0.0,
            'returncode': -1
        }
    
    start_time = time.time()
    
    try:
        # Компилируем и запускаем в одной команде
        # Используем /tmp для записи через --tmpfs
        # Передаем код через stdin для компиляции
        compile_and_run_script = f'''
g++ -x c++ - -o /tmp/a.out 2>&1 <<'CPPEOF'
{code}
CPPEOF
if [ $? -eq 0 ]; then
    /tmp/a.out
fi
'''
        
        compile_and_run_cmd = [
            'docker', 'run', '--rm', '-i',
            '--network=none',
            '--tmpfs=/tmp:rw,noexec,nosuid,size=100m',  # временная файловая система
            f'--memory={MAX_MEMORY}',
            f'--cpus={MAX_CPUS}',
            '--user=runner',
            image,
            'sh', '-c', compile_and_run_script
        ]
        
        logger.debug(f"Running C++ Docker command, timeout={timeout}")
        result = subprocess.run(
            compile_and_run_cmd,
            input=input_data.encode() if input_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        
        elapsed = round(time.time() - start_time, 3)
        stdout = result.stdout[:MAX_OUTPUT].decode(errors='ignore').strip()
        stderr = result.stderr[:MAX_OUTPUT].decode(errors='ignore').strip()
        
        # Разделяем вывод компиляции и выполнения
        # Если есть ошибки компиляции, они будут в stderr
        if result.returncode != 0:
            logger.warning(f"C++ Docker execution failed: returncode={result.returncode}, stderr={stderr[:100]}")
            return {
                'status': 'runtime_error',
                'stdout': stdout,
                'stderr': stderr,
                'time': elapsed,
                'returncode': result.returncode
            }
        
        logger.debug(f"C++ Docker execution successful: elapsed={elapsed}s")
        return {
            'status': 'ok',
            'stdout': stdout,
            'stderr': stderr,
            'time': elapsed,
            'returncode': result.returncode
        }
        
    except subprocess.TimeoutExpired as e:
        elapsed = round(time.time() - start_time, 3)
        logger.warning(f"C++ Docker execution timeout after {elapsed}s")
        # Пытаемся убить зависший процесс
        try:
            if hasattr(e, 'process') and e.process:
                e.process.kill()
                # Ждем немного, чтобы процесс завершился
                try:
                    e.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    # Если процесс не завершился, принудительно убиваем
                    e.process.terminate()
                    try:
                        e.process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        pass
        except Exception as kill_error:
            logger.warning(f"Error killing C++ process: {kill_error}")
        return {
            'status': 'timeout',
            'stdout': '',
            'stderr': f'Execution timeout after {timeout}s',
            'time': elapsed,
            'returncode': -1
        }
    except FileNotFoundError:
        elapsed = round(time.time() - start_time, 3)
        logger.error("Docker command not found")
        return {
            'status': 'error',
            'stdout': '',
            'stderr': 'Docker не установлен или не найден в PATH',
            'time': elapsed,
            'returncode': -1
        }
    except Exception as e:
        elapsed = round(time.time() - start_time, 3)
        logger.error(f"C++ Docker execution error: {e}", exc_info=True)
        return {
            'status': 'error',
            'stdout': '',
            'stderr': f'Ошибка выполнения: {str(e)}',
            'time': elapsed,
            'returncode': -1
        }
