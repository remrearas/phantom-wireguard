FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping curl docker.io \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements-test.txt \
 && pip install --no-cache-dir docker requests

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["sleep", "infinity"]
