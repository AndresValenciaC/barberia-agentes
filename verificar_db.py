# verificar_db.py
from db import get_connection

conn = get_connection()

def seccion(titulo):
    print(f"\n{'=' * 50}\n{titulo}\n{'=' * 50}")


with conn.cursor() as cur:
    # ---------- Estructura de la base de datos ----------
    seccion("ESTRUCTURA DE LA BASE DE DATOS")
    cur.execute("""
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)
    filas = cur.fetchall()

    tabla_actual = None
    for nombre_tabla, columna, tipo, nullable in filas:
        if nombre_tabla != tabla_actual:
            print(f"\n  📋 {nombre_tabla}")
            tabla_actual = nombre_tabla
        obligatorio = "" if nullable == "YES" else " (obligatorio)"
        print(f"      - {columna}: {tipo}{obligatorio}")

    # ---------- Citas, con nombre de cliente y servicio ----------
    seccion("CITAS")
    cur.execute("""
        SELECT c.id, c.fecha_hora, cl.nombre, s.nombre AS servicio, c.estado, c.canal_origen
        FROM citas c
        LEFT JOIN clientes cl ON c.cliente_id = cl.id
        LEFT JOIN servicios s ON c.servicio_id = s.id
        ORDER BY c.fecha_hora
    """)
    citas = cur.fetchall()
    for fila in citas:
        id_, fecha, cliente, servicio, estado, canal = fila
        cliente = cliente or "(sin nombre - cita antigua)"
        servicio = servicio or "(sin servicio - cita antigua)"
        print(f"  #{id_} | {fecha} | {cliente} | {servicio} | {estado} | canal:{canal}")
    print(f"\n  Total citas: {len(citas)}")

    # ---------- Clientes registrados ----------
    seccion("CLIENTES")
    cur.execute("SELECT id, nombre, celular, correo FROM clientes ORDER BY id")
    clientes = cur.fetchall()
    for fila in clientes:
        print(f"  #{fila[0]} | {fila[1]} | cel: {fila[2] or '-'} | correo: {fila[3] or '-'}")
    print(f"\n  Total clientes: {len(clientes)}")

    # ---------- Servicios registrados ----------
    seccion("SERVICIOS")
    cur.execute("SELECT id, nombre, duracion_minutos FROM servicios ORDER BY id")
    for fila in cur.fetchall():
        print(f"  #{fila[0]} | {fila[1]} | {fila[2]} min")

    # ---------- Últimas interacciones ----------
    seccion("ÚLTIMAS 5 INTERACCIONES")
    cur.execute("""
        SELECT canal, estado, input_tokens, output_tokens, costo_usd, creado_en
        FROM interacciones_agente
        ORDER BY creado_en DESC LIMIT 5
    """)
    for fila in cur.fetchall():
        canal, estado, in_tok, out_tok, costo, cuando = fila
        costo_txt = f"${costo:.5f}" if costo is not None else "(sin costo registrado)"
        print(f"  [{cuando.strftime('%Y-%m-%d %H:%M')}] {canal} | {estado} | {costo_txt}")

    # ---------- Resumen ----------
    cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(costo_usd), 0)
        FROM interacciones_agente WHERE costo_usd IS NOT NULL
    """)
    total_llamadas, total_costo = cur.fetchone()
    seccion("RESUMEN")
    print(f"  Llamadas con costo registrado: {total_llamadas}")
    print(f"  Costo total acumulado: ${total_costo:.5f} USD")

conn.close()