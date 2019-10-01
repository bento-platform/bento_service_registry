# CHORD Service Registry

**Author:** David Lougheed, Canadian Centre for Computational Genomics

Prototype implementation of GA4GH's [service registry API](https://github.com/ga4gh-discovery/ga4gh-service-registry/)
for the CHORD project.


## Details and Brainstorming

  * Implements GA4GH Service Registry Spec
  * Loads services from `chord_services.json` into a SQLite DB
  * If chordServiceID not in DB, generate a new GUID for service in this CHORD
    context, delete ones that are no longer present
  * Additional metadata:
      * chordServiceID: unique human-readable ID for service (ex. rnaget)
      * chordServiceType: other or data

TODO: SHOULD WE PULL DIRECTLY FROM REPOSITORIES OR IS THAT TOO MUCH OF A VULNERABILITY? MAYBE PIP...

All services must have a requirements.txt and implement /service-info.

How do updates work?

  * `pip install -U` for each service
  * call some regeneration script which re-checks `apt` dependencies + runs steps 3-n above
