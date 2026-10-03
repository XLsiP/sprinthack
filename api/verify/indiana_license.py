"""MOCK: Indiana PLA lookup. Replace with a real integration."""
from verify.mock import MockVerifier


class IndianaLicenseVerifier(MockVerifier):
    source = "Indiana PLA"
