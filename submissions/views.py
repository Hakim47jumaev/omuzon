# submissions/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from courses.models import Task, Enrollment, TestCase
from .models import Submission
from .serializers import SubmissionSerializer
import subprocess
import sys
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

MAX_CODE_LENGTH = 10000  # ограничение длины кода

# submissions/views.py
import subprocess
import sys
import tempfile
import os

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
    serializer = SubmissionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    task_id = serializer.validated_data['task_id']
    code = serializer.validated_data['code']
    lang = serializer.validated_data.get('lang', '').lower()

    if len(code) > MAX_CODE_LENGTH:
        return Response({"error": "Код слишком длинный"}, status=400)

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({"error": "Задача не найдена"}, status=404)

    if not Enrollment.objects.filter(user=request.user, course=task.module.course).exists():
        return Response({"error": "Вы не записаны на курс"}, status=403)

    if not lang:
        lang = getattr(task, 'lang', 'python').lower()

    testcases = TestCase.objects.filter(task=task, is_active=True).order_by('order')

    status_result = "accepted"
    feedback = "All tests passed"
    errors = []

    for test in testcases:
        try:
            if lang == 'python':
                cmd = [sys.executable, '-c', code]
                run_kwargs = {'input': test.input_data, 'capture_output': True, 'timeout': 2, 'text': True}
            elif lang == 'javascript':
                cmd = ['node', '-e', code]
                run_kwargs = {'input': test.input_data, 'capture_output': True, 'timeout': 2, 'text': True}
            elif lang == 'cpp' or lang == 'c++':
                # Создаем временные файлы
                with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as src_file:
                    src_file.write(code.encode())
                    src_file_path = src_file.name
                exe_file_path = src_file_path[:-4]  # удаляем .cpp
                # Компиляция
                compile_proc = subprocess.run(['g++', src_file_path, '-o', exe_file_path],
                                              capture_output=True, text=True)
                if compile_proc.returncode != 0:
                    status_result = "error"
                    feedback = compile_proc.stderr.strip()
                    errors.append(feedback)
                    os.unlink(src_file_path)
                    break
                # Запуск бинарника
                cmd = [exe_file_path]
                run_kwargs = {'input': test.input_data, 'capture_output': True, 'timeout': 2, 'text': True}
            else:
                status_result = "error"
                feedback = f"Язык {lang} не поддерживается"
                break

            result = subprocess.run(cmd, **run_kwargs)

            if result.stderr:
                status_result = "error"
                feedback = result.stderr.strip()
                errors.append(feedback)
                break

            output = result.stdout.strip()
            if output != test.expected_output.strip():
                status_result = "rejected"
                feedback = f"Failed test {test.id}"
                break

        except subprocess.TimeoutExpired:
            status_result = "error"
            feedback = f"Timeout on test {test.id}"
            errors.append(feedback)
            break
        except Exception as e:
            status_result = "error"
            feedback = str(e)
            errors.append(feedback)
            break
        finally:
            if lang in ['cpp', 'c++']:
                if os.path.exists(src_file_path):
                    os.unlink(src_file_path)
                if os.path.exists(exe_file_path):
                    os.unlink(exe_file_path)

    submission = Submission.objects.create(
        user=request.user,
        task=task,
        code=code,
        status=status_result,
        feedback=feedback,
        errors=errors,
        lang=lang
    )

    return Response({
        "message": "Код проверен",
        "status": status_result,
        "feedback": feedback,
        "submission_id": submission.id
    })

