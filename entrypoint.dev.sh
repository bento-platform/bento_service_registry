#!/bin/sh

export QUART_ENV=development
export QUART_APP=bento_service_registry.app:application

if [ -z "${INTERNAL_PORT}" ]; then
  # Set default internal port to 5000
  INTERNAL_PORT=5000
fi

python -m poetry install
python -m debugpy --listen 0.0.0.0:5678 -m quart run --host 0.0.0.0 --port "${INTERNAL_PORT}"
