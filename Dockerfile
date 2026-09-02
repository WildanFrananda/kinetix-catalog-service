# 3.14, matching the interpreter this code is actually developed against (the repo's venv is
# python3.14). The image previously ran 3.12 while every local run used 3.14 — the two never
# executed the same bytecode. Both resolve requirements.txt identically, so the tie is broken
# in favour of the version the developer sees. (S2 / P1-CI-04)
FROM python:3.14-slim@sha256:656d12e70054d5fda18a045e2494c96701e9792dd1445f95b3d038df954f57e9

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
