FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app
COPY pyproject.toml README.md ./
COPY backend ./backend
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[production]"

WORKDIR /app/backend
RUN mkdir -p data media staticfiles
EXPOSE 8001

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8001", "--workers", "2", "--threads", "2", "--access-logfile", "-", "--error-logfile", "-"]
