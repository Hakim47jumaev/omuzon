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


@shared_task
def submit_code_task(submission_id: int):
    """
    Проверяет код студента по всем тест-кейсам и обновляет Submission
    
    Args:
        submission_id: ID существующей Submission для обновления
    
    Returns:
        ID обновленной Submission
    """
    logger.info(f"Starting submission check for submission_id={submission_id}")
    try:
        submission = Submission.objects.get(id=submission_id)
    except Submission.DoesNotExist:
        logger.error(f"Submission {submission_id} not found")
        return None
    
    user = submission.user
    task = submission.task
    code = submission.code
    lang = submission.lang.lower()
    
    # Проверяем, что пользователь записан на курс
    if not Enrollment.objects.filter(user=user, course=task.module.course).exists():
        submission.status = 'error'
        submission.feedback = 'Пользователь не записан на курс'
        submission.save()
        return submission.id
    
    # Получаем все активные тест-кейсы
    testcases = TestCase.objects.filter(task=task, is_active=True).order_by('order')
    
    if not testcases.exists():
        # Нет тест-кейсов - обновляем submission со статусом error
        submission.status = 'error'
        submission.feedback = 'Нет тест-кейсов для проверки'
        submission.errors = []
        submission.save()
        return submission.id
    
    status_result = "accepted"
    feedback = "All tests passed"
    errors = []
    
    # Проверяем каждый тест-кейс
    for idx, test in enumerate(testcases, start=1):
        input_data = test.input_data or ""
        expected_output = test.expected_output.strip()
        
        # Выполняем код в Docker
        if lang in ('cpp', 'c++'):
            result = run_cpp_in_docker(code, input_data, timeout=2)
        else:
            result = run_code_in_docker(code, lang, input_data, timeout=2)
        
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
    
    # Обновляем Submission
    submission.status = status_result
    submission.feedback = feedback
    submission.errors = errors
    submission.save()
    
    logger.info(f"Submission {submission_id} updated with status={status_result}")
    return submission.id
