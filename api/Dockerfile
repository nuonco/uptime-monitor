FROM python:3.14

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install python dependencies
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"

# Install playwright browsers
RUN /app/.venv/bin/playwright install --with-deps chromium

COPY . /app
ENV PYTHONPATH=/app
CMD ["fastapi", "dev", "--host", "0.0.0.0", "--port", "8000", "main.py"]
