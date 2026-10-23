FROM python:3.12-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY gateway.py /app/gateway.py
USER 10001:10001
CMD ["python", "-B", "/app/gateway.py"]
