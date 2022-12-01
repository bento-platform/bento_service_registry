#!/bin/sh

if [ -z "${INTERNAL_PORT}" ]; then
  # Set default internal port to 5000
  INTERNAL_PORT=5000
fi

uvicorn bento_service_registry.app:application \
  --workers 1 \
  --loop uvloop \
  --host 0.0.0.0 \
  --port "${INTERNAL_PORT}"
