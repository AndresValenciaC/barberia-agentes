---
name: pyme-agenda-skeleton
description: Usa esta skill cuando se necesite construir o adaptar un sistema de agenda de citas con IA para una pyme (barbería, centro médico, spa, consultorio, etc.). Provee la arquitectura estándar probada - orquestador + subagentes + esquema de base de datos + reglas anti-alucinación - para no reconstruir el patrón desde cero en cada cliente nuevo.
---

# Esqueleto de sistema de agenda para pymes

## Arquitectura estándar

1. **Orquestador** — clasifica la intención del cliente (agenda / faq / otro) usando el
   HISTORIAL COMPLETO de la conversación, nunca solo el último mensaje. Mensajes cortos
   como "listo" o "sí" solo tienen sentido con contexto previo.

2. **Subagente de agenda** — usa herramientas reales (Calendar, base de datos) vía MCP.
   REGLA CRÍTICA: nunca debe confirmar una cita sin haber consultado disponibilidad real
   primero. Nunca debe calcular fechas relativas ("mañana", "el lunes") sin que el system
   prompt le dé la fecha actual como dato explícito - el modelo no sabe qué día es hoy.

3. **Subagente de FAQ** — sin herramientas, solo contexto estático del negocio. Si le
   preguntan algo fuera de ese contexto (precios no definidos, políticas no especificadas),
   debe admitir que no tiene el dato - nunca inventarlo.

## Esquema de base de datos mínimo (Postgres)

- `clientes` (id, nombre, celular, correo, canal_preferido)
- `servicios` (id, nombre, duracion_minutos, activo)
- `citas` (id, cliente_id, servicio_id, fecha_hora, estado, google_event_id, canal_origen)
- `interacciones_agente` (id, canal, mensaje_entrada, respuesta_json, estado,
   input_tokens, output_tokens, costo_usd) - log completo para evaluación y costos

## Lecciones de debugging que se repiten en cada implementación

- Rutas relativas (`credentials.json`, `.env`) rompen si el agente se lanza desde otro
  proceso (ej. Claude Desktop vs. terminal). Usar siempre `pathlib.Path(__file__).resolve().parent`.
- `max_tokens` bajo (10-20) para clasificadores de una palabra; alto (300-1024) para
  respuestas conversacionales. NUNCA usar max_tokens para arreglar un problema de
  interpretación - eso se arregla con mejor prompt y ejemplos concretos (few-shot).
- Cada subagente que recibe mensajes del cliente necesita el historial completo, no
  solo el mensaje actual, o pierde contexto en confirmaciones cortas.

## Checklist al adaptar esto a un nuevo negocio

- [ ] Definir servicios reales (nunca inventar precios/horarios no confirmados por el cliente)
- [ ] Definir reglas de negocio específicas (¿cancelaciones? ¿depósitos? ¿reglas de horario?)
- [ ] Ajustar nivel de complejidad: negocio simple = 2 subagentes; negocio complejo
  (ej. centro médico) = más subagentes, reglas más estrictas, posible aprobación humana
  antes de confirmar ciertas acciones