from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from db import get_connection

wb = Workbook()

# Estilos reutilizables
HEADER_FILL = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)


def escribir_encabezados(ws, encabezados):
    for col, texto in enumerate(encabezados, start=1):
        celda = ws.cell(row=1, column=col, value=texto)
        celda.fill = HEADER_FILL
        celda.font = HEADER_FONT
        celda.alignment = Alignment(horizontal="center")


def autoajustar_columnas(ws):
    for col in ws.columns:
        max_largo = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max_largo + 4


# ---------- Hoja 1: Citas ----------
ws_citas = wb.active
ws_citas.title = "Citas"
escribir_encabezados(ws_citas, ["ID", "Fecha", "Hora", "Estado", "Canal", "Google Event ID"])

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("""
    SELECT c.id, c.fecha_hora::date AS fecha, c.fecha_hora::time AS hora,
           cl.nombre AS cliente, s.nombre AS servicio, c.estado, c.canal_origen
    FROM citas c
    LEFT JOIN clientes cl ON c.cliente_id = cl.id
    LEFT JOIN servicios s ON c.servicio_id = s.id
    ORDER BY c.fecha_hora
""")
    for fila_num, fila in enumerate(cur.fetchall(), start=2):
        for col_num, valor in enumerate(fila, start=1):
            ws_citas.cell(row=fila_num, column=col_num, value=str(valor) if valor else "")

autoajustar_columnas(ws_citas)

# ---------- Hoja 2: Resumen de costos ----------
ws_costos = wb.create_sheet("Costos de IA")
escribir_encabezados(ws_costos, ["Día", "Llamadas", "Tokens entrada", "Tokens salida", "Costo USD"])

with conn.cursor() as cur:
    cur.execute("""
        SELECT creado_en::date, COUNT(*),
               COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0),
               COALESCE(SUM(costo_usd),0)
        FROM interacciones_agente
        WHERE costo_usd IS NOT NULL
        GROUP BY creado_en::date ORDER BY creado_en::date
    """)
    filas = cur.fetchall()
    for fila_num, fila in enumerate(filas, start=2):
        for col_num, valor in enumerate(fila, start=1):
            ws_costos.cell(row=fila_num, column=col_num, value=str(valor))

    # Fila de totales
    fila_total = len(filas) + 2
    ws_costos.cell(row=fila_total, column=1, value="TOTAL").font = Font(bold=True)
    for col in (3, 4, 5):
        letra = get_column_letter(col)
        ws_costos.cell(row=fila_total, column=col,
                        value=f"=SUM({letra}2:{letra}{fila_total-1})").font = Font(bold=True)

autoajustar_columnas(ws_costos)
conn.close()

# ---------- Guardar ----------
nombre_archivo = f"reporte_barberia_{datetime.now().strftime('%Y%m%d')}.xlsx"
wb.save(nombre_archivo)
print(f"Reporte generado: {nombre_archivo}")