#!/usr/bin/env python3
from setuptools import setup, find_packages
import os

# Read version from app
here = os.path.abspath(os.path.dirname(__file__))

setup(
    name="firespecs",
    version="3.0",
    description="Hardware monitoring tool with GUI",
    author="Denis Oreshkin",
    author_email="dm@koteevich.ru",
    url="https://firespecs.sourceforge.io/",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "": ["*.png", "*.ico", "*.desktop"],
    },
    install_requires=[
        "PyQt5",
        "psutil",
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "firespecs=app.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: System :: Hardware",
        "Topic :: System :: Monitoring",
    ],
)
