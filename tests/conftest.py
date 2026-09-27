from types import SimpleNamespace

import pytest


def _make_response(text: str, input_tokens: int = 10, output_tokens: int = 5):
    """Builds a stand-in for the Anthropic SDK's Message response, exposing
    only the attributes clasificar_intencion/conversar/responder_faq read:
    .content[0].text and .usage.input_tokens/output_tokens."""
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


@pytest.fixture
def make_anthropic_response():
    return _make_response
