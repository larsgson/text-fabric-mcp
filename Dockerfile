FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Copy system prompts for chat
COPY system_prompt.md system_prompt_quiz.md ./

# Pre-download Text-Fabric corpora at build time.
# This avoids GitHub API rate limits at runtime on Railway.
ENV HOME=/root
RUN python -c "from tf.app import use; use('ETCBC/bhsa', silent='deep'); use('ETCBC/nestle1904', silent='deep')"

# At runtime, HOME=/data (persistent volume) for quiz storage.
# Copy the pre-downloaded TF data into /data on first start (see entrypoint).
ENV HOME=/data
ENV QUIZ_DIR=/data/quizzes

COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
