# -*- coding: utf-8 -*-
"""
Tests for the microfs module.
"""
import microfs


def test_get_version():
    """
    Ensure call to the get_version function returns the expected string.
    """
    result = microfs.get_version()
    assert result == '.'.join([str(i) for i in microfs._VERSION])
