FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files ONLY (better cache)
COPY pyproject.toml uv.lock ./

# Install dependencies (prod only)
RUN uv sync --no-dev

# Copy application code
COPY . .

EXPOSE 8000

# Run migrations ONCE and start server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run gunicorn -k uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:8000 app.main:app"]
