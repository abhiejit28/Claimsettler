FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY src ./src

RUN uv pip install --system --no-cache -e .
RUN python -m spacy download en_core_web_sm

ENV PYTHONUNBUFFERED=1

# Each service overrides CMD via docker-compose.yml.
CMD ["python", "-m", "claimsettler.api.main"]
