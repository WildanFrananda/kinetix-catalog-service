FROM python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir pip==26.2.2 \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# What kinetix_build_info reports. .dockerignore keeps .git out of the build context, so nothing
# in here can work the answer out from the repository's history; a build that passes nothing
# falls back to the version this repository declares for itself, in ./VERSION.
#
# The default is EMPTY, not "unknown". An ARG defaulted to a word would set the environment
# variable to that word, and the environment wins over the declared version — the fallback would
# never be reached and every image would report "unknown" no matter what ./VERSION said.
ARG SERVICE_VERSION=
ENV KINETIX_SERVICE_VERSION=${SERVICE_VERSION}

RUN useradd --system --uid 10001 --create-home --shell /usr/sbin/nologin kinetix \
    && chown -R kinetix:kinetix /app
USER kinetix

EXPOSE 8000


HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4).status == 200 else 1)" || exit 1

# gunicorn, matching what kinetix-infrastructure/compose.yaml runs. `manage.py runserver` was
# here, and it does not drain: SIGTERM kills it where it stands, mid-response. The flags are the
# compose file's; gunicorn.conf.py in /app supplies graceful_timeout, the JSON log config and the
# shared metrics directory whichever way this image is started.
CMD ["gunicorn", "config.wsgi:application", \
     "--bind=0.0.0.0:8000", "--workers=3", "--timeout=30", \
     "--access-logfile=-", "--error-logfile=-"]
