"""Casos reales de conversación que le han fallado o casi le fallan al
clasificador. Corren contra la API real de Anthropic (sin mockear
client.messages.create) para verificar el comportamiento real del modelo
ante estos mensajes - la escritura a Postgres (log_interaccion) sí se
mockea, porque el propósito de estos tests es el modelo, no la base de
datos, y así no dependen de que el contenedor de Docker esté corriendo.

Marcados @pytest.mark.smoke: excluidos por default (ver pytest.ini),
correr aparte con: pytest -m smoke
"""
import pytest

import orquestador


@pytest.fixture(autouse=True)
def _sin_escritura_a_db(mocker):
    return mocker.patch.object(orquestador, "log_interaccion")


@pytest.mark.smoke
def test_servicio_valido_junto_a_servicio_inexistente_es_agenda():
    historial = [{"role": "user", "content": "necesito corte de cabello y arreglo de uñas"}]
    assert orquestador.clasificar_intencion(historial) == "agenda"


@pytest.mark.smoke
def test_confirmacion_corta_despues_de_proponer_cita_es_agenda():
    historial = [
        {"role": "user", "content": "quiero un corte para mañana a las 3pm"},
        {"role": "assistant", "content": "Tengo disponible mañana a las 3pm para corte de cabello, ¿confirmamos?"},
        {"role": "user", "content": "listo"},
    ]
    assert orquestador.clasificar_intencion(historial) == "agenda"


@pytest.mark.smoke
def test_confirmacion_explicita_de_cita_es_agenda():
    historial = [
        {"role": "user", "content": "quiero agendar un tinte el sábado a las 10am"},
        {"role": "assistant", "content": "Perfecto, tinte el sábado a las 10am está disponible. ¿Confirmo la cita?"},
        {"role": "user", "content": "sí confirmar cita"},
    ]
    assert orquestador.clasificar_intencion(historial) == "agenda"
