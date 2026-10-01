"""Fixed test entrypoint, with a Python network tripwire.

Docker network_mode:none is the runtime isolation boundary. This tripwire is
defence in depth, not a sandbox against native libraries or hostile code.
"""
import os
from pathlib import Path
import socket
import sys
import unittest


def deny_network(*args, **kwargs):
    raise RuntimeError('Network disabled in ACT isolated tests')


def install_network_guard():
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    socket.socket.sendto = deny_network
    socket.create_connection = deny_network
    socket.getaddrinfo = deny_network


def main():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'isolation.settings'
    install_network_guard()
    root = Path(__file__).resolve().parents[1]
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().discover(str(root / 'tests'), pattern='test_onboarding_logging.py'))
    suite.addTests(unittest.TestLoader().discover(str(root / 'isolation'), pattern='test_smoke.py'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
