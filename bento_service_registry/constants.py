from __future__ import annotations

from bento_service_registry import __version__

__all__ = [
    "SERVICE_ARTIFACT",
    "SERVICE_TYPE",
    "SERVICE_NAME",
]

SERVICE_ARTIFACT = "service-registry"

# For exact implementations, this should be org.ga4gh/service-registry/1.0.0.
# In our case, most of our services diverge or will at some point, so use ca.c3g.bento as the group.
SERVICE_TYPE = {
    "group": "ca.c3g.bento",
    "artifact": SERVICE_ARTIFACT,
    "version": __version__,
}
SERVICE_NAME = "Bento Service Registry"