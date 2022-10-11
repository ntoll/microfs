#!/usr/bin/env python3
from setuptools import setup


#: MAJOR, MINOR, RELEASE, STATUS [alpha, beta, final], VERSION
_VERSION = (1, 4, 5)


def get_version():
    """
    Returns a string representation of the version information of this project.
    """
    return ".".join([str(i) for i in _VERSION])


with open("README.rst") as f:
    readme = f.read()
with open("CHANGES.rst") as f:
    changes = f.read()


description = (
    "A module and utility to work with the simple filesystem on "
    "the BBC micro:bit"
)


setup(
    name="microfs",
    version=get_version(),
    description=description,
    long_description=readme + "\n\n" + changes,
    author="Nicholas H.Tollervey",
    author_email="ntoll@ntoll.org",
    url="https://github.com/ntoll/microfs",
    py_modules=[
        "microfs",
    ],
    license="MIT",
    install_requires=[
        "pyserial>=3.0.1,<4.0",
    ],
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Education",
        "Topic :: Software Development :: Embedded Systems",
    ],
    entry_points={
        "console_scripts": ["ufs=microfs:main"],
    },
)
