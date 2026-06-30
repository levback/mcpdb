FROM python:3.13-slim AS builder

ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.4"

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev --no-editable

FROM gcr.io/distroless/python3-debian12:nonroot

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder --chown=65532:65532 /app/.venv /app/.venv

USER 65532:65532
CMD ["python3", "-m", "mcpdb"]