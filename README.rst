MicroFS
-------

A simple command line tool and module for interacting with the limited
file system provided by MicroPython on the BBC micro:bit.

Installation
++++++++++++

To install simply type::

    $ pip install microfs

...and the package will download from PyPI. If you wish to upgrade to the
latest version, use the following command::

    $ pip install --no-cache --upgrade microfs

Usage
+++++

In your code::

    from microfs import ls, rm, put, get

From the command line use the "ufs" ("u" = micro) command.

To read the built-in help::

    $ ufs --help

List the files on the device::

    $ ufs ls

Delete a file on the device::

    $ ufs rm foo.txt

Copy a file onto the device::

    $ ufs put path/to/file.txt

Get a file from the device::

    $ ufs get foo.txt

Development
+++++++++++

The source code is hosted in GitHub. Please feel free to fork the repository.
Assuming you have Git installed you can download the code from the canonical
repository with the following command::

    $ git clone https://github.com/ntoll/microfs.git

Ensure you have the correct dependencies for development installed by creating
a virtualenv and running::

    $ pip install -r requirements.txt

To locally install your development version of the module into a virtualenv,
run the following command::

    $ python setup.py develop

There is a Makefile that helps with most of the common workflows associated
with development. Typing "make" on its own will list the options thus::

    $make

    There is no default Makefile target right now. Try:

    make clean - reset the project and remove auto-generated assets.
    make pyflakes - run the PyFlakes code checker.
    make pep8 - run the PEP8 style checker.
    make test - run the test suite.
    make coverage - view a report on test coverage.
    make check - run all the checkers and tests.
    make package - create a deployable package for the project.
    make publish - publish the project to PyPI.
    make docs - run sphinx to create project documentation.

