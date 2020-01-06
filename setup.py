#!/usr/bin/env python

import setuptools

with open("README.md", "r") as rf:
    long_description = rf.read()

setuptools.setup(
    name="chord_service_registry",
    version="0.1.0",

    python_requires=">=3.6",
    install_requires=["chord_lib @ git+https://github.com/c3g/chord_lib", "Flask", "requests", "requests-unixsocket"],

    author="David Lougheed",
    author_email="david.lougheed@mail.mcgill.ca",

    description="An implementation of GA4GH Service Registry API for the CHORD project.",
    long_description=long_description,
    long_description_content_type="text/markdown",

    packages=["chord_service_registry"],
    include_package_data=True,

    url="https://github.com/c3g/chord_service_registry",
    license="LGPLv3",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ]
)
