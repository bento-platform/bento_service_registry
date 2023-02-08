# Bento Service Registry

![Test Status](https://github.com/bento-platform/bento_service_registry/workflows/Test/badge.svg)
![Lint Status](https://github.com/bento-platform/bento_service_registry/workflows/Lint/badge.svg)
[![codecov](https://codecov.io/gh/bento-platform/bento_service_registry/branch/master/graph/badge.svg)](https://codecov.io/gh/bento-platform/bento_service_registry)

**Author:** David Lougheed, Canadian Centre for Computational Genomics

Prototype implementation of the GA4GH [service registry API](https://github.com/ga4gh-discovery/ga4gh-service-registry/)
for the Bento platform.


## Development

### Getting set up

1. Create a virtual environment for the project:
   ```bash
   virtualenv -p python3 ./env
   source env/bin/activate
   ```
2. Install `poetry`:
   ```bash
   pip install poetry
   ```
3. Install project dependencies:
   ```bash
   poetry install
   ```

### Running the service locally

To run the service in development mode, use the following command:

```bash
QUART_ENV=development QUART_APP=bento_service_registry.app quart run
```

### Running tests

To run tests and linting, run Tox:

```bash
tox
```


## Configuration

The following environment variables are used to configure the 
`bento_service_registry` service:

```bash
# Debug mode:
# Setting FLASK_ENV=development will set this to True as well as enabling Flask 
# debug mode.
CHORD_DEBUG=False

# When this is off, requests made to other services in the 
# registry will not validate SSL certificates. Defaults to (not CHORD_DEBUG)
BENTO_VALIDATE_SSL=True

# Following the bento_services.json 'schema'
# A JSON object of services registered in the service registry instance.
# CHORD_SERVICES also works here.
BENTO_SERVICES=bento_services.json

# Common URL base for all services
# BENTO_URL also works here.
CHORD_URL=http://127.0.0.1:5000/

# Timeout, in seconds (integers only), for contacting services from the JSON
CONTACT_TIMEOUT=1

# Service ID for the /service-info endpoint
SERVICE_ID=ca.c3g.bento:{current version}

# Python path template for the services, off of the CHORD_URL value
# Currently only supports artifact-based paths
URL_PATH_FORMAT=api/{artifact}
```
