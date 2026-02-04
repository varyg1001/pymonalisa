#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pymonalisa",
    version="0.1.2",
    description="pymonalisa - A Python library to decrypt IQIYI DRM License Ticket",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ReiDoBrega",
    author_email="",
    url="https://github.com/ReiDoBrega/pymonalisa",
    license="CC BY-NC-ND 4.0",
    packages=find_packages(),
    python_requires=">=3.9,<4.0",
    install_requires=[
        "click>=8.1.7",
        "cloup>=3.0.7",
        "loggpy>=0.1.0",
        "wasmtime>=36.0.0",
    ],
    entry_points={
        "console_scripts": [
            "pymonalisa=pymonalisa.main:main",
        ],
    },
    keywords=[
        "python",
        "drm",
        "monalisa",
        "iqcom",
        "iqiyi",
        "wasm",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Video",
        "Topic :: Security :: Cryptography",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    include_package_data=True,
)
