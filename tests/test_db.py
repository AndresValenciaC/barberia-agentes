import pytest

from db import calcular_costo, PRECIO_INPUT_POR_MILLON, PRECIO_OUTPUT_POR_MILLON


@pytest.mark.parametrize(
    "input_tokens, output_tokens, esperado",
    [
        (0, 0, 0.0),
        (1_000_000, 0, PRECIO_INPUT_POR_MILLON),
        (0, 1_000_000, PRECIO_OUTPUT_POR_MILLON),
        (1_000_000, 1_000_000, PRECIO_INPUT_POR_MILLON + PRECIO_OUTPUT_POR_MILLON),
        (500_000, 250_000, 1.0 + 2.5),
        (123, 456, round((123 / 1_000_000) * PRECIO_INPUT_POR_MILLON
                          + (456 / 1_000_000) * PRECIO_OUTPUT_POR_MILLON, 6)),
    ],
)
def test_calcular_costo(input_tokens, output_tokens, esperado):
    assert calcular_costo(input_tokens, output_tokens) == esperado


def test_calcular_costo_redondea_a_seis_decimales():
    costo = calcular_costo(1, 1)
    assert costo == round(costo, 6)
