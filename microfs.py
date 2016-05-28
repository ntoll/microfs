# -*- coding: utf-8 -*-
"""
This module contains functions for turning a Python script into a .hex file
and flashing it onto a BBC micro:bit.
"""


#: MAJOR, MINOR, RELEASE, STATUS [alpha, beta, final], VERSION
_VERSION = (0, 0, 1, 'alpha', 0)


def get_version():
    """
    Returns a string representation of the version information of this project.
    """
    return '.'.join([str(i) for i in _VERSION])
