"""
Celery задачи для асинхронного выполнения кода в Docker
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from courses.models import Task, TestCase, Enrollment
from .models import Submission
from .docker_runner import run_code_in_docker, run_cpp_in_docker
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def execute_code_task(
    code: str,
    lang: str,
    input_data: str = "",
    timeout: int = 2
):
    """
    Выполняет код в Docker контейнере (для run_code)
    
    Returns:
        Результат выполнения кода
    """
    lang = lang.lower()
    
    if lang in ('cpp', 'c++'):
        result = run_cpp_in_docker(code, input_data, timeout)
    else:
        result = run_code_in_docker(code, lang, input_data, timeout)
    
    return result


def execute_submission_check(submission_id: int):
    """
    Функция для проверки кода студента по всем тест-кейсам
    Может быть вызвана напрямую или через Celery
    """
    logger.info(f"=== Starting submission check for submission_id={submission_id} ===")
    try:
        submission = Submission.objects.get(id=submission_id)
        logger.info(f"Submission {submission_id} loaded: user={submission.user}, task={submission.task.id}, lang={submission.lang}")
    except Submission.DoesNotExist:
        logger.error(f"✗ Submission {submission_id} not found in database")
        return None
    except Exception as e:
        logger.error(f"✗ Error loading submission {submission_id}: {e}", exc_info=True)
        return None
    
    user = submission.user
    task = submission.task
    course = task.module.course
    code = submission.code
    lang = submission.lang.lower()
    
    # Проверяем, что пользователь записан на курс (как раньше - для всех курсов)
    if not Enrollment.objects.filter(user=user, course=course).exists():
        submission.status = 'error'
        submission.feedback = 'Пользователь не записан на курс'
        submission.save()
        return submission.id
    
    # Получаем все активные тест-кейсы
    testcases = TestCase.objects.filter(task=task, is_active=True).order_by('order')
    testcases_count = testcases.count()
    logger.info(f"Found {testcases_count} test cases for task {task.id}")
    
    if testcases_count == 0:
        # Нет тест-кейсов - обновляем submission со статусом error
        logger.warning(f"No test cases found for task {task.id}")
        submission.status = 'error'
        submission.feedback = 'Нет тест-кейсов для проверки'
        submission.errors = []
        submission.save()
        return submission.id
    
    status_result = "accepted"
    feedback = "All tests passed"
    errors = []
    
    # Проверяем каждый тест-кейс
    try:
        for idx, test in enumerate(testcases, start=1):
            input_data = test.input_data or ""
            expected_output = test.expected_output.strip()
            
            logger.debug(f"Running test {idx} for submission_id={submission_id}")
            
            # Выполняем код в Docker с таймаутом
            if lang in ('cpp', 'c++'):
                result = run_cpp_in_docker(code, input_data, timeout=2)
            else:
                result = run_code_in_docker(code, lang, input_data, timeout=2)
            
            logger.debug(f"Test {idx} result: status={result.get('status')}")
            
            # Обрабатываем результат
            if result['status'] == 'timeout':
                status_result = "error"
                feedback = f"Timeout on test {idx}"
                errors.append({
                    "test_index": idx,
                    "test_db_id": test.id,
                    "error": "timeout"
                })
                break
            
            elif result['status'] == 'runtime_error' or result['status'] == 'error':
                status_result = "error"
                feedback = result.get('stderr', 'Runtime error')
                errors.append({
                    "test_index": idx,
                    "test_db_id": test.id,
                    "error": result.get('stderr', 'Runtime error')
                })
                break
            
            elif result['status'] == 'ok':
                # Проверяем вывод
                output = result['stdout'].strip()
                if output != expected_output:
                    status_result = "rejected"
                    feedback = f"Failed test {idx}"
                    errors.append({
                        "test_index": idx,
                        "test_db_id": test.id,
                        "expected": expected_output,
                        "output": output
                    })
                    break
            
            else:
                status_result = "error"
                feedback = f"Unknown error on test {idx}"
                errors.append({
                    "test_index": idx,
                    "test_db_id": test.id,
                    "error": "Unknown error"
                })
                break
    except Exception as e:
        # Обработка неожиданных ошибок (например, таймаут всей задачи)
        logger.error(f"Error during submission check for {submission_id}: {e}", exc_info=True)
        status_result = "error"
        feedback = f"Ошибка при проверке: {str(e)}"
        errors = [{"error": str(e)}]
    
    # Обновляем Submission
    try:
        submission.refresh_from_db()
        submission.status = status_result
        submission.feedback = feedback
        submission.errors = errors
        submission.save()
        logger.info(f"✓ Submission {submission_id} updated successfully: status={status_result}, feedback={feedback[:50]}")
    except Exception as save_error:
        logger.error(f"✗ Error saving submission {submission_id}: {save_error}", exc_info=True)
    
    logger.info(f"=== Completed submission check for submission_id={submission_id} ===")
    return submission.id


@shared_task(bind=True, max_retries=0, time_limit=60, soft_time_limit=50)
def submit_code_task(self, submission_id: int):
    """
    Celery задача для проверки кода студента по всем тест-кейсам и обновления Submission
    
    Args:
        self: Celery task instance (игнорируется при прямом вызове)
        submission_id: ID существующей Submission для обновления
    
    Returns:
        ID обновленной Submission
    """
    return execute_submission_check(submission_id)
