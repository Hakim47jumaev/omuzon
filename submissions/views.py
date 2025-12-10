# submissions/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Submission
from .serializers import SubmissionSerializer
from courses.models import Task
import google.generativeai as genai
import json
import re
from decouple import config

genai.configure(api_key=config('GEMINI_API_KEY'))
model = genai.GenerativeModel("gemini-2.5-flash")   

def safe_json_gemini(prompt: str) -> dict:
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Пытаемся нормальный JSON
        return json.loads(text)
        
    except Exception as e:
        # Если упало — ищем JSON в тексте
        if 'text' in locals():
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
        return {
            "status": "error",
            "feedback": "AI не смог проверить код",
            "raw_error": str(e)
        }

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['task_id', 'code'],
        properties={
            'task_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID задачи'),
            'code': openapi.Schema(type=openapi.TYPE_STRING, description='Код студента'),
        },
        example={"task_id": 1, "code": "print('Салом, Таджикистан!')"}
    ),
    responses={200: "OK"}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_code(request):
    serializer = SubmissionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    task_id = serializer.validated_data['task_id']
    code = serializer.validated_data['code']

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({"error": "Задача не найдена"}, status=404)
    lang = request.data.get('lang', 'python').lower()
    prompt = f"""  
Ты — система проверки кода.

Язык: {lang}
Задача: {task.description and task.task_text}
Код:
{code}
Требования:
1. Запрещено выполнять код.
2. Анализируй логику.
3. Проверь на соответствие условию.
Правила:
ВАЖНО:
- Не оценивай стиль, оптимальность или красоту решения.
- Не сравнивай со стандартным/эталонным решением.
- Не придумывай скрытые требования.
- Если в ответе НЕТ очевидной ошибки, считай решение правильным.
- Не давай советы по улучшению, только факт проверки.

Отвечай только в Формат (строго JSON):
{{
  "status": "accepted" | "rejected" | "error",
  "feedback": "краткий намёк (1–2 предложения, прямого указания ошибки)"
}}

"""


    result = safe_json_gemini(prompt)

    submission = Submission.objects.create(
        user=request.user,
        task=task,
        code=code,
        status=result.get("status", "error"),
        feedback=result.get("feedback", "Нет ответа")
    )

    return Response({
        "message": "Код проверен AI",
        "result": result,
        "submission_id": submission.id
    })