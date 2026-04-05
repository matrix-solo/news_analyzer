FROM python:3.9-slim

LABEL maintainer="News Analyzer Team"
LABEL description="新闻分析工作流系统"

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=Asia/Shanghai

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY requirements.txt requirements.lock ./

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.lock

COPY . .

RUN mkdir -p data logs backups reports output

RUN chmod +x scripts/*.bat scripts/*.ps1 2>/dev/null || true

VOLUME ["/app/data", "/app/logs", "/app/backups", "/app/reports"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/app/data/news.db')" || exit 1

CMD ["python", "run_scheduler.py"]
