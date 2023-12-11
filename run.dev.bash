#!/bin/bash

# Update dependencies and install module locally
/poetry_user_install_dev.bash

export ASGI_APP_FACTORY='bento_service_registry.app:create_app'

# Set default internal port to 5000
: "${INTERNAL_PORT:=5000}"

# Set default debugger port to debugpy default
: "${DEBUGGER_PORT:=5678}"

python -m debugpy --listen "0.0.0.0:${DEBUGGER_PORT}" -m uvicorn \
  --factory "${ASGI_APP_FACTORY}" \
  --host 0.0.0.0 \
  --port "${INTERNAL_PORT}" \
  --reload
