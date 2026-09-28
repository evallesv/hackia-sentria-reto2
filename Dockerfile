FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/sentria
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
