import socket

_original_getaddrinfo = socket.getaddrinfo

def _getaddrinfo_ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = _getaddrinfo_ipv4_only

import os.path
import pathlib
from datetime import date, datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE_DIR = pathlib.Path(__file__).resolve().parent
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"
MARCADOR_AUTH = BASE_DIR / "ultima_autorizacion.txt"

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
            # Solo se llega aquí en una autorización NUEVA (no en un refresh silencioso)
            MARCADOR_AUTH.write_text(date.today().isoformat())
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def consultar_disponibilidad(fecha: str, hora: str, duracion_minutos: int = 30):
    """
    Verifica si un horario específico está libre en el calendario.
    fecha formato: YYYY-MM-DD, hora formato: HH:MM
    """
    service = get_calendar_service()
    inicio = f"{fecha}T{hora}:00-05:00"  # -05:00 = zona horaria Colombia

    dt_inicio = datetime.fromisoformat(inicio)
    dt_fin = dt_inicio + timedelta(minutes=duracion_minutos)

    eventos = service.events().list(
        calendarId="primary",
        timeMin=dt_inicio.isoformat(),
        timeMax=dt_fin.isoformat(),
        singleEvents=True,
    ).execute().get("items", [])

    return {"disponible": len(eventos) == 0, "conflictos": len(eventos)}


def crear_evento(fecha: str, hora: str, duracion_minutos: int, titulo: str, descripcion: str = ""):
    """
    Crea un evento real en Google Calendar. Devuelve el ID del evento creado.
    """
    service = get_calendar_service()
    inicio = f"{fecha}T{hora}:00-05:00"

    dt_inicio = datetime.fromisoformat(inicio)
    dt_fin = dt_inicio + timedelta(minutes=duracion_minutos)

    evento = {
        "summary": titulo,
        "description": descripcion,
        "start": {"dateTime": dt_inicio.isoformat(), "timeZone": "America/Bogota"},
        "end": {"dateTime": dt_fin.isoformat(), "timeZone": "America/Bogota"},
    }

    resultado = service.events().insert(calendarId="primary", body=evento).execute()
    return resultado["id"]