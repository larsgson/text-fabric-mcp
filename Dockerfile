FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Copy system prompts for chat
COPY system_prompt.md system_prompt_quiz.md ./

# Single persistent volume at /data holds both Text-Fabric cache and quizzes.
# Text-Fabric defaults to ~/text-fabric-data/ so we symlink it into /data.
# Quiz storage is pointed here via QUIZ_DIR env var.
# The volume is mounted at /data at runtime; subdirectories are created on startup.
# The symlink lets Text-Fabric find its cache at ~/text-fabric-data -> /data/text-fabric-data.
RUN ln -s /data/text-fabric-data /root/text-fabric-data

ENV QUIZ_DIR=/data/quizzes

EXPOSE 8000

CMD ["tf-api"]
