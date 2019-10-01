#!/usr/bin/env python3

from pkg_resources import get_distribution

name = "chord_service_registry"
__version__ = get_distribution(name).version
