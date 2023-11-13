FROM ghcr.io/bento-platform/bento_base_image:python-debian-2023.11.10

RUN pip install --no-cache-dir "uvicorn[standard]==0.24.0"

# Backwards-compatible with old BentoV2 container layout
WORKDIR /service-registry

COPY pyproject.toml .
COPY poetry.lock .

# Install production + development dependencies
# Without --no-root, we get errors related to the code not being copied in yet.
# But we don't want the code here, otherwise Docker cache doesn't work well.
RUN poetry config virtualenvs.create false && poetry install --no-root

# Copy entrypoint and runner script in, so we have something to start with - even though it'll get
# overwritten by volume mount.
COPY run.dev.bash .

CMD [ "/bin/bash", "./run.dev.bash" ]
