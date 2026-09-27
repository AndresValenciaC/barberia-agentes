import os
import psycopg
from dotenv import load_dotenv
import pathlib
from dotenv import load_dotenv

BASE_DIR = pathlib.Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
# Precios de Claude Sonnet 5 por millón de tokens (verificar en console.anthropic.com si cambian)
PRECIO_INPUT_POR_MILLON = 2.00
PRECIO_OUTPUT_POR_MILLON = 10.00


def calcular_costo(input_tokens: int, output_tokens: int) -> float:
    costo_input = (input_tokens / 1_000_000) * PRECIO_INPUT_POR_MILLON
    costo_output = (output_tokens / 1_000_000) * PRECIO_OUTPUT_POR_MILLON
    return round(costo_input + costo_output, 6)


def log_interaccion(canal: str, mensaje_entrada: str, respuesta_json: dict, estado: str,
                     cliente_id=None, input_tokens: int = None, output_tokens: int = None):
    costo = None
    if input_tokens is not None and output_tokens is not None:
        costo = calcular_costo(input_tokens, output_tokens)

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO interacciones_agente
                (cliente_id, canal, mensaje_entrada, respuesta_json, estado, input_tokens, output_tokens, costo_usd)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (cliente_id, canal, mensaje_entrada, psycopg.types.json.Json(respuesta_json),
             estado, input_tokens, output_tokens, costo),
        )


        conn.commit()
    conn.close()