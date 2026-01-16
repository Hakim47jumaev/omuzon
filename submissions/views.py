# submissions/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from courses.models import Task, Enrollment, TestCase, Course
from .models import Submission
from .serializers import SubmissionSerializer
from .tasks import submit_code_task, execute_code_task
from .docker_runner import run_code_in_docker, run_cpp_in_docker
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from datetime import timedelta

MAX_CODE_LENGTH = 10000  # ограничение длины кода
MAX_SUBMISSIONS_PER_MINUTE = 10  # лимит сабмитов в минуту для защиты от накрутки

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['task_id', 'code'],
        properties={
            'task_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID задачи'),
            'code': openapi.Schema(type=openapi.TYPE_STRING, description='Код студента'),
            'lang': openapi.Schema(type=openapi.TYPE_STRING, description='Язык кода', default='python')
        },
        example={
            'task_id': 1,
            'code': "print('Hello World')",
            'lang': 'python'
        }
    ),
    responses={
        200: openapi.Response('Код проверен'),
        400: "Ошибка валидации или код слишком длинный",
        403: "Пользователь не записан на курс",
        404: "Задача не найдена"
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_code(request):
    """
    Отправка кода на проверку через Celery (асинхронно в Docker)
    Сразу создает Submission и возвращает его ID
    """
    serializer = SubmissionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    task_id = serializer.validated_data['task_id']
    code = serializer.validated_data['code']
    lang = serializer.validated_data.get('lang', 'python').lower()

    if len(code) > MAX_CODE_LENGTH:
        return Response({"error": "Code too long"}, status=400)

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({"error": "Task not found"}, status=404)

    # Проверка записи на курс (как раньше - для всех курсов, включая олимпиады)
    course = task.module.course
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        return Response({"error": "Not enrolled"}, status=403)

    # Проверка олимпиадного режима
    now = timezone.now()
    
    if course.is_olimpiad:
        # Проверка времени начала олимпиады
        if course.start_time and course.start_time > now:
            return Response(
                {"error": "Олимпиада ещё не началась. Отправка решений будет доступна после начала."},
                status=403
            )
        # Проверка времени окончания олимпиады
        if course.end_time and course.end_time < now:
            return Response(
                {"error": "Олимпиада завершена. Отправка решений больше недоступна."},
                status=403
            )
        
        # Защита от накрутки: проверка лимита сабмитов в минуту
        one_minute_ago = now - timedelta(minutes=1)
        recent_submissions_count = Submission.objects.filter(
            user=request.user,
            task__module__course=course,
            created_at__gte=one_minute_ago
        ).count()
        
        if recent_submissions_count >= MAX_SUBMISSIONS_PER_MINUTE:
            return Response(
                {"error": f"Превышен лимит отправок. Максимум {MAX_SUBMISSIONS_PER_MINUTE} отправок в минуту."},
                status=429
            )

    # Создаем Submission сразу со статусом "pending"
    submission = Submission.objects.create(
        user=request.user,
        task=task,
        code=code,
        status='pending',
        feedback='Проверка в процессе...',
        errors=[],
        lang=lang
    )

    # Запускаем проверку кода через Celery (асинхронно)
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Submitting code check task to Celery for submission_id={submission.id}")
        # Асинхронный вызов через Celery
        submit_code_task.delay(submission.id)
        # Возвращаем сразу, статус будет обновлён Celery worker'ом
    except Exception as celery_error:
        # Если Celery недоступен, выполняем синхронно как fallback
        logger.warning(f"Celery not available, executing synchronously: {celery_error}")
        try:
            submit_code_task(submission.id)
            submission.refresh_from_db()
        except Exception as sync_error:
            logger.error(f"Error in synchronous execution: {sync_error}", exc_info=True)
            import traceback
            submission.status = 'error'
            submission.feedback = f'Ошибка выполнения: {str(sync_error)}'
            submission.errors = [{"error": str(sync_error), "traceback": traceback.format_exc()}]
            submission.save()

    # Обновляем submission из БД, чтобы получить актуальный статус
    submission.refresh_from_db()
    
    # Возвращаем submission_id и текущий статус
    return Response({
        "submission_id": submission.id,
        "status": submission.status
    }, status=202 if submission.status == "pending" else 200)



@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['task_id', 'code'],
        properties={
            'task_id': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description='ID задачи'
            ),
            'code': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='Код студента'
            ),
            'input': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='Пользовательский input (необязательно)',
                default=''
            ),
            'lang': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='Язык',
                default='python'
            ),
        },
        example={
            "task_id": 1,
            "code": "a=int(input())\nprint('You entered a number', a)",
            "input": "11",
            "lang": "python"
        }
    ),
    responses={
        200: openapi.Response(
            description="Результат выполнения",
            examples={
                "application/json": {
                    "stdout": "You entered a number 11",
                    "stderr": "",
                    "used_input": "11",
                    "lang": "python"
                }
            }
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_code(request):
    """
    Запуск кода студента в Docker (Run).
    Без проверки, без сохранения.
    Выполняется синхронно, но в безопасном Docker контейнере.
    """

    task_id = request.data.get('task_id')
    code = request.data.get('code', '')
    lang = request.data.get('lang', 'python').lower()
    custom_input = request.data.get('input')

    if not task_id or not code:
        return Response({"error": "task_id и code обязательны"}, status=400)

    if len(code) > MAX_CODE_LENGTH:
        return Response({"error": "Код слишком длинный"}, status=400)

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({"error": "Задача не найдена"}, status=404)

    # ---------------- INPUT ----------------
    # Если input не передан или пустой - берем первый тест-кейс задачи
    if custom_input is not None and str(custom_input).strip():
        used_input = str(custom_input)  # кастомный ввод
    else:
        # Берем первый тест-кейс задачи
        test = TestCase.objects.filter(task=task, is_active=True).order_by('order').first()
        if test:
            used_input = str(test.input_data) if test.input_data else ""
        else:
            used_input = ""  # если нет тест-кейсов - пустой ввод

    # Выполняем код в Docker контейнере
    if lang in ('cpp', 'c++'):
        result = run_cpp_in_docker(code, used_input, timeout=2)
    else:
        result = run_code_in_docker(code, lang, used_input, timeout=2)

    # Формируем ответ
    if result['status'] == 'ok':
        return Response({
            "stdout": result['stdout'],
            "stderr": result['stderr'],
            "used_input": used_input,
            "lang": lang
        })
    else:
        return Response({
        "stdout": result.get('stdout', ''),
        "stderr": result.get('stderr', 'Unknown error'),
        "used_input": used_input,
        "lang": lang
    })


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            description="Результат проверки кода",
            examples={
                "application/json": {
                    "id": 123,
                    "status": "accepted",
                    "feedback": "All tests passed",
                    "errors": [],
                    "code": "print('Hello')",
                    "lang": "python",
                    "created_at": "2024-01-01T12:00:00Z"
                }
            }
        ),
        404: "Submission not found"
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_submission(request, submission_id):
    """
    Получает результат проверки кода по ID submission
    """
    try:
        submission = Submission.objects.get(id=submission_id, user=request.user)
        
        return Response({
            "id": submission.id,
            "status": submission.status,
            "feedback": submission.feedback,
            "errors": submission.errors,
            "code": submission.code,
            "lang": submission.lang,
            "created_at": submission.created_at,
            "task_id": submission.task.id,
            "task_title": submission.task.title
        })
    except Submission.DoesNotExist:
        return Response({
            "error": "Submission not found"
        }, status=404)
