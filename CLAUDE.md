# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A conversational AI agent system for "Barbería Andres" (a barbershop) that handles appointment
scheduling via Google Calendar + Postgres, and answers FAQs. Built with the Anthropic Python SDK
(`claude-sonnet-4-5`), no framework. There's also an MCP server exposing the same calendar/booking
tools, and reporting scripts (Excel report, token/cost usage summary) driven off the interaction log.

This repo is not a git repository — there is no `git` history to consult here.

## Running things

- Start Postgres: `docker-compose up -d` (container `pyme_agentes_db`, db `pyme_agentes`, exposed on `5432`)
- Apply schema (first run only): load `schema.sql` into the running Postgres instance
- Run the main chat loop: `python main.py` (interactive stdin loop, type `salir` to quit)
- Run the agenda subagent standalone: `python agent.py`
- Run the orchestrator's built-in classifier smoke test: `python orquestador.py`
- Run the MCP server standalone: `python mcp_server.py`
- Inspect DB contents/schema from the terminal: `python verificar_db.py`
- Generate the Excel report (citas + costos de IA): `python reporte_excel.py`
- Print token usage / cost summary to the terminal: `python reporte_tokens.py`
- Test raw Google Calendar auth/listing: `python test_calendar.py`

There is no test suite, linter, or build step configured — there's also no `requirements.txt`;
dependencies (`anthropic`, `psycopg`, `python-dotenv`, `google-auth`, `google-auth-oauthlib`,
`google-api-python-client`, `openpyxl`, `mcp`) are installed directly into `venv/`.

Config comes from `.env` (loaded via `pathlib.Path(__file__).resolve().parent / ".env"` in every
entry point, never a bare relative path — see below): `ANTHROPIC_API_KEY`, `DB_HOST`, `DB_PORT`,
`DB_NAME`, `DB_USER`, `DB_PASSWORD`.

## Core principle

This project must never invent or assume data, figures, dates, or availability that haven't been
verified. Concretely: the agenda subagent must never confirm a booking without a real
`consultar_disponibilidad` call, must never guess a relative date ("tomorrow", "Friday") without
the actual current date given in its system prompt, and the FAQ subagent must never state a price,
hour, or policy not present in its static business-facts block — it should say the info isn't
available instead. Apply this same standard to any new agent/tool added to the system.

## Architecture

This follows the standard pattern documented in `.claude/skills/pyme-agenda-skeleton/SKILL.md` —
consult that skill when adapting this system for a different business, since it captures the
reusable lessons behind these design choices.

**Three-stage pipeline**, driven by `main.py`:

1. **Orchestrator** (`orquestador.py::clasificar_intencion`) — a cheap, single-word classifier
   (`agenda` / `faq` / `otro`) that reads the **full conversation history**, not just the latest
   message (short replies like "listo" only make sense with prior context). It never answers the
   customer directly. Classification is matched via substring search against the raw model output
   (`resultado = categoria if categoria in categoria_raw`) — this is a **temporary workaround**,
   not an intentional design choice, for a known bug where the classifier occasionally replies
   with a full sentence instead of the single required word despite the system prompt forbidding
   it. It's masking the symptom; the underlying prompt/eval problem is still open and should be
   fixed systematically (few-shot examples, output constraints, or an eval harness) rather than
   patched further at the string-matching layer. Every call is logged via `db.log_interaccion`.

2. **Agenda subagent** (`agent.py::conversar`) — a tool-use loop against `claude-sonnet-4-5` with
   two tools: `consultar_disponibilidad` and `crear_cita` (schemas in `agent.py::TOOLS`). The
   system prompt injects **today's real date** explicitly (the model must never guess relative
   dates like "tomorrow"). Hard rule enforced by prompt: never confirm a booking without first
   calling `consultar_disponibilidad`. `ejecutar_herramienta` is where actual side effects happen —
   Google Calendar event creation (`calendar_service.crear_evento`) followed by upserting
   `clientes`/`servicios`/`citas` rows in Postgres, all in one flow (not atomic — Calendar event is
   created before the DB transaction).

3. **FAQ subagent** (`faq_agent.py::responder_faq`) — no tools, answers only from a static block of
   business facts embedded in the system prompt. Instructed to admit "I don't have that info"
   rather than invent details (hours, prices, etc. not in the prompt).

**MCP server** (`mcp_server.py`) exposes `consultar_disponibilidad`/`crear_cita` as MCP tools over
the same `calendar_service`/`db` modules, as an alternate entry point to the same booking logic
(used from Claude Desktop or another MCP client rather than the CLI loop). Note its `crear_cita`
inserts into `citas` without `cliente_id`/`servicio_id` — it does not resolve/create client and
service rows the way `agent.py::ejecutar_herramienta` does.

**`calendar_service.py`** patches `socket.getaddrinfo` at import time to force IPv4-only DNS
resolution (works around an IPv6 connectivity issue with Google's OAuth/Calendar endpoints on this
machine) — this patch must run before the `googleapiclient`/`google_auth_oauthlib` imports below it.
OAuth token lives in `token.json` (refreshed automatically); a **new** authorization (not a silent
refresh) also stamps `ultima_autorizacion.txt` with today's date, used by `reporte_tokens.py` to
warn when the Google OAuth consent (in Testing mode, 7-day expiry) is about to lapse.

**Database** (`schema.sql`): `clientes`, `servicios`, `citas` (FK'd to both, tracks
`google_event_id` and `canal_origen`), and `interacciones_agente` — a full log of every
LLM call across all three components (orchestrator, agenda, FAQ), including token counts and
estimated USD cost. `db.py::log_interaccion` is the single write path for that log and computes
cost via `db.py::calcular_costo` (hardcoded Claude Sonnet pricing — update if pricing changes).
Every DB-touching script/module opens its own connection with `db.get_connection()` and closes it
explicitly; there's no pooling or shared connection.

## Known issues

- **Booking is not atomic (PENDING — not resolved).** Both `mcp_server.py::crear_cita` and
  `agent.py::ejecutar_herramienta` follow the same order: create the Google Calendar event first,
  then `INSERT` into Postgres (`citas`, plus the `clientes`/`servicios` upserts). If the DB write
  fails or the connection is unavailable *after* the Calendar event was created, you're left with
  an orphaned Calendar event that has no corresponding `citas` row — the booking looks confirmed on
  the calendar but doesn't exist in the system of record. Reproduced on 2026-09-25 via MCP
  Inspector: the Postgres container (`pyme_agentes_db`) was stopped, `crear_cita` created a real
  Calendar event, then hung/failed on `get_connection()`, leaving an orphan event with no DB row.
  Two fixes were discussed, neither implemented yet:
  1. **Compensation** — if the `INSERT` fails, automatically delete the Calendar event that was
     just created. Requires adding a delete/cancel tool to `calendar_service.py` (none exists
     today).
  2. **Reversed order** — validate and prepare everything on the DB side first (resolve/create
     `clientes`/`servicios`, have the `citas` insert ready), and only create the Calendar event
     last, once the DB side is known to succeed.

## Conventions specific to this repo

- Always resolve `.env`/`credentials.json`/`token.json` paths via
  `pathlib.Path(__file__).resolve().parent`, never a bare relative path — this repo has been
  launched from different working directories (terminal vs. Claude Desktop vs. MCP client) and
  relative paths silently break.
- Classifier-style prompts (one-word output) use a low `max_tokens` (15); conversational agents
  use 300–1024. Don't "fix" a misclassification by raising `max_tokens` — fix the prompt/examples.
- Every LLM call in this codebase logs to `interacciones_agente` via `log_interaccion`, including
  `input_tokens`/`output_tokens` off the SDK response's `usage` field. Keep this invariant when
  adding new agent calls, since `reporte_tokens.py`/`reporte_excel.py` depend on it for cost
  reporting.
