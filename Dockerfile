FROM python:3.14-slim-bookworm

# Python
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    POETRY_HOME='/usr/local' \
    POETRY_VERSION=2.2.1

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN if [ "$ENVIRONMENT" = "development" ]; then \
    poetry install --no-ansi ; \
    else \
    poetry install --no-ansi --only=main ; \
    fi

COPY . /app

RUN chmod +x /app/run.sh

EXPOSE 8080

CMD ["/app/run.sh"]

