# Portal Voice Integration Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY portal_voice_integration.py /app/
COPY manaos_logger.py /app/
COPY manaos_error_handler.py /app/
COPY manaos_timeout_config.py /app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV FLASK_APP=portal_voice_integration.py
ENV FLASK_ENV=production
ENV PORT=5116

EXPOSE 5116

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5116/health || exit 1

CMD ["python", "-u", "portal_voice_integration.py"]
