# Unified Dashboard Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY unified_dashboard.py /app/
COPY manaos_logger.py /app/
COPY manaos_error_handler.py /app/
COPY manaos_async_client.py /app/
COPY unified_test_system.py /app/
COPY personality_autonomy_secretary_integration.py /app/
COPY learning_memory_integration.py /app/
COPY manaos_performance_optimizer.py /app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV FLASK_APP=unified_dashboard.py
ENV FLASK_ENV=production
ENV PORT=5130

EXPOSE 5130

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5130/ || exit 1

CMD ["python", "-u", "unified_dashboard.py"]
