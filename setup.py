import setuptools

from chord_service_registry import __version__

with open("README.md", "r") as rf:
    long_description = rf.read()

setuptools.setup(
    name="chord_service_registry",
    version=__version__,
    author="David Lougheed",
    author_email="david.lougheed@mail.mcgill.ca",
    description="An implementation of GA4GH Service Registry API for the CHORD project.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="TODO",
    packages=["chord_service_registry"],
    install_requires=["Flask"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ]
)
