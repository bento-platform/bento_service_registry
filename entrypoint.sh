#!/bin/sh

uvicorn bento_service_registry.app:application \
  --workers 1 \
  --host 0.0.0.0 \
  --port "${INTERNAL_PORT}"
