# Bento Service Registry

![Test Status](https://github.com/bento-platform/bento_service_registry/workflows/Test/badge.svg)
![Lint Status](https://github.com/bento-platform/bento_service_registry/workflows/Lint/badge.svg)
[![codecov](https://codecov.io/gh/bento-platform/bento_service_registry/branch/master/graph/badge.svg)](https://codecov.io/gh/bento-platform/bento_service_registry)

**Author:** David Lougheed, Canadian Centre for Computational Genomics

Prototype implementation of the GA4GH [service registry API](https://github.com/ga4gh-discovery/ga4gh-service-registry/)
for the Bento platform.


## Development

### Getting set up

1. Install `poetry`:
   ```bash
   pip install poetry
   ```
2. Install project dependencies in a Poetry-managed virtual environment:
   ```bash
   poetry install
   ```

### Running the service locally

To run the service in development mode, use the following command:

```bash
poetry run python -m debugpy --listen "0.0.0.0:5678" -m uvicorn \
  "bento_service_registry.app:application" \
  --host 0.0.0.0 \
  --port "${INTERNAL_PORT}" \
  --reload
```

### Running tests

To run tests and linting, run Tox:

```bash
poetry run tox
```


## Configuration

The following environment variables are used to configure the 
`bento_service_registry` service:

```bash
# Debug mode:
BENTO_DEBUG=false

# When this is off, requests made to other services in the 
# registry will not validate SSL certificates.
BENTO_VALIDATE_SSL=true

# Following the bento_services.json 'schema'
# A JSON object of services registered in the service registry instance.
# CHORD_SERVICES also works here.
BENTO_SERVICES=bento_services.json

# Common URL base for all services
# CHORD_URL also works here.
BENTO_URL=http://127.0.0.1:5000/
BENTO_PUBLIC_URL=${BENTO_URL}  # By default, maps to the same URL - can be used for interpolation
BENTO_PORTAL_PUBLIC_URL=${BENTO_URL}  # By default, maps to the same URL - can be used for interpolation

# Timeout, in seconds (integers only), for contacting services from the JSON
CONTACT_TIMEOUT=5

# Service ID for the /service-info endpoint
SERVICE_ID=ca.c3g.bento:service-registry

# CORS origins for all requests
CORS_ORIGINS='*'

# Log level (debug/info/warning/error)
LOG_LEVEL=debug

# Authorization settings
BENTO_AUTHZ_SERVICE_URL=http://bentov2.local/api/authorization
AUTHZ_ENABLED=true
```
