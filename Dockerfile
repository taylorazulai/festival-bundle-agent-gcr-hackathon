FROM python:3.11-slim

# Install system dependencies: CA certs for MongoDB TLS + Node.js for MCP server
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

RUN useradd -m appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY frontend/ ./frontend/
COPY data/ ./data/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["uvicorn", "src.agent_main:app", "--host", "0.0.0.0", "--port", "8080"]
