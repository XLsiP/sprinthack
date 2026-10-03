"""MOCK: NMTCB lookup. Replace with a real integration."""
from verify.mock import MockVerifier


class NmtcbVerifier(MockVerifier):
    source = "NMTCB"
