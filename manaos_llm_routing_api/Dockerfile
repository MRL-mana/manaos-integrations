# LLM Routing API Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY manaos_llm_routing_api.py /app/
COPY llm_router_enhanced.py /app/
COPY llm_difficulty_analyzer.py /app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV FLASK_APP=manaos_llm_routing_api.py
ENV FLASK_ENV=production
ENV PORT=5111

EXPOSE 5111

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5111/health || exit 1

CMD ["python", "-u", "manaos_llm_routing_api.py"]
