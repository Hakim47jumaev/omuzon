# tasks.py
"""
Celery задачи для асинхронной проверки submission по тестам
Поведение как в Stepik:
- CRLF и LF считаются одинаковыми
- пробелы в конце строк игнорируются
- пустые строки в конце игнорируются
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from courses.models import TestCase, Enrollment
from .models import Submission
from .docker_runner import run_code_in_docker
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def normalize_output(s: str) -> str:
    """
    Stepik-like нормализация вывода.
    """
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in s.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


@shared_task
def execute_code_task(code: str, lang: str, input_data: str = "", timeout: int = 2):
    """
    Выполнение кода в Docker (режим Run).
    """
    return run_code_in_docker(code, lang, input_data, timeout)


def execute_submission_check(submission_id: int):
    logger.info(f"=== Starting submission check for submission_id={submission_id} ===")

    try:
        submission = Submission.objects.select_related("user", "task").get(id=submission_id)
    except Submission.DoesNotExist:
        logger.error(f"Submission {submission_id} not found")
        return None

    user = submission.user
    task = submission.task
    course = task.module.course
    code = submission.code
    lang = (submission.lang or "").lower().strip()

    # Проверка записи на курс
    if not Enrollment.objects.filter(user=user, course=course).exists():
        submission.status = "error"
        submission.feedback = "Пользователь не записан на курс"
        submission.errors = []
        submission.save(update_fields=["status", "feedback", "errors"])
        return submission.id

    testcases = TestCase.objects.filter(task=task, is_active=True).order_by("order")
    if not testcases.exists():
        submission.status = "error"
        submission.feedback = "Нет тест-кейсов для проверки"
        submission.errors = []
        submission.save(update_fields=["status", "feedback", "errors"])
        return submission.id

    status_result = "accepted"
    feedback = "All tests passed"
    errors = []

    try:
        for idx, test in enumerate(testcases, start=1):
            input_data = test.input_data or ""

            result = run_code_in_docker(code, lang, input_data, timeout=2)
            st = result.get("status")

            if st == "timeout":
                status_result = "error"
                feedback = f"Timeout on test {idx}"
                errors.append({
                    "test_index": idx,
                    "test_db_id": test.id,
                    "input": input_data,
                    "error": "timeout",
                })
                break

            if st == "compile_error":
                status_result = "rejected"
                feedback = f"Compile error on test {idx}"
                errors.append({
                    "test_index": idx,
                    "test_db_id": test.id,
                    "input": input_data,
                    "error": "compile_error",
                    "stderr": result.get("stderr", ""),
                })
                break

            if st in ("runtime_error", "error"):
                status_result = "error"
                feedback = (result.get("stderr") or "Runtime error").strip()
                errors.append({
                    "test_index": idx,
                    "test_db_id": test.id,
                    "input": input_data,
                    "error": "runtime_error",
                    "stderr": result.get("stderr", ""),
                })
                break

            if st == "ok":
                raw_out = result.get("stdout") or ""
                raw_exp = test.expected_output or ""

                output = normalize_output(raw_out)
                expected_output = normalize_output(raw_exp)

                if output != expected_output:
                    status_result = "rejected"
                    feedback = f"Failed test {idx}"
                    errors.append({
                        "test_index": idx,
                        "test_db_id": test.id,
                        "input": input_data,
                        "expected": raw_exp,
                        "output": raw_out,
                    })
                    break
            else:
                status_result = "error"
                feedback = f"Unknown error on test {idx}"
                errors.append({
                    "test_index": idx,
                    "test_db_id": test.id,
                    "input": input_data,
                    "error": "unknown_status",
                    "status": st,
                })
                break

    except Exception as e:
        logger.error(f"Error during submission check {submission_id}: {e}", exc_info=True)
        status_result = "error"
        feedback = f"Ошибка при проверке: {str(e)}"
        errors = [{"error": str(e)}]

    submission.refresh_from_db()
    submission.status = status_result
    submission.feedback = feedback
    submission.errors = errors
    submission.save(update_fields=["status", "feedback", "errors"])

    logger.info(f"=== Completed submission check for submission_id={submission_id} ===")
    return submission.id


@shared_task(bind=True, max_retries=0, time_limit=60, soft_time_limit=50)
def submit_code_task(self, submission_id: int):
    return execute_submission_check(submission_id)
