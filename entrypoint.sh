#!/bin/sh

if [ -z "${INTERNAL_PORT}" ]; then
  # Set default internal port to 5000
  INTERNAL_PORT=5000
fi

hypercorn bento_service_registry.app:application \
  --workers 1 \
  -k uvloop \
  --bind "0.0.0.0:${INTERNAL_PORT}"
