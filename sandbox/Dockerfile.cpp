FROM gcc:12-slim
RUN useradd -m -u 1000 runner
WORKDIR /work
USER runner
