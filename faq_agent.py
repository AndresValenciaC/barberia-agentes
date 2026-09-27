import os
from anthropic import Anthropic
from dotenv import load_dotenv
import pathlib
from db import log_interaccion

BASE_DIR = pathlib.Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT_FAQ = """Eres el asistente de información general de Barbería Andres.

INFORMACIÓN REAL DEL NEGOCIO (única fuente válida, no inventes nada fuera de esto):
- Servicios: corte de cabello, arreglo de barba, tinte, cejas.
- Horario: Lunes a Sábado, 9:00am a 6:00pm. Domingo cerrado.

REGLAS:
- Si te preguntan algo que no está en la información de arriba, responde
  honestamente que no tienes ese dato disponible - NUNCA lo inventes.
- No necesitas decir que vas a "transferir" a nadie - el sistema que te
  contiene ya se encarga de eso automáticamente."""


def responder_faq(historial: list, mensaje_usuario_actual: str):
    respuesta = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        system=SYSTEM_PROMPT_FAQ,
        messages=historial,
    )
    texto_final = next((b.text for b in respuesta.content if b.type == "text"), "")
    historial.append({"role": "assistant", "content": respuesta.content})
    log_interaccion(
        "faq", mensaje_usuario_actual, {"respuesta": texto_final}, "respondido",
        input_tokens=respuesta.usage.input_tokens,
        output_tokens=respuesta.usage.output_tokens,
    )
    return texto_final, historial