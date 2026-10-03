"""MOCK: ARRT lookup. Replace with a real integration."""
from verify.mock import MockVerifier


class ArrtVerifier(MockVerifier):
    source = "ARRT"
