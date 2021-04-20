# Bento Service Registry

![Build Status](https://api.travis-ci.com/bento-platform/bento_service_registry.svg?branch=master)
[![codecov](https://codecov.io/gh/bento-platform/bento_service_registry/branch/master/graph/badge.svg)](https://codecov.io/gh/bento-platform/bento_service_registry)

**Author:** David Lougheed, Canadian Centre for Computational Genomics

Prototype implementation of GA4GH's [service registry API](https://github.com/ga4gh-discovery/ga4gh-service-registry/)
for the Bento platform.

## Development

### Running the Service

To run the service, use the following command:

```bash
FLASK_DEBUG=True FLASK_APP=bento_service_registry.app flask run
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
# Following the chord_services.json schema
# (https://github.com/c3g/chord_singularity/blob/master/chord_services.schema.json)
# A list of services on a single domain which are registered in the service
# registry instance.
CHORD_SERVICES=chord_services.json

# Common URL base for all services
# BENTO_URL also works for this
CHORD_URL=http://127.0.0.1:5000/

# Timeout, in seconds (integers only), for contacting services from the JSON
CONTACT_TIMEOUT=1

# Service ID for the /service-info endpoint
SERVICE_ID=ca.c3g.bento:{current version}

# Python path template for the services, off of the CHORD_URL value
# Currently only supports artifact-based paths
URL_PATH_FORMAT=api/{artifact}
```
