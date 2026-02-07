FROM gcc:12

# создать пользователя
RUN useradd -m  runner

# создать /app и дать права runner
RUN mkdir -p /app && chown -R runner:runner /app

WORKDIR /app
USER runner

CMD ["bash"]
