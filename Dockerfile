FROM ghcr.io/bento-platform/bento_base_image:python-debian-latest

RUN pip install --no-cache-dir poetry==1.2.2 uvicorn==0.19.0

# Backwards-compatible with old BentoV2 container layout
WORKDIR /service-registry

COPY pyproject.toml pyproject.toml
COPY poetry.toml poetry.toml
COPY poetry.lock poetry.lock

# Install production dependencies
# Without --no-root, we get errors related to the code not being copied in yet.
# But we don't want the code here, otherwise Docker cache doesn't work well.
RUN poetry install --without dev --no-root

# Manually copy only what's relevant
# (Don't use .dockerignore, which allows us to have development containers too)
COPY bento_service_registry bento_service_registry
COPY entrypoint.sh entrypoint.sh
COPY LICENSE LICENSE
COPY README.md README.md

# Install the module itself, locally (similar to `pip install -e .`)
RUN poetry install --without dev

CMD [ "sh", "./entrypoint.sh" ]
