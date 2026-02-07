FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Copy system prompt for chat
COPY system_prompt.md ./

# Create quizzes directory (mount as volume for persistence)
RUN mkdir -p /app/quizzes

# Text-Fabric stores data in ~/text-fabric-data/ (hardcoded to $HOME).
# In Docker, HOME=/root, so the cache lives at /root/text-fabric-data/.
# Mount a volume there to persist across deploys and avoid re-downloading.

EXPOSE 8000

CMD ["tf-api"]
