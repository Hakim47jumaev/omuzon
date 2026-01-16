"""
Конфигурация Gunicorn для production
"""
import multiprocessing

# Количество worker процессов
# Обычно: (2 x CPU cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Тип worker класса
worker_class = 'sync'

# Биндинг
bind = 'unix:/run/gunicorn.sock'

# Таймауты
timeout = 120
keepalive = 5

# Логирование
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Перезагрузка при изменении кода (только для development)
reload = False

# Имя процесса
proc_name = 'omuzon_api'

# Пользователь и группа (раскомментируйте для production)
# user = 'www-data'
# group = 'www-data'

# Максимальное количество запросов на worker перед перезапуска
max_requests = 1000
max_requests_jitter = 50

# Preload приложение для экономии памяти
preload_app = True
