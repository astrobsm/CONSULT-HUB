FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
# Run as an unprivileged user. Pre-create the uploads dir and hand /app to the
# user so a fresh named volume mounted there inherits writable ownership.
RUN chmod +x docker-entrypoint.sh \
    && mkdir -p /app/uploads \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
