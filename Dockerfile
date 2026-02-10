FROM python:3.13-slim
WORKDIR /app

# Install Python dependencies (includes context-fabric)
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Also install text-fabric for corpus pre-download (build-time only)
RUN pip install --no-cache-dir "text-fabric>=12.0.0"

# Copy system prompts for chat
COPY system_prompt.md system_prompt_quiz.md ./

# Pre-download Text-Fabric corpora at build time.
# The .tf source files are used by Context-Fabric at runtime.
ENV HOME=/root
RUN python -c "\
from tf.app import use; \
use('ETCBC/bhsa', silent='deep'); \
use('ETCBC/nestle1904', silent='deep')" \
 && test -f /root/text-fabric-data/github/ETCBC/bhsa/tf/2021/otext.tf \
 && echo '=== Corpus pre-download OK ===' \
 && find /root/text-fabric-data -maxdepth 4 -type d | head -20

# At runtime, HOME=/data (persistent volume).
# Context-Fabric will compile .tf -> .cfm on first load.
ENV HOME=/data
ENV QUIZ_DIR=/data/quizzes

EXPOSE 8000

CMD ["tf-api"]
