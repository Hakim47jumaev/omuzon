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
Ты — строгий компилятор и педантичный ревьюер кода. Ошибок не прощаешь..
Язык программирования: {lang}
Задача:{task.description or task.task_text}
Код студента:{code}
Проверь и ответь ТОЛЬКО в JSON:
{{
  "status": "accepted" | "rejected" | "error",
  "feedback": "ochen-ochen Краткий отзыв на russkom  shtobi ne bilo ochevidno , tolko namek"
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