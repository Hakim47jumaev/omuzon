# Скрипт для запуска Celery на Windows
cd $PSScriptRoot
.venv\Scripts\Activate.ps1
celery -A core worker --pool=solo --loglevel=info
