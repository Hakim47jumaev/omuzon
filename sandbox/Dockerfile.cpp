FROM gcc:12-slim

# создаём непривилегированного пользователя
RUN useradd -m -u 1000 runner

# удаляем ненужные пакеты для уменьшения размера образа
RUN apt-get update && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# рабочая директория
WORKDIR /app

# переключаемся на НЕ root
USER runner

# по умолчанию контейнер просто ждёт команду
CMD ["g++"]
