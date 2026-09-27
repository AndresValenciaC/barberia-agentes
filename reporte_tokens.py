from db import get_connection
import pathlib
from datetime import date

BASE_DIR = pathlib.Path(__file__).resolve().parent
MARCADOR_AUTH = BASE_DIR / "ultima_autorizacion.txt"
SALDO_INICIAL_USD = 20.00  # ajusta este número si vuelves a cargar créditos

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0), COALESCE(SUM(costo_usd),0)
        FROM interacciones_agente WHERE costo_usd IS NOT NULL
    """)
    total_llamadas, total_input, total_output, total_costo = cur.fetchone()
    total_costo = float(total_costo)

    print("=" * 50)
    print("RESUMEN DE USO DE TOKENS")
    print("=" * 50)
    print(f"Llamadas registradas con costo: {total_llamadas}")
    print(f"Tokens de entrada (input):      {total_input:,}")
    print(f"Tokens de salida (output):      {total_output:,}")
    print(f"Costo total estimado:           ${total_costo:.4f} USD")
    print()

    cur.execute("""
        SELECT creado_en::date AS dia, COUNT(*), COALESCE(SUM(costo_usd),0)
        FROM interacciones_agente WHERE costo_usd IS NOT NULL
        GROUP BY dia ORDER BY dia
    """)
    filas = cur.fetchall()

    print("GASTO POR DÍA")
    print("-" * 50)
    CIAN = "\033[96m"
    RESET = "\033[0m"
    if not filas:
        print("(sin datos con costo registrado todavía)")
    else:
        costo_max = max(float(f[2]) for f in filas) or 1
        for dia, llamadas, costo in filas:
            costo = float(costo)
            barra_largo = int((costo / costo_max) * 30) if costo_max > 0 else 0
            barra = f"{CIAN}{'█' * barra_largo}{RESET}"
            print(f"{dia}  {llamadas:>3} llamadas  ${costo:.4f}  {barra}")

    # ---------- Gasto por componente (orquestador vs. agenda vs. faq) ----------
    cur.execute("""
        SELECT canal, COUNT(*), COALESCE(SUM(costo_usd),0)
        FROM interacciones_agente WHERE costo_usd IS NOT NULL
        GROUP BY canal ORDER BY SUM(costo_usd) DESC
    """)
    print("\nGASTO POR COMPONENTE")
    print("-" * 50)
    for canal, llamadas, costo in cur.fetchall():
        print(f"{canal:<15} {llamadas:>3} llamadas   ${float(costo):.4f}")

conn.close()

# ---------- Saldo y renovación ----------
print("\n" + "=" * 50)
print("SALDO Y RENOVACIÓN")
print("=" * 50)
print(f"Saldo inicial cargado: ${SALDO_INICIAL_USD:.2f} USD")
print(f"Gastado (según registrado en este sistema): ${total_costo:.5f} USD")
print(f"Saldo estimado restante: ${SALDO_INICIAL_USD - total_costo:.5f} USD")
print("  (nota: este estimado solo refleja lo que este script ha registrado;")
print("   el saldo real y autoritativo está en console.anthropic.com)")

if MARCADOR_AUTH.exists():
    fecha_auth = date.fromisoformat(MARCADOR_AUTH.read_text().strip())
    dias_transcurridos = (date.today() - fecha_auth).days
    dias_restantes = 7 - dias_transcurridos
    if dias_restantes > 0:
        print(f"\nToken de Google Calendar: renovado hace {dias_transcurridos} día(s).")
        print(f"Quedan aproximadamente {dias_restantes} día(s) antes de que expire (modo Testing).")
    else:
        print(f"\nToken de Google Calendar: probablemente YA EXPIRÓ (han pasado {dias_transcurridos} días).")
else:
    print("\nToken de Google Calendar: sin registro de última autorización todavía.")