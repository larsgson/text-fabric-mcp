FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Copy system prompt for chat
COPY system_prompt.md ./

# Single persistent volume at /data holds both Text-Fabric cache and quizzes.
# Text-Fabric defaults to ~/text-fabric-data/ so we symlink it into /data.
# Quiz storage is pointed here via QUIZ_DIR env var.
RUN mkdir -p /data/text-fabric-data /data/quizzes \
    && ln -s /data/text-fabric-data /root/text-fabric-data

ENV QUIZ_DIR=/data/quizzes

EXPOSE 8000

CMD ["tf-api"]
