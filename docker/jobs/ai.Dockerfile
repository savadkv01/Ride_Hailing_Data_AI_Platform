FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY vector/requirements.txt /tmp/requirements.vector.txt
COPY rag/requirements.txt /tmp/requirements.rag.txt
RUN pip install --no-cache-dir -r /tmp/requirements.vector.txt -r /tmp/requirements.rag.txt \
    && pip install --no-cache-dir psycopg2-binary==2.9.10

COPY . /app
