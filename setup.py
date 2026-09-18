#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Instalador de Antivinux (setuptools)."""

import os
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.dirname(__file__))

about = {}
with open(os.path.join(HERE, "antivinux", "__init__.py"), "r", encoding="utf-8") as fh:
    exec(fh.read(), about)

with open(os.path.join(HERE, "README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()

data_files = [
    ("share/applications", ["data/org.antivinux.app.desktop"]),
    ("share/metainfo", ["data/org.antivinux.app.appdata.xml"]),
    ("share/icons/hicolor/scalable/apps", ["data/antivinux.svg"]),
    ("share/pixmaps", ["data/antivinux.svg"]),
    ("share/polkit-1/actions", ["data/org.antivinux.policy"]),
    (
        "share/antivinux",
        [
            "data/antivinux-update-db.sh",
            "data/antivinux-self-update.sh",
        ],
    ),
]

setup(
    name=about["__app_name__"].lower(),
    version=about["__version__"],
    description=about["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=about["__author__"],
    author_email=about.get("__author_email__"),
    url=about["__homepage__"],
    license=about["__license__"],
    packages=find_packages(exclude=["tests", "debian"]),
    include_package_data=True,
    python_requires=">=3.6",
    data_files=data_files,
    entry_points={
        "console_scripts": [
            "antivinux=antivinux.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: Security",
    ],
)