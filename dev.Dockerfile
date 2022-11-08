FROM ghcr.io/bento-platform/bento_base_image:python-debian-latest

RUN pip install --no-cache-dir poetry==1.2.2 uvicorn==0.19.0

# Backwards-compatible with old BentoV2 container layout
WORKDIR /service-registry

COPY pyproject.toml pyproject.toml
COPY poetry.toml poetry.toml
COPY poetry.lock poetry.lock

# Install production + development dependencies
# Without --no-root, we get errors related to the code not being copied in yet.
# But we don't want the code here, otherwise Docker cache doesn't work well.
RUN poetry install --no-root

# Include repository in development container builds
COPY .git .git
COPY . .

RUN poetry install

CMD [ "sh", "./entrypoint.dev.sh" ]
