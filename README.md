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
