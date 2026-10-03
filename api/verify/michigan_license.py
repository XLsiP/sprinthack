"""MOCK: Michigan LARA lookup. Replace with a real integration."""
from verify.mock import MockVerifier


class MichiganLicenseVerifier(MockVerifier):
    source = "Michigan LARA"
