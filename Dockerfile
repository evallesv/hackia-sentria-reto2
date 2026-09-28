FROM python:3.13-slim-bookworm@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/sentria
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr=5.3.0-2 \
        tesseract-ocr-spa=1:4.1.0-2 tesseract-ocr-eng=1:4.1.0-2 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt \
    && useradd --create-home --uid 10001 sentria \
    && mkdir -p /srv/sentria/storage/uploads \
    && chown -R sentria:sentria /srv/sentria
COPY --chown=sentria:sentria app ./app
COPY --chown=sentria:sentria templates ./templates
COPY --chown=sentria:sentria static ./static
COPY --chown=sentria:sentria data/demo ./data/demo
COPY --chown=sentria:sentria alembic.ini ./
COPY --chown=sentria:sentria migrations ./migrations
USER sentria
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
