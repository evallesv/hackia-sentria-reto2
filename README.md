# Sentria · Auditor agéntico de siniestros

Base de implementación del **reto 2 de hackIAthon Panamá**: contrastar facturas y cotizaciones de un taller con siniestro, inspección y tarifario, con cálculos reproducibles y evidencia para un auditor humano.

**Estado: entorno de desarrollo funcional, no MVP documental terminado.** Incluye demo guiada, motor financiero, casos sintéticos, pruebas, contratos y adaptador Gemini. La demo predeterminada simula la revisión semántica; carga/extracción de PDF y Excel, persistencia y validación con Gemini real siguen en el [plan](docs/implementation-plan.md).

## Empezar hoy

Requisitos: Python 3.12 o 3.13 y [uv](https://docs.astral.sh/uv/). Python 3.13 es la versión de desarrollo y del contenedor.

```bash
uv sync --locked --all-groups
cp .env.example .env
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Abre [la plataforma local](http://127.0.0.1:8000). Selecciona **B**, pulsa **Auditar** y abre `RATE_MISMATCH`: `(55 − 45) × 8 = 80 USD`. La interfaz explica cada paso, muestra fuentes y descarga el reporte JSON. [Guía completa](docs/user-guide.md).

```bash
make check                           # formato, lint, pruebas y golden cases
make format                          # autoformato y corrección automática con ruff
make lock                            # sincroniza uv.lock y exporta requirements.txt con hashes
make contracts                       # exporta JSON Schema desde Pydantic
make tools-pdf                       # genera el PDF de registro de herramientas IA
docker compose up --build            # alternativa local con Docker
```

No se necesita base de datos ni clave para la simulación. Los datos de `data/demo/` son ficticios; los `.txt` son evidencia de fixtures, **no PDFs extraídos**.

## Gemini y Oracle ARM64

Guarda `GEMINI_API_KEY` en `.env`, consulta modelos y elige uno disponible con function calling:

```bash
uv run python -m scripts.list_gemini_models
# Editar .env: GEMINI_MODEL=<identificador devuelto>, AI_MODE=gemini
uv run python -m scripts.smoke_gemini  # hasta 3 llamadas según tarifa de tu cuenta
```

Reinicia el servidor después de cambiar variables. Si la IA falla, el resultado solicita información; nunca se sustituye silenciosamente por simulación. El adaptador hace una llamada acotada y el servidor ejecuta los checks obligatorios.

Para el VPS: [guía Oracle ARM64, DNS, TLS y rollback](docs/deployment-oracle.md) y `compose.oracle.yaml`. No se ha desplegado ni se han usado claves. OpenCode Go se usará para desarrollar por tareas; Gemini atenderá la aplicación. [Guía de agentes económicos](docs/low-cost-agents.md).

## Resultados de referencia

| Caso | Facturado USD | Diferencia potencial sin impuestos USD | Subtotal de referencia USD | Estado |
|---|---:|---:|---:|---|
| A: sin discrepancias | 1,850.00 | 0.00 | 1,850.00 | CANDIDATE_FOR_APPROVAL |
| B: tarifa de pintura | 1,930.00 | 80.00 | 1,850.00 | REVIEW_REQUIRED |
| C: tarifa, duplicado, reparación sin respaldo | 2,430.00 | 250.00 | 2,180.00 | REVIEW_REQUIRED |
| D: sin tarifario | 1,930.00 | 0.00 no evaluado | No disponible | INFORMATION_REQUIRED |

El subtotal de referencia **no autoriza un pago**. Un posible duplicado requiere confirmación; un hallazgo semántico no produce un descuento automático. No se calcula un impuesto fiscal ni se asume una tasa local.

## Documentación y estructura

- [Análisis del reto, bases y privacidad](docs/requirements-analysis.md).
- [Arquitectura](docs/architecture.md), [contratos y API](docs/contracts.md), [ingeniería de IA](docs/ai-engineering.md).
- [Plan por horas y tareas](docs/implementation-plan.md), [OpenCode Go](docs/low-cost-agents.md).
- [Privacidad](docs/privacy.md), [publicación y entrega](docs/delivery/checklist.md).
- [Verificaciones ejecutadas y límites](docs/verification.md).

`app/models.py` define contratos; `app/audit/` calcula; `app/agent/` integra IA; `app/services/` coordina. `templates/` y `static/` contienen la UI sin build Node. `tests/` y `scripts/evaluate.py` verifican comportamiento. `docs/tasks/` contiene encargos acotados para continuar.

## Equipo

| Integrante | Perfil proporcionado |
|---|---|
| Eduardo Valle | [LinkedIn](https://linkedin.com/in/evallesv) |
| Jose Muñoz | [LinkedIn](https://linkedin.com/in/jose-salcedo-442663293) |
| Santiago López | [LinkedIn](https://linkedin.com/in/santiago-lopez-software-engineer) |

Los roles del plan son propuestas, no inferencias de experiencia. Representante oficial y elegibilidad por confirmar.

**Fecha a resolver:** las [bases de Panamá](https://hackiathon.dev/wp-content/uploads/2026/08/hackIAthon-Panama-Bases-y-Entregables.pdf), §3, fijan el cierre inicial para el **23/09/2026, 23:59**. Esta preparación es del **27/09/2026**. Confirmar eventual extensión; no se presume concedida. Las bases también exigen un PDF de herramientas de IA.

Se conserva la licencia **GPL-3.0** existente en [LICENSE](LICENSE). Remoto configurado: [evallesv/hackia-sentria-reto2](https://github.com/evallesv/hackia-sentria-reto2).
