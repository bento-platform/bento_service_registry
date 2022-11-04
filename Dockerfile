FROM ghcr.io/bento-platform/bento_base_image:python-debian-latest

RUN pip install --no-cache-dir poetry==1.2.2 uvicorn==0.19.0

WORKDIR /app

COPY pyproject.toml pyproject.toml
COPY poetry.toml poetry.toml
COPY poetry.lock poetry.lock

# Install production dependencies
RUN poetry install --without dev

COPY . .

# Install the module itself, locally (similar to `pip install -e .`)
RUN poetry install --without dev

CMD [ "sh", "./entrypoint.sh" ]
