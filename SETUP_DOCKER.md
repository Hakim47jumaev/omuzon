# Настройка Docker Sandbox для выполнения кода

## Шаг 1: Сборка Docker образов

Перейдите в директорию `sandbox/` и соберите образы:

```bash
cd sandbox/

# Python
docker build -t code-runner-python -f Dockerfile .

# Node.js (JavaScript)
docker build -t code-runner-node -f Dockerfile.node .

# C++ (GCC)
docker build -t code-runner-cpp -f Dockerfile.cpp .
```

## Шаг 2: Запуск Redis (для Celery)

```bash
# Windows (Docker Desktop)
docker run -d -p 6379:6379 redis:7-alpine

# Linux/Mac
docker run -d -p 6379:6379 redis:7-alpine
```

## Шаг 3: Запуск Celery Worker

В отдельном терминале:

```bash
celery -A core worker --loglevel=info
```

## Шаг 4: Запуск Django сервера

```bash
python manage.py runserver
```

## Как это работает

1. **`/api/submissions/run-code/`** - Запускает код синхронно в Docker (для тестирования)
2. **`/api/submissions/submit-code/`** - Отправляет код на проверку асинхронно через Celery
3. **`/api/submissions/check-status/<task_id>/`** - Проверяет статус выполнения задачи

### Пример использования:

```python
# 1. Отправить код на проверку
POST /api/submissions/submit-code/
{
    "task_id": 1,
    "code": "print('Hello')",
    "lang": "python"
}

# Ответ:
{
    "message": "Code submission started",
    "task_id": "abc123...",
    "status": "pending"
}

# 2. Проверить статус
GET /api/submissions/check-status/abc123.../

# Ответ (когда готово):
{
    "status": "SUCCESS",
    "submission_id": 42,
    "result": {
        "status": "accepted",
        "feedback": "All tests passed",
        "errors": []
    }
}
```

## Безопасность

Все контейнеры запускаются с:
- ✅ Непривилегированным пользователем
- ✅ Ограничением памяти (256MB)
- ✅ Ограничением CPU (0.5)
- ✅ Отключенной сетью
- ✅ Read-only файловой системой
- ✅ Временной файловой системой для /tmp
