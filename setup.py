#!/usr/bin/env python3
import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))


def _icon_data_files():
    icons_root = os.path.join(here, "icons")
    if not os.path.isdir(icons_root):
        return []
    files = []
    for root, _dirs, filenames in os.walk(icons_root):
        for name in filenames:
            full = os.path.join(root, name)
            files.append(os.path.relpath(full, here).replace(os.sep, "/"))
    return [("share/firespecs/icons", files)] if files else []


setup(
    name="firespecs",
    version="4.0",
    description="Hardware monitoring tool with GUI",
    author="Denis Oreshkin",
    author_email="dm@koteevich.ru",
    url="https://firespecs.sourceforge.io/",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    data_files=_icon_data_files(),
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
