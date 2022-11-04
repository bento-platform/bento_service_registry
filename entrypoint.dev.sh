#!/bin/sh

export QUART_ENV=development
export QUART_APP=bento_service_registry.app:application
python -m debugpy --listen 0.0.0.0:5678 -m quart run
