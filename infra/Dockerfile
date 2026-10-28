# Build:  docker build -f infra/Dockerfile -t raglab:0.2.0 .
# Run:    docker run --env-file .env -p 8000:8000 raglab:0.2.0              (API)
#         docker run --env-file .env raglab:0.2.0 ingest --config configs/prod.yaml   (batch job)

# ---- build stage: resolve + install exact versions from uv.lock ----
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
# Dependencies first (cached layer; only rebuilt when the lockfile changes)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
# Then our code
COPY src ./src
COPY api ./api
COPY configs ./configs
COPY data/sources.yaml ./data/sources.yaml
RUN uv sync --frozen --no-dev

# ---- runtime stage: no uv, no compilers, non-root ----
FROM python:3.12-slim
WORKDIR /app
COPY --from=build /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
RUN useradd --create-home app && mkdir -p /app/data && chown -R app /app/data
USER app
EXPOSE 8000
# `raglab` is the launcher created from [project.scripts]; the CMD is its subcommand.
ENTRYPOINT ["raglab"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
