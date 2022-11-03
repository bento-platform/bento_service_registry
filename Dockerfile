FROM ghcr.io/bento-platform/bento_base_image:python-debian-latest

RUN pip install --no-cache-dir poetry==1.2.2 uvicorn==0.19.0

WORKDIR /app

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock

# Install production dependencies
RUN poetry install --without dev

COPY . .

RUN poetry install

CMD [ "sh", "./entrypoint.sh" ]
