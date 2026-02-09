FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Copy system prompts for chat
COPY system_prompt.md system_prompt_quiz.md ./

# Single persistent volume at /data.
# Set HOME=/data so Text-Fabric writes its cache to /data/text-fabric-data.
# Quiz storage also lives under /data via QUIZ_DIR.
ENV HOME=/data
ENV QUIZ_DIR=/data/quizzes

EXPOSE 8000

CMD ["tf-api"]
