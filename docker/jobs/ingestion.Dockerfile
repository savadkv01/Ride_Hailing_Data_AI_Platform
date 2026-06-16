FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY ingestion/synthetic/requirements.txt /tmp/requirements.ingestion.txt
COPY ingestion/open_data/requirements.txt /tmp/requirements.open_data.txt
RUN pip install --no-cache-dir -r /tmp/requirements.ingestion.txt -r /tmp/requirements.open_data.txt \
    && pip install --no-cache-dir psycopg2-binary==2.9.10 requests==2.32.3

COPY . /app
