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
# Verify that the download succeeded by checking for key files.
ENV HOME=/root
RUN python -c "\
from tf.app import use; \
use('ETCBC/bhsa', silent='deep'); \
use('ETCBC/nestle1904', silent='deep')" \
 && test -f /root/text-fabric-data/github/ETCBC/bhsa/tf/2021/otext.tf \
 && echo '=== TF pre-download OK ===' \
 && find /root/text-fabric-data -maxdepth 4 -type d | head -20

# At runtime, HOME=/data (persistent volume).
ENV HOME=/data
ENV QUIZ_DIR=/data/quizzes

EXPOSE 8000

CMD ["tf-api"]
