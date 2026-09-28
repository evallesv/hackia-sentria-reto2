# Auditor Agéntico de Facturación de Siniestros · Equipo Sentria

> **🚀 Enlace público del agente funcional en producción:** [https://sentria.fly.dev](https://sentria.fly.dev)  
> **Healthcheck del sistema:** [https://sentria.fly.dev/healthz](https://sentria.fly.dev/healthz) · **CI/CD:** Despliegue automático vía GitHub Actions a Fly.io (Linux ARM64, 512 MB RAM)  
> **Repositorio de código:** [https://github.com/evallesv/hackia-sentria-reto2](https://github.com/evallesv/hackia-sentria-reto2)  
> **Entrega oficial:** Reto 2 para [hackIAthon Panamá (Viamatica / ADEN)](https://hackiathon.dev/wp-content/uploads/2026/08/hackIAthon-Panama-Bases-y-Entregables.pdf) dirigido a `hackiathon@viamatica.com`

---

## 1. Planteamiento del Problema

En la industria de seguros de automóviles, cuando un vehículo asegurado sufre un accidente, se inicia un proceso de reparación que genera múltiples documentos desconectados:
1. **La declaración del asegurado (Siniestro):** Describe cómo ocurrió el accidente y qué partes del vehículo fueron afectadas.
2. **El informe pericial (Inspección):** El reporte técnico emitido por el ajustador o taller donde se verifican visualmente los daños mecánicos y de carrocería.
3. **La factura o cotización de cobro (Taller):** El desglose de horas de mano de obra, insumos de pintura y repuestos que el taller cobra a la aseguradora.
4. **El tarifario contractual pactado:** El convenio vinculante entre la aseguradora y el taller donde se fijan las tarifas máximas permitidas por hora y unidad.

### El dolor en la operación diaria
Actualmente, los analistas de siniestros deben revisar manualmente cada expediente cruzando estos 4 documentos a la vez con calculadora en mano. Este proceso artesanal presenta tres grandes problemas:
* **Lentitud y cuello de botella:** Toma entre 30 y 45 minutos por expediente, retrasando la autorización de reparaciones y el pago a los talleres.
* **Fuga de capital por sobrecostos invisibles:** La fatiga humana hace que pasen desapercibidos cobros por encima de la tarifa pactada, piezas facturadas dos veces o arreglos de zonas del auto que no tuvieron nada que ver con el choque reportado.
* **Fricción en las liquidaciones:** Discusiones entre aseguradoras y talleres por falta de un informe objetivo y transparente que explique exactamente el porqué de cada observación.

---

## 2. Supuestos Iniciales y Principios del Agente

Para construir una herramienta confiable, auditable y segura para el negocio, establecimos tres principios rectores:

1. **Copiloto asistencial (Human-in-the-Loop):**  
   El agente de IA **nunca autoriza un pago ni rechaza una factura por su cuenta**. Su propósito es auditar exhaustivamente el expediente, detectar las inconsistencias y preparar un informe fundamentado para que el analista humano tome la decisión final en segundos. El sistema emite únicamente estados operativos de recomendación: `CANDIDATE_FOR_APPROVAL` (sin anomalías detectadas), `REVIEW_REQUIRED` (atención en tarifas o daños) o `INFORMATION_REQUIRED` (documentación faltante).

2. **Determinismo financiero (La IA no calcula dinero):**  
   Los modelos de lenguaje (LLMs) son excepcionales interpretando texto libre y descripciones mecánicas ambiguas, pero no son calculadoras financieras y pueden alucinar en operaciones aritméticas. Por diseño estricto, **el LLM nunca calcula dinero, sumas ni diferencias**. Los cálculos de tarifas, horas y subtotales se ejecutan mediante código determinista con aritmética `Decimal` y redondeo estándar `ROUND_HALF_UP` exacto a centavos de dólar (USD).

3. **Cero alucinaciones y fundamentación documental estricta:**  
   Todo hallazgo debe estar respaldado por una cita textual exacta indicando el documento de origen y su ubicación comprobable (página del PDF o fila/hoja del Excel). Si una tarifa no está convenida o el documento es ilegible, el sistema no asume ni inventa datos: se detiene y solicita información.

4. **Tratamiento ético y privacidad de datos:**  
   En estricto apego al [Aviso de Política de Tratamiento de Datos Personales de hackIAthon](https://hackiathon.dev/aviso-de-la-politica-de-tratamiento-de-datos-personales/), toda la información utilizada en las pruebas es **100% sintética y ficticia**, sin contener datos personales identificables (PII) de asegurados ni información financiera confidencial real.

---

## 3. ¿Qué problema resuelve Sentria?

| Desafío Tradicional (Revisión manual) | Con Sentria (Auditor Agéntico) |
| :--- | :--- |
| **30 - 45 minutos** por expediente. | **Menos de 2 segundos** de auditoría automatizada. |
| Fugas de dinero por tarifas no contractuales. | **Detección matemática instantánea:** ej. *(55 − 45) × 8 = $80.00 USD* de sobrecosto en pintura. |
| Inclusión de repuestos ajenos al siniestro. | **Verificación semántica de daños:** alerta si se factura suspensión en un choque frontal. |
| Cobros duplicados de mano de obra. | **Identificación de redundancias:** detecta cobros repetidos sobre el mismo componente. |
| Decisiones opacas o arbitrarias. | **Transparencia total:** reporte con citas textuales y cálculo paso a paso. |

### Resultados en los Casos de Referencia

| Caso | Facturado USD | Diferencia potencial sin impuestos USD | Subtotal de referencia USD | Estado Operativo | Explicación de Negocio |
| :--- | :---:| :---:| :---:| :--- | :--- |
| **A: Sin discrepancias** | $1,850.00 | $0.00 | $1,850.00 | `CANDIDATE_FOR_APPROVAL` | Todos los precios respetan el tarifario y los daños corresponden al choque. |
| **B: Sobrecosto tarifario** | $1,930.00 | $80.00 | $1,850.00 | `REVIEW_REQUIRED` | El taller cobró $55.00/h de pintura en vez de los $45.00/h pactados por convenio. |
| **C: Múltiples anomalías** | $2,430.00 | $250.00 | $2,180.00 | `REVIEW_REQUIRED` | Facturaron alineación duplicada y repuestos sin respaldo de daño en el siniestro. |
| **D: Falta tarifario** | $1,930.00 | $0.00 (no evaluado) | *No disponible* | `INFORMATION_REQUIRED` | No hay tarifario oficial vigente registrado; se requiere gestión humana. |

---

## 4. Arquitectura y Tecnologías

El sistema está construido como un monolito modular moderno en **Python 3.13** y **FastAPI**:
* **Extracción de Documentos:** Parseo nativo de PDFs con `pypdf` (extrayendo texto por página y detectando documentos escaneados) y lectura de tarifarios en Excel con `openpyxl` en modo de solo lectura estricto.
* **Persistencia Relacional e Integridad:** Modelado declarativo con **SQLAlchemy 2** y migraciones automáticas con **Alembic**, operando sobre SQLite en modo WAL montado en volumen persistente privado en Fly.io.
* **Idempotencia de Auditorías:** Claves criptográficas por combinación de `claim_id + snapshot_hash + rule_version + prompt_version + model_name`, garantizando que reintentos idénticos no generen duplicados ni consumo innecesario de tokens.
* **Inteligencia Artificial:** Conexión con **Google Gemini (`gemini-2.5-flash-lite`)** mediante el SDK oficial `google-genai` con *Structured Outputs / Function Calling* estricto y salvaguardas de timeout y token budgeting.
* **Interfaz de Usuario:** Interfaz web sobria, profesional y moderna servida desde FastAPI con plantillas Jinja2 y JavaScript nativo sin dependencias pesadas de Node.

---

## 5. Instrucciones para Ejecución y Evaluación

### Opción 1: Probar en Producción (Recomendada)
Accede directamente a la plataforma en vivo: **[https://sentria.fly.dev](https://sentria.fly.dev)**
1. **Auditoría Rápida:** Selecciona cualquiera de los casos preparados (**A**, **B**, **C** o **D**) y haz clic en **«Auditar expediente inmediatamente →»**.
2. **Gestión y Extracción Documental:** Haz clic en **«Inspeccionar documentos del caso ↓»** o desplázate a la sección **02 / Documentación y Extracción** para:
   * Subir nuevos documentos digitales (Factura PDF, Declaración PDF, Inspección PDF y Tarifario XLSX).
   * Extraer ítems de cobro y tarifas con sus citas textuales de evidencia (página y texto original).
   * Confirmar la normalización y auditar en tiempo real sobre el expediente activo.
3. **Dictamen y Trazabilidad:** Revisa el estado operativo (`CANDIDATE_FOR_APPROVAL`, `REVIEW_REQUIRED`, `INFORMATION_REQUIRED`), las métricas financieras (facturado, diferencia calculada y subtotal de referencia), el desglose de hallazgos con citas de evidencia y el recorrido técnico de 5 fases explicables con descarga del dictamen en JSON.

### Opción 2: Ejecución Local
Requisitos: Python 3.12 o 3.13 y [uv](https://docs.astral.sh/uv/).

```bash
# 1. Clonar e instalar dependencias bloqueadas
git clone https://github.com/evallesv/hackia-sentria-reto2.git
cd hackia-sentria-reto2
uv sync --locked --all-groups

# 2. Ejecutar la suite completa de calidad (lint, formato, 62 pruebas y evaluación A-D)
make check

# 3. Iniciar el servidor local
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Abre en tu navegador [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 6. Documentación Adicional

- [Guía de Usuario](docs/user-guide.md)
- [Análisis de Requisitos y Bases](docs/requirements-analysis.md)
- [Arquitectura del Sistema](docs/architecture.md)
- [Contratos de Datos y Esquemas JSON](docs/contracts.md)
- [Ingeniería de Inteligencia Artificial](docs/ai-engineering.md)
- [Registro de Herramientas IA (PDF Requerido)](docs/delivery/herramientas-ia-preparacion.pdf)
- [Borrador de Envío de Entrega](docs/delivery/submission.md)

---

## 7. Equipo Sentria

| Integrante | Rol en el Proyecto | Perfil Profesional |
| :--- | :--- | :--- |
| **Eduardo Valle** | Representante del Equipo / Arquitectura & Integración | [LinkedIn](https://linkedin.com/in/evallesv) |
| **Jose Muñoz** | Motor de Reglas Financieras & Persistencia | [LinkedIn](https://linkedin.com/in/jose-salcedo-442663293) |
| **Santiago López** | Plataforma Web & Experiencia de Usuario | [LinkedIn](https://linkedin.com/in/santiago-lopez-software-engineer) |

**Licencia:** Software de código abierto bajo licencia **GPL-3.0** (ver [LICENSE](LICENSE)).
