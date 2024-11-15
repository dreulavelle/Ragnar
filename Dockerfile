FROM ollama/ollama:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-distutils \
    python3-pip \
    && pip install poetry \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/ollama /app/data /ollama && \
    chmod 777 /app/ollama /app/data /ollama
    
ENV PATH="/usr/local/bin:/root/.local/bin:/app/ollama/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    FORCE_COLOR=1 \
    TERM=xterm-256color \
    POETRY_PYTHON=/usr/bin/python3.11 \
    OLLAMA_HOST=0.0.0.0 \
    OLLAMA_DEBUG=0

WORKDIR /app
COPY pyproject.toml poetry.lock ./

RUN mkdir -p /app/ollama/.cache/pypoetry && \
    poetry install --without dev

COPY src/ ./src/
COPY start.sh ./
RUN chmod +x start.sh
EXPOSE 11434

ENTRYPOINT []
CMD ["./start.sh"]
