#!/bin/bash
# Скрипт для настройки production окружения

set -e

PROJECT_DIR="/var/www/omuzon/API"
VENV_PATH="$PROJECT_DIR/.venv"

echo "=== Настройка production окружения ==="

# 1. Установка зависимостей системы
echo "Установка системных зависимостей..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv nginx redis-server

# 2. Создание директорий
echo "Создание директорий..."
sudo mkdir -p /var/www/omuzon/API
sudo mkdir -p /var/log/celery
sudo mkdir -p /run/gunicorn

# 3. Копирование systemd файлов
echo "Настройка systemd сервисов..."
sudo cp deploy/celery.service /etc/systemd/system/
sudo cp deploy/gunicorn.service /etc/systemd/system/

# 4. Настройка Nginx
echo "Настройка Nginx..."
sudo cp deploy/nginx.conf /etc/nginx/sites-available/omuzon
sudo ln -sf /etc/nginx/sites-available/omuzon /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 5. Создание виртуального окружения (если еще не создано)
if [ ! -d "$VENV_PATH" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv $VENV_PATH
fi

# 6. Установка Python зависимостей
echo "Установка Python зависимостей..."
source $VENV_PATH/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 7. Сбор статических файлов
echo "Сбор статических файлов..."
python manage.py collectstatic --noinput

# 8. Применение миграций
echo "Применение миграций..."
python manage.py migrate

# 9. Настройка прав доступа
echo "Настройка прав доступа..."
sudo chown -R www-data:www-data /var/www/omuzon
sudo chmod -R 755 /var/www/omuzon

# 10. Перезагрузка systemd и запуск сервисов
echo "Запуск сервисов..."
sudo systemctl daemon-reload
sudo systemctl enable redis
sudo systemctl enable celery
sudo systemctl enable gunicorn
sudo systemctl enable nginx

sudo systemctl start redis
sudo systemctl start celery
sudo systemctl start gunicorn
sudo systemctl restart nginx

echo "=== Готово! ==="
echo "Проверьте статус сервисов:"
echo "  sudo systemctl status redis"
echo "  sudo systemctl status celery"
echo "  sudo systemctl status gunicorn"
echo "  sudo systemctl status nginx"
