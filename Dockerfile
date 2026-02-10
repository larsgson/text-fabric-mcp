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

# Pre-compile .cfm caches at build time to avoid memory spike at runtime.
# Each corpus is compiled in a SEPARATE Python process so memory is freed
# between them (BHSA alone needs ~3.5 GiB during compilation).

# 1) Compile Hebrew (BHSA)
RUN python -c "\
import cfabric; \
CF = cfabric.Fabric(locations='/root/text-fabric-data/github/ETCBC/bhsa/tf/2021', silent=True); \
CF.loadAll(silent=True); \
print('Compiled: BHSA')" \
 && test -d /root/text-fabric-data/github/ETCBC/bhsa/tf/2021/.cfm \
 && echo '=== BHSA .cfm OK ==='

# 2) Compile Greek (Nestle1904) — hide nodeId.tf first (int32 overflow in CF 0.5.x)
RUN mv /root/text-fabric-data/github/ETCBC/nestle1904/tf/*/nodeId.tf \
       /root/text-fabric-data/github/ETCBC/nestle1904/tf/nodeId.tf._skip 2>/dev/null; \
    python -c "\
import cfabric; \
CF = cfabric.Fabric(locations='/root/text-fabric-data/github/ETCBC/nestle1904/tf/0.4.0', silent=True); \
CF.loadAll(silent=True); \
print('Compiled: Nestle1904')" \
 && mv /root/text-fabric-data/github/ETCBC/nestle1904/tf/nodeId.tf._skip \
       /root/text-fabric-data/github/ETCBC/nestle1904/tf/*/nodeId.tf 2>/dev/null; \
    test -d /root/text-fabric-data/github/ETCBC/nestle1904/tf/0.4.0/.cfm \
 && echo '=== Nestle1904 .cfm OK ==='

# At runtime, HOME=/data (persistent volume).
# Pre-compiled .cfm caches are copied to the volume on first boot.
ENV HOME=/data
ENV QUIZ_DIR=/data/quizzes

EXPOSE 8000

CMD ["tf-api"]
