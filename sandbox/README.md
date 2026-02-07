# Docker Sandbox для выполнения кода

Этот каталог содержит Dockerfile'ы для безопасного выполнения кода студентов в изолированных контейнерах.

## Сборка образов

### Python
```bash
docker build -t code-runner-python -f Dockerfile .
```

### Node.js (JavaScript)
```bash
docker build -t code-runner-node -f Dockerfile.node .
```

### C++ (GCC)
```bash
docker build -t code-runner-cpp -f Dockerfile.cpp .
```

## Безопасность

Все образы настроены с:
- Непривилегированным пользователем (runner)
- Ограничениями памяти (256MB)
- Ограничениями CPU (0.5)
- Отключенной сетью
- Read-only файловой системой (кроме /tmp)

## Использование

Образы используются автоматически через `submissions/docker_runner.py` и Celery задачи.
