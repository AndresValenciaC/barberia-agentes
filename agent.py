import os
import json
from datetime import date
from anthropic import Anthropic
from dotenv import load_dotenv

from calendar_service import consultar_disponibilidad, crear_evento
from db import log_interaccion, get_connection

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def construir_system_prompt():
    hoy = date.today().isoformat()  # ej. "2026-09-16"
    return f"""Eres el asistente de agenda de Barbería Andres.

CONTEXTO:
La fecha de HOY es {hoy} (dato real del sistema, no lo cuestiones).
Servicios disponibles: corte de cabello, arreglo de barba, tinte, cejas.
Horario de atención: Lunes a Sábado, 9:00am a 6:00pm.

TAREA:
Dado un mensaje de un cliente, extrae: servicio(s) solicitado(s), fecha/hora
preferida, nombre del cliente. Si falta algún dato, pregunta solo por lo que falta.
Cuando el cliente diga "hoy", "mañana", "el viernes", etc., calcula la fecha
exacta (YYYY-MM-DD) usando la fecha de HOY que se te dio arriba - nunca la inventes.

REGLAS:
- Si el servicio solicitado no existe en la lista, dilo explícitamente.
- Antes de confirmar una cita, SIEMPRE usa la herramienta consultar_disponibilidad.
- Si el horario no está disponible, sugiere alternativas cercanas dentro del horario de atención.
- Solo usa crear_cita después de confirmar disponibilidad Y de tener todos los datos completos.
- Nunca inventes disponibilidad ni confirmes una cita sin haber usado las herramientas."""

TOOLS = [
    {
        "name": "consultar_disponibilidad",
        "description": "Verifica si un horario específico está libre en el calendario de la barbería.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fecha": {"type": "string", "description": "Formato YYYY-MM-DD"},
                "hora": {"type": "string", "description": "Formato HH:MM, 24 horas"},
                "duracion_minutos": {"type": "integer", "description": "Duración estimada del servicio"},
            },
            "required": ["fecha", "hora", "duracion_minutos"],
        },
    },
    {
        "name": "crear_cita",
        "description": "Crea una cita real: agrega el evento a Google Calendar y lo registra en la base de datos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fecha": {"type": "string", "description": "Formato YYYY-MM-DD"},
                "hora": {"type": "string", "description": "Formato HH:MM, 24 horas"},
                "duracion_minutos": {"type": "integer"},
                "servicio": {"type": "string"},
                "nombre_cliente": {"type": "string"},
            },
            "required": ["fecha", "hora", "duracion_minutos", "servicio", "nombre_cliente"],
        },
    },
]


def ejecutar_herramienta(nombre: str, input_data: dict) -> dict:
    """Aquí es donde TU código, no el modelo, ejecuta la acción real."""
    if nombre == "consultar_disponibilidad":
        return consultar_disponibilidad(
            input_data["fecha"], input_data["hora"], input_data["duracion_minutos"]
        )

    if nombre == "crear_cita":
        google_event_id = crear_evento(
            fecha=input_data["fecha"],
            hora=input_data["hora"],
            duracion_minutos=input_data["duracion_minutos"],
            titulo=f"{input_data['servicio']} - {input_data['nombre_cliente']}",
            descripcion="Cita creada por el asistente de agenda.",
        )

        conn = get_connection()
        with conn.cursor() as cur:
            # Busca o crea el cliente
            cur.execute("SELECT id FROM clientes WHERE nombre = %s", (input_data["nombre_cliente"],))
            cliente = cur.fetchone()
            if cliente:
                cliente_id = cliente[0]
            else:
                cur.execute(
                    "INSERT INTO clientes (nombre) VALUES (%s) RETURNING id",
                    (input_data["nombre_cliente"],),
                )
                cliente_id = cur.fetchone()[0]

            # Busca o crea el servicio
            cur.execute("SELECT id FROM servicios WHERE nombre = %s", (input_data["servicio"],))
            servicio = cur.fetchone()
            if servicio:
                servicio_id = servicio[0]
            else:
                cur.execute(
                    "INSERT INTO servicios (nombre, duracion_minutos) VALUES (%s, %s) RETURNING id",
                    (input_data["servicio"], input_data["duracion_minutos"]),
                )
                servicio_id = cur.fetchone()[0]

            # Ahora sí, la cita con las referencias reales
            cur.execute(
                """INSERT INTO citas (cliente_id, servicio_id, fecha_hora, estado, google_event_id, canal_origen)
                   VALUES (%s, %s, %s, 'confirmada', %s, 'agent')""",
                (cliente_id, servicio_id,
                 f"{input_data['fecha']} {input_data['hora']}:00", google_event_id),
            )
            conn.commit()
        conn.close()
        return {"cita_creada": True, "google_event_id": google_event_id}

    return {"error": f"herramienta desconocida: {nombre}"}



def conversar(mensajes: list, mensaje_usuario_actual: str, canal: str = "test"):
    """mensajes = historial completo. mensaje_usuario_actual = el texto plano
    de este turno específico, para loguearlo sin ambigüedad."""
    while True:
        respuesta = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=construir_system_prompt(),
            tools=TOOLS,
            messages=mensajes,
        )

        if respuesta.stop_reason != "tool_use":
            texto_final = next(
                (b.text for b in respuesta.content if b.type == "text"), ""
            )
            mensajes.append({"role": "assistant", "content": respuesta.content})
            log_interaccion(
                canal, mensaje_usuario_actual,
                {"respuesta": texto_final}, "respondido",
                input_tokens=respuesta.usage.input_tokens,
                output_tokens=respuesta.usage.output_tokens,
            )
            return texto_final, mensajes

        mensajes.append({"role": "assistant", "content": respuesta.content})
        resultados_tools = []

        for bloque in respuesta.content:
            if bloque.type == "tool_use":
                print(f"  [Agente está usando la herramienta: {bloque.name}]")
                resultado = ejecutar_herramienta(bloque.name, bloque.input)
                resultados_tools.append({
                    "type": "tool_result",
                    "tool_use_id": bloque.id,
                    "content": json.dumps(resultado),
                })

        mensajes.append({"role": "user", "content": resultados_tools})


if __name__ == "__main__":
    print("Asistente de Barbería (escribe 'salir' para terminar)\n")
    historial = []

    while True:
        entrada = input("Cliente: ")
        if entrada.lower() == "salir":
            break
        historial.append({"role": "user", "content": entrada})
        respuesta_texto, historial = conversar(historial, entrada)
        print(f"Asistente: {respuesta_texto}\n")