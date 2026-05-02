FROM python:3.11-slim

# MCP servers come in two flavours: Python (run via `uvx`) and Node (run via `npx`).
# Install both runtimes so config.yaml can use either.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# uv (provides `uvx` for one-shot Python tool launches)
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
