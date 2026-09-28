# Sentria · Revisión de cotizaciones de siniestros asistida por IA

> **Etapa:** prototipo funcional presentado al filtro previo de hackIAthon Panamá.\
> **Aplicación de demostración:** [https://sentria.fly.dev](https://sentria.fly.dev)\
> **Healthcheck del sistema:** [https://sentria.fly.dev/healthz](https://sentria.fly.dev/healthz) · **CI/CD:** Despliegue automático vía GitHub Actions a Fly.io  
> **Repositorio de código:** [https://github.com/evallesv/hackia-sentria-reto2](https://github.com/evallesv/hackia-sentria-reto2)  
> **Propuesta para el filtro previo:** Reto 2 de [hackIAthon Panamá (Viamatica / ADEN)](https://hackiathon.dev/wp-content/uploads/2026/08/hackIAthon-Panama-Bases-y-Entregables.pdf), dirigida a `hackiathon@viamatica.com`.

Sentria ayuda al analista a revisar la cotización de un taller antes de autorizar la reparación y emitir la factura. Contrasta documentos y tarifas, identifica diferencias y prepara observaciones con evidencia para la decisión humana.

**Alcance agéntico:** es una aplicación con IA integrada y un flujo agéntico acotado. El servidor coordina las verificaciones; Gemini interpreta documentos y devuelve evaluaciones estructuradas mediante *function calling*. Python valida las referencias, ejecuta los controles obligatorios, calcula los importes y determina el estado operativo. El modelo no elige libremente el siguiente paso ni autoriza reparaciones o pagos.

---

## 1. Planteamiento del Problema

En la industria de seguros de automóviles, cuando un vehículo asegurado sufre un accidente, se inicia un proceso de reparación que genera múltiples documentos desconectados:
1. **La declaración del asegurado (Siniestro):** Describe cómo ocurrió el accidente y qué partes del vehículo fueron afectadas.
2. **El informe pericial (Inspección):** El reporte técnico emitido por el ajustador o taller donde se verifican visualmente los daños mecánicos y de carrocería.
3. **La cotización del taller:** El desglose de mano de obra, insumos y repuestos propuestos antes de autorizar la reparación y emitir una factura.
4. **El tarifario estándar:** Se configura una vez y se incorpora automáticamente a cada expediente nuevo. La demo incluye precios sintéticos; el analista puede sustituirlos desde la interfaz para futuros expedientes.

### El dolor en la operación diaria
Actualmente, los analistas de siniestros deben revisar manualmente cada expediente cruzando estos 4 documentos a la vez con calculadora en mano. Este proceso artesanal presenta tres grandes problemas:
* **Lentitud y cuello de botella:** El cruce manual de documentos y tarifas consume tiempo del analista y retrasa la revisión de las reparaciones propuestas.
* **Fuga de capital por sobrecostos invisibles:** La fatiga humana hace que pasen desapercibidos cobros por encima de la tarifa pactada, piezas facturadas dos veces o arreglos de zonas del auto que no tuvieron nada que ver con el choque reportado.
* **Fricción en las liquidaciones:** Discusiones entre aseguradoras y talleres por falta de un informe objetivo y transparente que explique exactamente el porqué de cada observación.

---

## 2. Supuestos Iniciales y Principios del Prototipo

El prototipo se construye sobre cuatro principios:

1. **Copiloto asistencial (Human-in-the-Loop):**  
   El sistema **nunca autoriza un pago ni aprueba o rechaza una cotización por su cuenta**. Prepara observaciones para que el analista humano tome la decisión final. Emite únicamente tres estados operativos: **candidato para aprobación** (sin anomalías detectadas en los controles ejecutados), **revisión requerida** (observaciones que requieren evaluación) o **información requerida** (evidencia o datos insuficientes).

2. **Determinismo financiero (La IA no calcula dinero):**  
   Los modelos de lenguaje (LLMs) son excepcionales interpretando texto libre y descripciones mecánicas ambiguas, pero no son calculadoras financieras y pueden alucinar en operaciones aritméticas. Por diseño estricto, **el LLM nunca calcula dinero, sumas ni diferencias**. Los cálculos de tarifas, horas y subtotales se ejecutan mediante código determinista con aritmética `Decimal` y redondeo estándar `ROUND_HALF_UP` exacto a centavos de dólar (USD).

3. **Validación de evidencia documental:**\
   Los hallazgos requieren referencias al documento activo y una ubicación comprobable (página del PDF o fila/hoja del Excel). La evidencia ausente, la extracción ilegible, una tarifa ambigua o un fallo del proveedor impiden el estado candidato para aprobación. Comprobar que una cita existe no garantiza que la interpretación del modelo sea correcta: el analista debe revisar su pertinencia.

4. **Tratamiento ético y privacidad de datos:**  
   La demostración utiliza **datos sintéticos y ficticios**, sin expedientes reales de asegurados ni información financiera confidencial. La evaluación debe realizarse con archivos sintéticos; el uso operativo con datos reales requiere definir los controles de acceso, privacidad y tratamiento correspondientes.

---

## 3. ¿Qué problema resuelve Sentria?

| Desafío Tradicional (Revisión manual) | Con Sentria |
| :--- | :--- |
| Cruce manual de documentos y tarifas. | Clasificación y extracción con Gemini, seguidas de revisión humana y auditoría automatizada. La latencia depende del proveedor. |
| Fugas de dinero por tarifas no contractuales. | **Cálculo determinista:** ej. *(55 − 45) × 8 = $80.00 USD* de sobrecosto en pintura. |
| Inclusión de repuestos ajenos al siniestro. | **Revisión semántica asistida:** compara las reparaciones propuestas con los daños documentados; su interpretación requiere revisión humana. |
| Cobros duplicados de mano de obra. | **Identificación de redundancias:** detecta cobros repetidos sobre el mismo componente. |
| Decisiones difíciles de justificar. | **Trazabilidad:** reporte con referencias documentales y desglose del cálculo. |

### Resultados en los Casos de Referencia

| Caso | Cotizado USD (impuestos declarados) | Diferencia potencial sin impuestos USD | Subtotal de referencia USD | Estado Operativo | Explicación de Negocio |
| :--- | :---:| :---:| :---:| :--- | :--- |
| **A: Sin discrepancias** | $1,979.50 | $0.00 | $1,850.00 | Candidato para aprobación | Los controles del caso sintético no detectan discrepancias. |
| **B: Sobrecosto tarifario** | $2,065.10 | $80.00 | $1,850.00 | Revisión requerida | El taller cobró $55.00/h de pintura en vez de los $45.00/h pactados por convenio. |
| **C: Múltiples anomalías** | $2,600.10 | $250.00 | $2,180.00 | Revisión requerida | Sobrecosto tarifario y alineación duplicada; el respaldo de la reparación de dirección requiere revisión del analista. |

Estos casos sintéticos muestran el comportamiento del prototipo. No constituyen una medición de precisión semántica ni de ahorro de tiempo con expedientes reales. La evaluación de documentos y formatos de proveedores no vistos requiere un corpus reservado y criterios de aceptación adicionales.

> **Nota sobre impuestos y localización:** Las cotizaciones sintéticas de demostración aplican la tasa del **7% de ITBMS de Panamá** (subtotal más 7%). Para otros países o jurisdicciones fiscales, la tasa y denominación se configuran de forma manual mediante las variables `TAX_RATE` (ej. `0.16` para IVA México) y `TAX_NAME` en la configuración del sistema. La *Diferencia potencial* se calcula sobre la base neta contratada sin duplicar cálculos fiscales automáticos.

---

## 4. Arquitectura y Tecnologías

El sistema está construido como un monolito modular moderno en **Python 3.13** y **FastAPI**:
* **Clasificación y extracción:** `pypdf` obtiene texto por página y Gemini clasifica y extrae datos de distintos diseños de PDF con salida JSON estructurada. El servidor exige citas textuales existentes y comprueba que los importes aparezcan en ellas. El usuario puede corregir tipos, servicios, unidades e importes antes de confirmar. Los tarifarios XLSX se leen con `openpyxl`; las fórmulas en tarifas y las unidades desconocidas se rechazan.
* **Persistencia Relacional e Integridad:** Modelado declarativo con **SQLAlchemy 2** y migraciones automáticas con **Alembic**, operando sobre SQLite en modo WAL montado en volumen persistente privado en Fly.io.
* **Idempotencia de Auditorías:** Claves criptográficas por combinación de `claim_id + snapshot_hash + rule_version + prompt_version + model_name`, garantizando que reintentos idénticos no generen duplicados ni consumo innecesario de tokens.
* **Inteligencia Artificial:** Conexión con **Google Gemini (`gemini-2.5-flash-lite`)** mediante el SDK oficial `google-genai` con *Structured Outputs / Function Calling* estricto y salvaguardas de timeout y token budgeting.
* **Interfaz de Usuario:** Interfaz web sobria, profesional y moderna servida desde FastAPI con plantillas Jinja2 y JavaScript nativo sin dependencias pesadas de Node.

---

## 5. Instrucciones para Ejecución y Evaluación

### Opción 1: Evaluar la Demostración Desplegada
Accede directamente a la plataforma en vivo: **[https://sentria.fly.dev](https://sentria.fly.dev)**
El navegador solicitará las credenciales compartidas del jurado:

- **Usuario:** `jurado`
- **Contraseña:** `Sentria-Reto2-2026!`

El acceso protege la interfaz, la API y las descargas de documentos. `/healthz` permanece público para monitoreo.
Estas credenciales son públicas para facilitar la evaluación con datos sintéticos; para uso privado, configura otra contraseña mediante `DEMO_PASSWORD`.

1. **Auditoría Rápida:** Selecciona cualquiera de los casos preparados (**A**, **B** o **C**) y haz clic en **«Auditar expediente inmediatamente →»**.
2. **Gestión y Extracción Documental:** Haz clic en **«Inspeccionar documentos del caso ↓»** o desplázate a la sección **02 / Documentación y Extracción** para:
   * Para cargar tus propios archivos sintéticos, pulsa **«Crear expediente y subir documentos»**. Se abrirá el formulario de carga y la guía de extracción y auditoría.
   * Subir tres PDF digitales: cotización, declaración e inspección. Gemini detecta el tipo; el selector manual permite corregirlo. El tarifario ya está incorporado. En «Tarifario estándar» puedes descargarlo y sustituirlo una sola vez; cada expediente conserva la versión con la que fue creado.
   * Extraer los datos mediante Gemini, revisar las citas y corregir servicios, cantidades, unidades, precios y totales declarados.
   * Confirmar la normalización y auditar en tiempo real sobre el expediente activo.
3. **Dictamen y Trazabilidad:** Revisa el estado operativo (candidato para aprobación, revisión requerida o información requerida), las métricas financieras (cotizado, diferencia calculada y subtotal de referencia), el desglose de hallazgos con citas de evidencia y el recorrido técnico de 5 fases explicables con descarga del dictamen en JSON.

### Opción 2: Ejecución Local
Requisitos: Python 3.12 o 3.13 y [uv](https://docs.astral.sh/uv/).

```bash
# 1. Clonar e instalar dependencias bloqueadas
git clone https://github.com/evallesv/hackia-sentria-reto2.git
cd hackia-sentria-reto2
uv sync --locked --all-groups

# 2. Ejecutar la suite completa de calidad (lint, formato, 108 pruebas y evaluación A-D interna)
make check

# 3. Iniciar el servidor local
STANDARD_TARIFF_ENABLED=true uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Para clasificación y extracción reales configura `AI_MODE=gemini`, `GEMINI_MODEL` y `GEMINI_API_KEY` fuera de Git. El modo `mock` usa un parser limitado a los formatos de prueba y requiere selección manual del tipo. El OCR local para PDF escaneados se activa con `OCR_ENABLED=true`; Docker incluye Tesseract en español e inglés. En instalaciones locales requiere el ejecutable Tesseract y esos idiomas. Procesa hasta cinco páginas escaneadas por documento a 300 DPI, con límites de resolución, tiempo y confianza; números dudosos bloquean la extracción. La confirmación exige cotejar texto e importes con el PDF original. No se garantiza extracción correcta de todos los proveedores: es obligatoria la revisión humana. El caso D permanece como regresión técnica de ausencia de tarifa, pero se retira de la selección del jurado.

Abre en tu navegador [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 6. Documentación Adicional

- [Guía de Usuario](docs/user-guide.md)
- [Análisis de Requisitos y Bases](docs/requirements-analysis.md)
- [Arquitectura del Sistema](docs/architecture.md)
- [Contratos de Datos y Esquemas JSON](docs/contracts.md)
- [Ingeniería de Inteligencia Artificial](docs/ai-engineering.md)
- [Registro de Herramientas IA (PDF Requerido)](docs/delivery/herramientas-ia.pdf)
- [Borrador de Envío de Entrega](docs/delivery/submission.md)

---

## 7. Equipo Sentria

| Integrante | Rol en el Proyecto | Perfil Profesional |
| :--- | :--- | :--- |
| **Eduardo Valle** | Representante del Equipo / Arquitectura & Integración | [LinkedIn](https://linkedin.com/in/evallesv) |
| **Jose Muñoz** | Motor de Reglas Financieras & Persistencia | [LinkedIn](https://linkedin.com/in/jose-salcedo-442663293) |
| **Santiago López** | Plataforma Web & Experiencia de Usuario | [LinkedIn](https://linkedin.com/in/santiago-lopez-software-engineer) |

**Licencia:** Software de código abierto bajo licencia **GPL-3.0** (ver [LICENSE](LICENSE)).
