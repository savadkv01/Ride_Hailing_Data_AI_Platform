FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY ml/requirements.txt /tmp/requirements.ml.txt
RUN pip install --no-cache-dir -r /tmp/requirements.ml.txt

COPY . /app
