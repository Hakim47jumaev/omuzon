# Техническое задание API для фронтенда

## Базовый URL
```
http://your-domain.com/api/
```

## Аутентификация
Все защищенные эндпоинты требуют JWT токен в заголовке:
```
Authorization: Bearer <access_token>
```

---

## 1. ACCOUNTS (Аккаунты)

### 1.1. Регистрация
**POST** `/api/accounts/register/`

**Тело запроса:**
```json
{
  "username": "string (max 150)",
  "email": "string (email)",
  "password": "string (min 6)"
}
```

**Успешный ответ (200):**
```json
{
  "message": "Verification code sent to your email."
}
```

**Ошибки:**
- `400` - Email уже зарегистрирован или код уже отправлен
- `400` - Username уже занят

---

### 1.2. Подтверждение кода
**POST** `/api/accounts/verify/`

**Тело запроса:**
```json
{
  "email": "string (email)",
  "verification_code": "string (4 цифры)"
}
```

**Успешный ответ (201):**
```json
{
  "message": "Account created successfully.",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "user",
    "first_name": "",
    "last_name": ""
  },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Ошибки:**
- `400` - Неверный или истекший код

---

### 1.3. Вход
**POST** `/api/accounts/login/`

**Тело запроса:**
```json
{
  "login": "string (username или email)",
  "password": "string"
}
```

**Успешный ответ (200):**
```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "user",
    "first_name": "",
    "last_name": ""
  },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Ошибки:**
- `400` - Неверный логин или пароль
- `400` - Аккаунт отключен

---

### 1.4. Выход
**POST** `/api/accounts/logout/`

**Требует аутентификации:** Нет

**Успешный ответ (200):**
```json
{
  "message": "Logged out."
}
```

---

### 1.5. Профиль (GET)
**GET** `/api/accounts/profile/`

**Требует аутентификации:** Да

**Успешный ответ (200):**
```json
{
  "id": 1,
  "user": "username",
  "avatar": "http://domain.com/media/avatars/avatar.jpg",
  "bio": "Bio text"
}
```

---

### 1.6. Профиль (UPDATE)
**PUT/PATCH** `/api/accounts/profile/`

**Требует аутентификации:** Да

**Тело запроса (multipart/form-data):**
```
avatar: File (необязательно)
bio: string (необязательно)
```

**Успешный ответ (200):**
```json
{
  "id": 1,
  "user": "username",
  "avatar": "http://domain.com/media/avatars/avatar.jpg",
  "bio": "Updated bio"
}
```

---

### 1.7. Статистика обучения
**GET** `/api/accounts/profile/education/`

**Требует аутентификации:** Да

**Успешный ответ (200):**
```json
{
  "summary": {
    "enrolled_courses": 5,
    "completed_courses": 2,
    "in_progress_courses": 3,
    "total_solved_tasks": 15,
    "total_submissions": 45,
    "tasks_per_day": [
      {
        "date": "2024-01-15",
        "solved_tasks": 3
      },
      {
        "date": "2024-01-16",
        "solved_tasks": 5
      }
    ]
  },
  "courses": [
    {
      "course_id": 1,
      "title": "Python Basics",
      "start_time": "2024-01-01T10:00:00Z",
      "is_active": true,
      "status": "in_progress",
      "progress_percent": 65.5,
      "solved_tasks": 13,
      "total_tasks": 20,
      "tasks_per_day": [
        {
          "date": "2024-01-15",
          "solved_tasks": 2
        }
      ]
    }
  ]
}
```

**Примечание:** `status` может быть: `"not_started"`, `"in_progress"`, `"completed"`

---

### 1.8. Google Sign In
**POST** `/api/accounts/google-signin/`

**Требует аутентификации:** Нет

**Тело запроса:**
```json
{
  "id_token": "string (Google ID token)",
  "email": "string (email)",
  "display_name": "string (необязательно)"
}
```

**Успешный ответ (200):**
```json
{
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "name": "User Name"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**Ошибки:**
- `400` - Неверный Google token
- `400` - Email не совпадает

---

## 2. COURSES (Курсы)

### 2.1. Список курсов
**GET** `/api/courses/courses/`

**Требует аутентификации:** Нет

**Query параметры:**
- `search` - поиск по title и description
- `ordering` - сортировка: `start_time`, `title`, `enrolled_count` (можно с `-` для обратного порядка)

**Успешный ответ (200):**
```json
[
  {
    "id": 1,
    "title": "Python Basics",
    "description": "Learn Python",
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": null,
    "is_active": true,
    "is_olimpiad": false,
    "is_olimpiad_active": false,
    "is_olimpiad_finished": false,
    "enrolled_count": 150
  }
]
```

---

### 2.2. Детали курса
**GET** `/api/courses/courses/<course_id>/`

**Требует аутентификации:** Нет

**Успешный ответ (200):**
```json
{
  "id": 1,
  "title": "Python Basics",
  "description": "Learn Python",
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": null,
  "is_olimpiad": false,
  "is_olimpiad_active": false,
  "is_olimpiad_finished": false,
  "is_enrolled": true,
  "solved_tasks_count": 5,
  "total_tasks": 10,
  "progress_percent": 50.0,
  "modules": [
    {
      "id": 1,
      "title": "Module 1",
      "description": "First module",
      "order": 1,
      "tasks": [
        {
          "id": 1,
          "title": "Task 1",
          "description": "Task description",
          "task_text": "Full task text",
          "order": 1,
          "is_solved": true,
          "last_submission": {
            "id": 123,
            "status": "accepted",
            "feedback": "All tests passed",
            "created_at": "2024-01-15T12:00:00Z",
            "code": "print('Hello')",
            "lang": "python"
          },
          "my_submissions": [
            {
              "id": 123,
              "status": "accepted",
              "feedback": "All tests passed",
              "created_at": "2024-01-15T12:00:00Z",
              "code": "print('Hello')",
              "lang": "python"
            }
          ],
          "testcases": [
            {
              "id": 1,
              "input_data": "5",
              "expected_output": "10",
              "is_active": true,
              "order": 1
            }
          ]
        }
      ]
    }
  ]
}
```

**Если курс не начался (200):**
```json
{
  "detail": "Курс ещё не начался. Доступ будет открыт после даты начала.",
  "start_time": "2024-01-01T10:00:00Z",
  "title": "Python Basics"
}
```

**Если олимпиада не началась (200):**
```json
{
  "detail": "Олимпиада ещё не началась. Доступ будет открыт после даты начала.",
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": "2024-01-01T12:00:00Z",
  "title": "Олимпиада",
  "is_olimpiad": true
}
```

**Если олимпиада завершена (200):**
```json
{
  "detail": "Олимпиада завершена. Результаты зафиксированы.",
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": "2024-01-01T12:00:00Z",
  "title": "Олимпиада",
  "is_olimpiad": true,
  "is_finished": true
}
```

**Ошибки:**
- `404` - Курс не найден

**Примечание:** 
- `last_submission` и `my_submissions` могут быть `null` или `[]` если нет сабмитов
- `is_solved` - `false` для неавторизованных пользователей
- Статусы submission: `"pending"`, `"accepted"`, `"rejected"`, `"error"`

---

### 2.3. Мои курсы
**GET** `/api/courses/courses/enrolled/`

**Требует аутентификации:** Да

**Успешный ответ (200):**
```json
[
  {
    "id": 1,
    "title": "Python Basics",
    "description": "Learn Python",
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": null,
    "is_active": true,
    "is_olimpiad": false,
    "is_olimpiad_active": false,
    "is_olimpiad_finished": false,
    "enrolled_count": 150
  }
]
```

---

### 2.4. Запись на курс
**POST** `/api/courses/courses/enroll/`

**Требует аутентификации:** Да

**Тело запроса:**
```json
{
  "course_id": 1
}
```

**Успешный ответ (201):**
```json
{
  "message": "Успешно записан на курс"
}
```

**Если уже записан (200):**
```json
{
  "message": "Вы уже записаны на этот курс"
}
```

**Ошибки:**
- `400` - `course_id` обязателен
- `404` - Курс не найден

---

### 2.5. Детали модуля
**GET** `/api/courses/modules/<module_id>/`

**Требует аутентификации:** Нет

**Успешный ответ (200):**
```json
{
  "id": 1,
  "title": "Module 1",
  "description": "First module",
  "order": 1,
  "tasks": [
    {
      "id": 1,
      "title": "Task 1",
      "description": "Task description",
      "task_text": "Full task text",
      "order": 1,
      "is_solved": false,
      "last_submission": null,
      "my_submissions": [],
      "testcases": [
        {
          "id": 1,
          "input_data": "5",
          "expected_output": "10",
          "is_active": true,
          "order": 1
        }
      ]
    }
  ]
}
```

---

### 2.6. Детали задачи
**GET** `/api/courses/tasks/<task_id>/`

**Требует аутентификации:** Нет

**Успешный ответ (200):**
```json
{
  "id": 1,
  "title": "Task 1",
  "description": "Task description",
  "task_text": "Full task text",
  "order": 1,
  "is_solved": false,
  "last_submission": null,
  "my_submissions": [],
  "testcases": [
    {
      "id": 1,
      "input_data": "5",
      "expected_output": "10",
      "is_active": true,
      "order": 1
    }
  ]
}
```

---

### 2.7. Лидерборд олимпиады
**GET** `/api/courses/courses/<course_id>/leaderboard/`

**Требует аутентификации:** Нет

**Успешный ответ (200):**
```json
{
  "course": {
    "id": 1,
    "title": "Олимпиада по программированию",
    "is_olimpiad": true,
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": "2024-01-01T12:00:00Z",
    "is_finished": false
  },
  "leaderboard": [
    {
      "rank": 1,
      "user_id": 1,
      "username": "user1",
      "solved_count": 5,
      "submission_count": 8,
      "last_accepted_at": "2024-01-01T11:30:00Z"
    },
    {
      "rank": 2,
      "user_id": 2,
      "username": "user2",
      "solved_count": 5,
      "submission_count": 10,
      "last_accepted_at": "2024-01-01T11:35:00Z"
    }
  ]
}
```

**Ошибки:**
- `400` - Курс не является олимпиадой
- `404` - Курс не найден

**Примечание:** Сортировка: больше решённых задач → меньше попыток → раньше последний ACCEPTED

---

### 2.8. Создание курса (Admin)
**POST** `/api/courses/courses/create/`

**Требует аутентификации:** Да

**Тело запроса:**
```json
{
  "title": "string",
  "description": "string",
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": "2024-01-01T12:00:00Z",
  "is_olimpiad": false
}
```

**Успешный ответ (201):**
```json
{
  "id": 1,
  "title": "Python Basics",
  "description": "Learn Python",
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": null,
  "is_active": true,
  "is_olimpiad": false,
  "is_olimpiad_active": false,
  "is_olimpiad_finished": false,
  "enrolled_count": 0
}
```

---

### 2.9. Обновление курса (Admin)
**PUT/PATCH** `/api/courses/courses/<course_id>/update/`

**Требует аутентификации:** Да (только владелец)

**Тело запроса:** (те же поля, что и при создании)

**Успешный ответ (200):** (те же поля, что и при создании)

---

### 2.10. Удаление курса (Admin)
**DELETE** `/api/courses/courses/<course_id>/delete/`

**Требует аутентификации:** Да (только владелец)

**Успешный ответ (204):** Без тела

---

## 3. SUBMISSIONS (Отправка кода)

### 3.1. Отправка кода на проверку
**POST** `/api/submissions/submit-code/`

**Требует аутентификации:** Да

**Тело запроса:**
```json
{
  "task_id": 1,
  "code": "print('Hello World')",
  "lang": "python"
}
```

**Успешный ответ (202):**
```json
{
  "submission_id": 123,
  "status": "pending"
}
```

**Ошибки:**
- `400` - Ошибка валидации или код слишком длинный (max 10000 символов)
- `403` - Пользователь не записан на курс
- `403` - Олимпиада ещё не началась / завершена
- `404` - Задача не найдена
- `429` - Превышен лимит отправок (максимум 10 в минуту для олимпиад)

**Примечание:** 
- Проверка выполняется асинхронно
- Используйте `get_submission` для получения результата
- Поддерживаемые языки: `"python"`, `"cpp"`, `"c++"` (по умолчанию `"python"`)

---

### 3.2. Запуск кода (без проверки)
**POST** `/api/submissions/run-code/`

**Требует аутентификации:** Да

**Тело запроса:**
```json
{
  "task_id": 1,
  "code": "a=int(input())\nprint('You entered a number', a)",
  "input": "11",
  "lang": "python"
}
```

**Успешный ответ (200):**
```json
{
  "stdout": "You entered a number 11",
  "stderr": "",
  "used_input": "11",
  "lang": "python"
}
```

**Ошибки:**
- `400` - `task_id` и `code` обязательны
- `400` - Код слишком длинный
- `404` - Задача не найдена

**Примечание:**
- Если `input` не передан, используется первый тест-кейс задачи
- Если тест-кейсов нет, используется пустой ввод
- Выполнение синхронное, но в Docker контейнере

---

### 3.3. Получение результата проверки
**GET** `/api/submissions/<submission_id>/`

**Требует аутентификации:** Да

**Успешный ответ (200):**
```json
{
  "id": 123,
  "status": "accepted",
  "feedback": "All tests passed",
  "errors": [],
  "code": "print('Hello')",
  "lang": "python",
  "created_at": "2024-01-15T12:00:00Z",
  "task_id": 1,
  "task_title": "Task 1"
}
```

**Если статус pending:**
```json
{
  "id": 123,
  "status": "pending",
  "feedback": "Проверка в процессе...",
  "errors": [],
  "code": "print('Hello')",
  "lang": "python",
  "created_at": "2024-01-15T12:00:00Z",
  "task_id": 1,
  "task_title": "Task 1"
}
```

**Если ошибка:**
```json
{
  "id": 123,
  "status": "error",
  "feedback": "Ошибка выполнения: ...",
  "errors": [
    {
      "error": "Error message",
      "traceback": "Traceback..."
    }
  ],
  "code": "print('Hello')",
  "lang": "python",
  "created_at": "2024-01-15T12:00:00Z",
  "task_id": 1,
  "task_title": "Task 1"
}
```

**Ошибки:**
- `404` - Submission not found

**Статусы:**
- `"pending"` - На проверке
- `"accepted"` - Принято
- `"rejected"` - Отклонено
- `"error"` - Ошибка

---

## 4. JWT TOKENS

### 4.1. Получение токенов
**POST** `/api/token/`

**Требует аутентификации:** Нет

**Тело запроса:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Успешный ответ (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

### 4.2. Обновление токена
**POST** `/api/token/refresh/`

**Требует аутентификации:** Нет

**Тело запроса:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Успешный ответ (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## Важные замечания

1. **Формат дат:** Все даты в формате ISO 8601: `"2024-01-15T12:00:00Z"`

2. **Заголовки:**
   - Для аутентификации: `Authorization: Bearer <access_token>`
   - Для загрузки файлов: `Content-Type: multipart/form-data`

3. **Статусы submission:**
   - `"pending"` - На проверке
   - `"accepted"` - Принято
   - `"rejected"` - Отклонено
   - `"error"` - Ошибка

4. **Языки программирования:**
   - `"python"` (по умолчанию)
   - `"cpp"` или `"c++"`

5. **Олимпиадный режим:**
   - Проверка времени начала/окончания
   - Лимит 10 отправок в минуту
   - Учитываются только сабмиты в рамках времени олимпиады

6. **Polling для submission:**
   - После отправки кода (`submit-code`) получаете `submission_id`
   - Используйте `get_submission` для проверки статуса
   - Рекомендуется polling каждые 1-2 секунды до изменения статуса с `"pending"`

7. **Ошибки валидации:**
   - Всегда возвращаются в формате:
   ```json
   {
     "field_name": ["Error message"]
   }
   ```
   или
   ```json
   {
     "error": "Error message"
   }
   ```
