# Local-only deployment draft for PROJECT OMEGA.
# Not a production deployment; review proxy/auth/rate-limit behavior before public exposure.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app
COPY backend/server.py /app/backend/server.py

RUN useradd --system --uid 10001 --no-create-home appuser
USER 10001:10001

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=2).read()"]

CMD ["python", "/app/backend/server.py"]
