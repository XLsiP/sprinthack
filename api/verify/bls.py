"""MOCK: American Heart Association lookup. Replace with a real integration."""
from verify.mock import MockVerifier


class BlsVerifier(MockVerifier):
    source = "American Heart Association"
