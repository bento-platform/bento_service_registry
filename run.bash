#!/bin/bash

export ASGI_APP_FACTORY='bento_service_registry.app:create_app'

# Set default internal port to 5000
: "${INTERNAL_PORT:=5000}"

uvicorn \
  --factory "${ASGI_APP_FACTORY}" \
  --workers 1 \
  --loop uvloop \
  --host 0.0.0.0 \
  --port "${INTERNAL_PORT}"
