# coding: utf-8

from os import path

from setuptools import find_packages, setup

setup(
    name="scout-rerunner",
    version="1.0",
    description="Scout rerunner",
    license="MIT",
    author="Markus Johansson",
    author_email="markus.h.johansson@skane.se",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords=["OpenAPI", "Connexion"],
    packages=find_packages(exclude=["auth"]),
    package_data={"": ["openapi/openapi.yaml"]},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "flask>=1.1.2",
        "connexion>=2.7.0",
        "swagger-ui-bundle>=0.0.8",
        "ped-parser==1.6.6",
        "pymongo==3.11.0",
        "fabric==2.5.0",
        "pyyaml",
        "attr",
        "cattrs",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "mongomock"],
)
