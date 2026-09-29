# syntax=docker/dockerfile:1
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN addgroup --system parksmart && adduser --system --ingroup parksmart parksmart

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=parksmart:parksmart . .
RUN mkdir -p /app/instance && chown -R parksmart:parksmart /app/instance

USER parksmart
EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "90", "run:app"]
