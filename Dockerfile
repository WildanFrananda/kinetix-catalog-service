FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --system --uid 10001 --create-home --shell /usr/sbin/nologin kinetix \
    && chown -R kinetix:kinetix /app
USER kinetix

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
