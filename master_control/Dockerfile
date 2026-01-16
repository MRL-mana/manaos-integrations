# Master Control Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY master_control.py /app/
COPY ultimate_integration.py /app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV FLASK_APP=master_control.py
ENV FLASK_ENV=production
ENV PORT=9700

EXPOSE 9700

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:9700/ || exit 1

CMD ["python", "-u", "master_control.py"]
