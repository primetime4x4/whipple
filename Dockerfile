FROM python:3.12-slim
ENV TZ=America/Chicago PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends     tzdata curl ca-certificates &&     rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium
COPY . .
RUN mkdir -p /app/data/bulletins /app/data/logs
EXPOSE 28813
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3     CMD curl -f http://localhost:28813/health.json || exit 1
CMD ["python", "app.py"]
