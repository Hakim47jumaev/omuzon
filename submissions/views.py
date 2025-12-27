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
    lang = serializer.validated_data.get('lang', 'python').lower()

    if len(code) > MAX_CODE_LENGTH:
        return Response({"error": "Code too long"}, status=400)

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({"error": "Task not found"}, status=404)

    if not Enrollment.objects.filter(
        user=request.user,
        course=task.module.course
    ).exists():
        return Response({"error": "Not enrolled"}, status=403)

    testcases = TestCase.objects.filter(
        task=task,
        is_active=True
    ).order_by('order')

    status_result = "accepted"
    feedback = "All tests passed"
    errors = []

    for idx, test in enumerate(testcases, start=1):
        try:
            # ---------- RUN ----------
            if lang == 'python':
                cmd = [sys.executable, '-c', code]
                run_kwargs = {
                    'input': test.input_data or '',
                    'capture_output': True,
                    'timeout': 2,
                    'text': True
                }

            elif lang == 'javascript':
                cmd = ['node', '-e', code]
                run_kwargs = {
                    'input': test.input_data or '',
                    'capture_output': True,
                    'timeout': 2,
                    'text': True
                }

            elif lang in ('cpp', 'c++'):
                with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as src:
                    src.write(code.encode())
                    src_path = src.name

                exe_path = src_path[:-4]

                compile_proc = subprocess.run(
                    ['g++', src_path, '-o', exe_path],
                    capture_output=True,
                    text=True
                )

                if compile_proc.returncode != 0:
                    status_result = "error"
                    feedback = "Compilation error"
                    errors.append({
                        "test_index": idx,
                        "test_db_id": test.id,
                        "stderr": compile_proc.stderr.strip()
                    })
                    break

                cmd = [exe_path]
                run_kwargs = {
                    'input': test.input_data or '',
                    'capture_output': True,
                    'timeout': 2,
                    'text': True
                }

            else:
                return Response({"error": "Language not supported"}, status=400)

            result = subprocess.run(cmd, **run_kwargs)

            # ---------- RUNTIME ERROR ----------
            if result.stderr:
                status_result = "error"
                feedback = "Runtime error"
                errors.append({
                    "test_index": idx,
                    "test_db_id": test.id,
                    "stderr": result.stderr.strip()
                })
                break

            # ---------- CHECK ----------
            output = result.stdout.strip()
            expected = test.expected_output.strip()

            if output != expected:
                status_result = "rejected"
                feedback = f"Failed test {idx}"
                errors.append({
                    "test_index": idx,
                    "test_db_id": test.id,
                    "expected": expected,
                    "output": output
                })
                break

        except subprocess.TimeoutExpired:
            status_result = "error"
            feedback = f"Timeout on test {idx}"
            errors.append({
                "test_index": idx,
                "test_db_id": test.id,
                "error": "timeout"
            })
            break

        except Exception as e:
            status_result = "error"
            feedback = "Internal error"
            errors.append({
                "test_index": idx,
                "test_db_id": test.id,
                "error": str(e)
            })
            break

        finally:
            if lang in ('cpp', 'c++'):
                if 'src_path' in locals() and os.path.exists(src_path):
                    os.unlink(src_path)
                if 'exe_path' in locals() and os.path.exists(exe_path):
                    os.unlink(exe_path)

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
        "status": status_result,
        "feedback": feedback,
        "submission_id": submission.id
    })



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
)@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_code(request):
    """
    Запуск кода студента (Run).
    Без проверки, без сохранения.
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
    if custom_input is not None:
        used_input = str(custom_input)  # кастомный ввод, даже пустой
    else:
        test = TestCase.objects.filter(task=task, is_active=True).order_by('order').first()
        used_input = str(test.input_data) if test else ""  # первый test_case или пусто

    try:
        # ---------------- PYTHON ----------------
        if lang == 'python':
            cmd = [sys.executable, '-c', code]

            result = subprocess.run(
                cmd,
                input=used_input,
                capture_output=True,
                text=True,
                timeout=2
            )

        # ---------------- JAVASCRIPT ----------------
        elif lang == 'javascript':
            cmd = ['node', '-e', code]

            result = subprocess.run(
                cmd,
                input=used_input,
                capture_output=True,
                text=True,
                timeout=2
            )

        # ---------------- C++ ----------------
        elif lang in ('cpp', 'c++'):
            with tempfile.TemporaryDirectory() as tmp:
                cpp_file = os.path.join(tmp, 'main.cpp')
                exe_file = os.path.join(tmp, 'a.out')

                with open(cpp_file, 'w') as f:
                    f.write(code)

                compile_proc = subprocess.run(
                    ['g++', cpp_file, '-o', exe_file],
                    capture_output=True,
                    text=True
                )

                if compile_proc.returncode != 0:
                    return Response({
                        "stdout": "",
                        "stderr": compile_proc.stderr,
                        "used_input": used_input,
                        "lang": lang
                    })

                result = subprocess.run(
                    [exe_file],
                    input=used_input,
                    capture_output=True,
                    text=True,
                    timeout=2
                )

        else:
            return Response({"error": f"Язык {lang} не поддерживается"}, status=400)

    except subprocess.TimeoutExpired:
        return Response({
            "stdout": "",
            "stderr": "Execution timeout",
            "used_input": used_input,
            "lang": lang
        })

    except Exception as e:
        return Response({
            "stdout": "",
            "stderr": str(e),
            "used_input": used_input,
            "lang": lang
        })

    return Response({
        "stdout": result.stdout,
        "stderr": result.stderr,
        "used_input": used_input,
        "lang": lang
    })
