# State Provider Registry
# Maps state codes to provider implementations

from typing import Dict
from providers.base import LotteryProvider

_REGISTRY: Dict[str, LotteryProvider] = {}

def register_provider(state_code: str, provider: LotteryProvider):
    """Register a provider for a state"""
    _REGISTRY[state_code.upper()] = provider

def get_provider(state_code: str) -> LotteryProvider:
    """Get provider for a state"""
    provider = _REGISTRY.get(state_code.upper())
    if not provider:
        raise ValueError(f"No provider registered for state: {state_code}")
    return provider

def list_providers() -> list:
    """List all registered state codes"""
    return list(_REGISTRY.keys())
