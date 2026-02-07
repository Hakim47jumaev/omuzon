@echo off
cd /d %~dp0
call .venv\Scripts\activate.bat
celery -A core worker --pool=solo --loglevel=info
pause
