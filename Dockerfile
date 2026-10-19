# Local-only OMEGA backend draft; not a production deployment.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend/server.py /app/backend/server.py
COPY backend/owner_auth_v1.py /app/backend/owner_auth_v1.py
RUN useradd --system --uid 10001 --no-create-home appuser && \
    mkdir -p /var/lib/omega && chown 10001:10001 /var/lib/omega
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=2).read()"]
CMD ["python", "/app/backend/server.py"]
