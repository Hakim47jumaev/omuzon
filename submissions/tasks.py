"""
Celery задачи для асинхронной проверки submission по тестам
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from courses.models import TestCase, Enrollment
from .models import Submission
from .docker_runner import run_code_in_docker
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def execute_code_task(code: str, lang: str, input_data: str = "", timeout: int = 2):
    """
    Выполняет код в Docker контейнере (для режима Run).
    """
    return run_code_in_docker(code, lang, input_data, timeout)


def execute_submission_check(submission_id: int):
    logger.info(f"=== Starting submission check for submission_id={submission_id} ===")

    try:
        submission = Submission.objects.select_related("user", "task").get(id=submission_id)
        logger.info(
            f"Submission {submission_id} loaded: user={submission.user}, task={submission.task.id}, lang={submission.lang}"
        )
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
    lang = (submission.lang or "").lower().strip()

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
            expected_output = (test.expected_output or "").strip()

            logger.debug(f"Running test {idx} for submission_id={submission_id}")

            result = run_code_in_docker(code, lang, input_data, timeout=2)
            st = result.get("status")

            logger.debug(f"Test {idx} result: status={st}")

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
                output = (result.get("stdout") or "").strip()
                if output != expected_output:
                    status_result = "rejected"
                    feedback = f"Failed test {idx}"
                    errors.append({
                        "test_index": idx,
                        "test_db_id": test.id,
                        "input": input_data,
                        "expected": expected_output,
                        "output": output,
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
        logger.error(f"Error during submission check for {submission_id}: {e}", exc_info=True)
        status_result = "error"
        feedback = f"Ошибка при проверке: {str(e)}"
        errors = [{"error": str(e)}]

    try:
        submission.refresh_from_db()
        submission.status = status_result
        submission.feedback = feedback
        submission.errors = errors
        submission.save(update_fields=["status", "feedback", "errors"])
        logger.info(f"✓ Submission {submission_id} updated successfully: status={status_result}, feedback={feedback[:80]}")
    except Exception as save_error:
        logger.error(f"✗ Error saving submission {submission_id}: {save_error}", exc_info=True)

    logger.info(f"=== Completed submission check for submission_id={submission_id} ===")
    return submission.id


@shared_task(bind=True, max_retries=0, time_limit=60, soft_time_limit=50)
def submit_code_task(self, submission_id: int):
    return execute_submission_check(submission_id)
