# Инструкция по деплою на Production (Gunicorn + Nginx)

## 🚀 Быстрый старт

```bash
# 1. Скопируйте файлы на сервер
# 2. Отредактируйте пути в deploy/*.service и deploy/nginx.conf
# 3. Запустите скрипт настройки:
chmod +x deploy/setup.sh
sudo ./deploy/setup.sh
```

---

## 📋 Что нужно запустить при деплое:

### 1. Redis (для Celery)
```bash
# Через systemd (рекомендуется)
sudo systemctl start redis
sudo systemctl enable redis  # автозапуск при перезагрузке

# Или через Docker
docker run -d --name redis --restart=always -p 6379:6379 redis:7-alpine
```

### 2. Celery Worker
```bash
# Через systemd (рекомендуется)
# Создайте файл /etc/systemd/system/celery.service
```

### 3. Gunicorn (Django приложение)
```bash
# Через systemd (рекомендуется)
# Создайте файл /etc/systemd/system/gunicorn.service
```

### 4. Nginx (веб-сервер)
```bash
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

## Создание systemd сервисов

### Celery Worker Service

Создайте файл `/etc/systemd/system/celery.service`:

```ini
[Unit]
Description=Celery Service
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/project/API
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A core worker --pool=solo --loglevel=info --pidfile=/var/run/celery/celery.pid --logfile=/var/log/celery/celery.log
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl daemon-reload
sudo systemctl start celery
sudo systemctl enable celery
```

### Gunicorn Service

Создайте файл `/etc/systemd/system/gunicorn.service`:

```ini
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/project/API
ExecStart=/path/to/venv/bin/gunicorn \
    --access-logfile - \
    --workers 3 \
    --bind unix:/run/gunicorn.sock \
    core.wsgi:application

Restart=always

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
```

---

## Nginx конфигурация

Создайте файл `/etc/nginx/sites-available/omuzon`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 10M;

    location /static/ {
        alias /path/to/your/project/API/staticfiles/;
    }

    location /media/ {
        alias /path/to/your/project/API/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активация:
```bash
sudo ln -s /etc/nginx/sites-available/omuzon /etc/nginx/sites-enabled/
sudo nginx -t  # проверка конфигурации
sudo systemctl reload nginx
```

---

## Проверка статуса всех сервисов

```bash
# Проверка статуса
sudo systemctl status redis
sudo systemctl status celery
sudo systemctl status gunicorn
sudo systemctl status nginx

# Просмотр логов
sudo journalctl -u celery -f
sudo journalctl -u gunicorn -f
```

---

## Порядок запуска при перезагрузке сервера:

1. Redis (автоматически через systemd)
2. Celery Worker (автоматически через systemd)
3. Gunicorn (автоматически через systemd)
4. Nginx (автоматически через systemd)

Все сервисы настроены на автозапуск через `systemctl enable`.

---

## Важные моменты:

1. **Пути**: Замените `/path/to/your/project/API` на реальный путь к проекту
2. **Пользователь**: Обычно `www-data` или `nginx` на Linux
3. **Виртуальное окружение**: Укажите правильный путь к `.venv`
4. **Права доступа**: Убедитесь, что пользователь имеет права на директории проекта
5. **Логи**: Проверяйте логи при проблемах: `/var/log/celery/` и `journalctl`

---

## Проверка работы:

```bash
# Проверить, что все запущено
sudo systemctl status redis celery gunicorn nginx

# Проверить порты
sudo netstat -tlnp | grep -E '6379|80|8000'

# Проверить процессы
ps aux | grep -E 'celery|gunicorn|nginx|redis'
```

---

## 📝 Резюме: Что запускается при деплое

### Обязательные сервисы:

1. **Redis** (порт 6379)
   - Очередь для Celery
   - `sudo systemctl start redis`

2. **Celery Worker**
   - Обрабатывает задачи проверки кода
   - `sudo systemctl start celery`

3. **Gunicorn**
   - WSGI сервер для Django
   - `sudo systemctl start gunicorn`

4. **Nginx** (порт 80/443)
   - Reverse proxy и статические файлы
   - `sudo systemctl start nginx`

### Автозапуск:

Все сервисы настроены на автозапуск через `systemctl enable`, поэтому при перезагрузке сервера они запустятся автоматически.

### Мониторинг:

```bash
# Просмотр логов в реальном времени
sudo journalctl -u celery -f
sudo journalctl -u gunicorn -f
sudo tail -f /var/log/nginx/error.log
```

### Перезапуск сервисов:

```bash
# После изменений в коде
sudo systemctl restart gunicorn

# После изменений в Celery задачах
sudo systemctl restart celery

# После изменений в Nginx конфигурации
sudo nginx -t  # проверка
sudo systemctl reload nginx
```
