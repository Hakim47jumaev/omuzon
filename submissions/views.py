from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import SubmissionSerializer
from .models import Submission
from courses.models import Task, Enrollment
import google.generativeai as genai
import json
import re
from decouple import config

GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
try:
    genai.configure(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else genai.configure()
except Exception:
    pass
model = genai.GenerativeModel("gemini-2.5-flash")

ALLOWED_LANGS = {"python", "javascript", "java", "c", "cpp", "go", "ruby"}
MAX_CODE_LENGTH = 10000

def safe_json_gemini(prompt: str) -> dict:
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        return json.loads(text)
    except Exception as e:
        if 'text' in locals():
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return {
            "status": "error",
            "feedback": "AI натавонист кодро санҷад",
            "raw_error": str(e)
        }

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['task_id', 'code'],
        properties={
            'task_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID-и вазифа'),
            'code': openapi.Schema(type=openapi.TYPE_STRING, description='Коди донишҷӯ'),
            'lang': openapi.Schema(type=openapi.TYPE_STRING, description='Забони барномасозӣ', default='python'),
        },
        example={"task_id": 1, "code": "print('Салом, Тоҷикистон!')"}
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
        return Response({"error": "Вазифа ёфт нашуд"}, status=404)

    lang = request.data.get('lang', 'python').lower()

    if len(code) > MAX_CODE_LENGTH:
        return Response({"error": "Код хеле калон аст"}, status=400)
    if lang not in ALLOWED_LANGS:
        return Response({"error": "Забони дастгиришаванда нест"}, status=400)
    if not Enrollment.objects.filter(user=request.user, course=task.module.course).exists():
        return Response({"error": "Шумо ба курс сабти ном нашудаед"}, status=403)

    desc = (task.description or "").strip()
    task_text = (task.task_text or "").strip()
    problem = f"{desc}\n{task_text}" if desc else task_text
    prompt = f"""  
Шумо — низоми санҷиши код.

Забон: {lang}
Вазифа: {problem}
Код:
{code}
Талабот:
1. Кодро иҷро накун.
2. Мантиқро таҳлил кун.
3. Бо шарти вазифа мувофиқатро санҷ.

Қоидаҳо:
ВАЖНО:
- Услуб, оптимальность ё зебоии кодро баҳогузорӣ накун.
- Бо ҳалли стандартӣ муқоиса накун.
- Талаботи пинҳонро эҷод накун.
- Агар хато рӯшан набошад, ҳалли дуруст дониста шавад.
- Маслиҳат барои беҳтар кардани код дода нашавад, танҳо натиҷаи санҷиш.

Ҷавобро танҳо дар Формати JSON диҳед:
{{
  "status": "accepted" | "rejected" | "error",
  "feedback": "нишони кӯтоҳ (1-2 ҷумла, ишора ба хато)"
}}

"""

    result = safe_json_gemini(prompt)

    submission = Submission.objects.create(
        user=request.user,
        task=task,
        code=code,
        status=result.get("status", "error"),
        feedback=result.get("feedback", "Ҷавоб нест"),
        errors=[result.get("raw_error")] if result.get("raw_error") else [],
        lang=lang  # поле забон илова карда шуд
    )

    return Response({
        "message": "Код аз тарафи AI санҷида шуд",
        "result": result,
        "submission_id": submission.id
    })
