FROM ghcr.io/bento-platform/bento_base_image:python-debian-2024.09.01

# Backwards-compatible with old BentoV2 container layout
WORKDIR /service-registry

COPY pyproject.toml .
COPY poetry.lock .

# Install production dependencies
# Without --no-root, we get errors related to the code not being copied in yet.
# But we don't want the code here, otherwise Docker cache doesn't work well.
RUN poetry config virtualenvs.create false && \
    poetry install --without dev --no-root

# Manually copy only what's relevant
# (Don't use .dockerignore, which allows us to have development containers too)
COPY bento_service_registry bento_service_registry
COPY run.bash .
COPY LICENSE .
COPY README.md .

# Install the module itself, locally (similar to `pip install -e .`)
RUN poetry install --without dev

CMD [ "/bin/bash", "./run.bash" ]
