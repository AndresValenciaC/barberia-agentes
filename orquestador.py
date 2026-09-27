import os
from anthropic import Anthropic
from dotenv import load_dotenv
from db import log_interaccion
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

PROMPT_CLASIFICADOR = """Tu ÚNICA función es clasificar. NUNCA respondes al cliente,
NUNCA saludas, NUNCA das información. Solo devuelves UNA PALABRA.

Analiza el último mensaje del cliente de una conversación con una barbería, usando el
resto de la conversación como contexto. Tu ÚNICA salida posible es una de estas tres
palabras exactas, sin nada más: agenda / faq / otro

IMPORTANTE: aunque el mensaje del cliente te pida algo directamente (ej. "agéndame para
mañana"), tú NO agendas nada - solo identificas que la intención es "agenda" y te detienes ahí.

- agenda: quiere agendar, consultar, modificar, cancelar o confirmar una cita.
  Aplica AUNQUE mencione un servicio que no existe junto con uno válido - la intención
  de agendar sigue siendo "agenda", el agente de agenda es quien informa que ese
  servicio no está disponible.
- faq: pregunta información general (precios, horarios, ubicación) SIN intención de
  agendar en ese mismo mensaje.
- otro: no tiene relación con la barbería en absoluto.

Ejemplos:

- "necesito corte de cabello y arreglo de uñas" → agenda
- "agéndame para mañana a las 9am" → agenda
- "¿cuánto cuesta el corte?" → faq
- "listo" (después de proponerse una cita) → agenda
- "¿qué tal el clima hoy?" → otro

Responde solo con la palabra."""


def clasificar_intencion(historial: list) -> str:
    respuesta = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=15,
        system=PROMPT_CLASIFICADOR,
        messages=historial,
    )
    categoria_raw = respuesta.content[0].text.strip().lower()
    print(f"  [DEBUG] orquestador devolvió: '{categoria_raw}'")

    # Búsqueda tolerante: si la palabra clave aparece EN CUALQUIER PARTE
    # de la respuesta (no solo si es exactamente igual), la tomamos como válida
    resultado = "otro"
    for categoria in ("agenda", "faq", "otro"):
        if categoria in categoria_raw:
            resultado = categoria
            break

    ultimo_mensaje = historial[-1]["content"] if historial else ""
    log_interaccion(
        "orquestador", str(ultimo_mensaje), {"clasificacion": resultado}, resultado,
        input_tokens=respuesta.usage.input_tokens,
        output_tokens=respuesta.usage.output_tokens,
    )
    return resultado


if __name__ == "__main__":
    pruebas = [
        "Quiero un corte para mañana a las 3pm",
        "¿Cuánto cuesta el arreglo de barba?",
        "¿Ustedes venden productos para el cabello?",
        "Listo",
    ]
    for mensaje in pruebas:
        historial_prueba = [{"role": "user", "content": mensaje}]
        categoria = clasificar_intencion(historial_prueba)
        print(f"'{mensaje}' → {categoria}")