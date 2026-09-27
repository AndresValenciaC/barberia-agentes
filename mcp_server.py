from mcp.server.mcpserver import MCPServer
from calendar_service import consultar_disponibilidad as _consultar, crear_evento
from db import get_connection

mcp = MCPServer("Barberia Andres")


@mcp.tool()
def consultar_disponibilidad(fecha: str, hora: str, duracion_minutos: int = 30) -> dict:
    """
    Verifica si un horario específico está libre en el calendario de la barbería.
    fecha formato: YYYY-MM-DD, hora formato: HH:MM (24 horas)
    """
    return _consultar(fecha, hora, duracion_minutos)


@mcp.tool()
def crear_cita(fecha: str, hora: str, duracion_minutos: int, servicio: str, nombre_cliente: str) -> dict:
    """
    Crea una cita real: agrega el evento a Google Calendar y lo registra en la base de datos.
    """
    google_event_id = crear_evento(
        fecha=fecha,
        hora=hora,
        duracion_minutos=duracion_minutos,
        titulo=f"{servicio} - {nombre_cliente}",
        descripcion="Cita creada vía servidor MCP.",
    )
    conn = get_connection()
    with conn.cursor() as cur:
        # Busca o crea el cliente
        cur.execute("SELECT id FROM clientes WHERE nombre = %s", (nombre_cliente,))
        cliente = cur.fetchone()
        if cliente:
            cliente_id = cliente[0]
        else:
            cur.execute(
                "INSERT INTO clientes (nombre) VALUES (%s) RETURNING id",
                (nombre_cliente,),
            )
            cliente_id = cur.fetchone()[0]

        # Busca o crea el servicio
        cur.execute("SELECT id FROM servicios WHERE nombre = %s", (servicio,))
        servicio_row = cur.fetchone()
        if servicio_row:
            servicio_id = servicio_row[0]
        else:
            cur.execute(
                "INSERT INTO servicios (nombre, duracion_minutos) VALUES (%s, %s) RETURNING id",
                (servicio, duracion_minutos),
            )
            servicio_id = cur.fetchone()[0]

        cur.execute(
            """INSERT INTO citas (cliente_id, servicio_id, fecha_hora, estado, google_event_id, canal_origen)
               VALUES (%s, %s, %s, 'confirmada', %s, 'mcp')""",
            (cliente_id, servicio_id, f"{fecha} {hora}:00", google_event_id),
        )
        conn.commit()
    conn.close()
    return {"cita_creada": True, "google_event_id": google_event_id}


if __name__ == "__main__":
    mcp.run()