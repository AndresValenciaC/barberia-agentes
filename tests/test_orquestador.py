import pytest

import orquestador


@pytest.fixture(autouse=True)
def _sin_escritura_a_db(mocker):
    """clasificar_intencion siempre loguea vía db.log_interaccion; lo mockeamos
    en todos los tests de este archivo para no depender de Postgres."""
    return mocker.patch.object(orquestador, "log_interaccion")


def _historial(mensaje: str):
    return [{"role": "user", "content": mensaje}]


def test_respuesta_limpia_agenda(mocker, make_anthropic_response):
    mocker.patch.object(
        orquestador.client.messages, "create",
        return_value=make_anthropic_response("agenda"),
    )
    resultado = orquestador.clasificar_intencion(_historial("quiero un corte mañana"))
    assert resultado == "agenda"


def test_respuesta_con_texto_extra_que_contiene_la_palabra_clave(mocker, make_anthropic_response):
    mocker.patch.object(
        orquestador.client.messages, "create",
        return_value=make_anthropic_response("agendando la cita del cliente"),
    )
    resultado = orquestador.clasificar_intencion(_historial("agéndame para mañana"))
    assert resultado == "agenda"


def test_respuesta_sin_ninguna_palabra_clave_cae_en_otro(mocker, make_anthropic_response):
    mocker.patch.object(
        orquestador.client.messages, "create",
        return_value=make_anthropic_response("no tengo idea de qué responder"),
    )
    resultado = orquestador.clasificar_intencion(_historial("¿qué tal el clima hoy?"))
    assert resultado == "otro"


def test_no_llama_a_la_api_real(mocker, make_anthropic_response):
    mock_create = mocker.patch.object(
        orquestador.client.messages, "create",
        return_value=make_anthropic_response("faq"),
    )
    orquestador.clasificar_intencion(_historial("¿cuánto cuesta el corte?"))
    mock_create.assert_called_once()
