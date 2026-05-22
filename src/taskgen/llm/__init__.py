from .base import LLMProvider
from .kimi import KimiProvider
from .fake import FakeProvider


def create_provider(mode: str = "kimi", **kwargs) -> LLMProvider:
    if mode == "fake" or mode == "mock":
        return FakeProvider()
    return KimiProvider(**kwargs)
