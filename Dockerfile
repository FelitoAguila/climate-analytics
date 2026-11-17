# Image of the `pipelines` package: it runs `update-neon` (or `load-neon`) without installing
# Python, uv or any dependency. The connection string never goes into the image: it is passed
# when the container starts.
#
#   docker build -t climate-pipelines .
#   docker run --rm -e DATABASE_URL climate-pipelines                         # update-neon
#   docker run --rm -e DATABASE_URL climate-pipelines update-neon --limit 2

FROM python:3.12-slim

# uv, at the same version as the workflows, copied from its official image
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# 1. The dependencies only. Docker reuses this layer (the slowest one) while uv.lock and the
#    pyproject files do not change, so a change in the code rebuilds in seconds.
#    uv needs the pyproject of every workspace member to check uv.lock.
COPY pyproject.toml uv.lock ./
COPY packages/pipelines/pyproject.toml packages/pipelines/
COPY packages/analysis/pyproject.toml packages/analysis/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package pipelines --no-install-workspace

# 2. The code of the package
COPY packages/pipelines packages/pipelines
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package pipelines --no-editable

# 3. Run as a normal user, not as root
RUN useradd --create-home app
USER app
ENV PATH="/app/.venv/bin:$PATH"

# The default command; any other is given after the image name
CMD ["update-neon"]
