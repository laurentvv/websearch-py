"""The default test run is offline: see the `_offline_by_default` fixture in conftest.py."""

import socket

import pytest


def test_the_suite_cannot_open_a_socket():
    with pytest.raises(RuntimeError, match="offline test"):
        socket.create_connection(("192.0.2.1", 9), timeout=0.1)  # TEST-NET-1: never routed anyway
