from bento_lib.service_info.types import GA4GHServiceType

__all__ = [
    "BENTO_SERVICE_KIND",
    "SERVICE_TYPE",
]

BENTO_SERVICE_KIND: str = "service-registry"

# For exact implementations, this should be org.ga4gh/service-registry/1.0.0.
# In our case, most of our services diverge or will at some point, so use ca.c3g.bento as the group.
SERVICE_TYPE: GA4GHServiceType = {
    "group": "ca.c3g.bento",
    "artifact": "service-registry",
    "version": "1.0.0",
}
