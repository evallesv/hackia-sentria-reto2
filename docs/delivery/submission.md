# Entrega Final · Reto 2: Auditor Agéntico de Siniestros

**Destinatario:** `hackiathon@viamatica.com`  
**Asunto:** Reto 2 - Equipo Sentria - Eduardo Valle, Jose Muñoz y Santiago López

---

Estimado comité evaluador de hackIAthon Panamá:

El equipo **Sentria** presenta su solución de **Auditor Agéntico de Facturación de Siniestros Automotrices** para el **Reto 2**.

Nuestra solución contrasta facturas y cotizaciones de talleres contra el reporte del siniestro, el informe de inspección y los tarifarios pactados. Implementa una arquitectura híbrida donde los cálculos financieros y validaciones de tarifas son estrictamente deterministas (aritmética `Decimal` con redondeo `ROUND_HALF_UP`), mientras que los modelos de lenguaje (Gemini 2.5) evalúan la consistencia semántica y correspondencia de daños mediante *function calling* estructurado, impidiendo alucinaciones o modificaciones no auditadas.

### Entregables del Reto

1. **Agente en Ejecución (URL Pública HTTPS):**
   * **Plataforma Web:** [https://sentria.fly.dev](https://sentria.fly.dev)
   * **Healthcheck del Sistema:** [https://sentria.fly.dev/healthz](https://sentria.fly.dev/healthz)
   * *Alojado en contenedor Linux ARM64 en Ashburn, VA con TLS automático y modo Gemini activo.*

2. **Repositorio de Código:**
   * **GitHub:** [https://github.com/evallesv/hackia-sentria-reto2](https://github.com/evallesv/hackia-sentria-reto2)
   * Incluye código fuente completo, contratos Pydantic y JSON Schemas, suite de 64 pruebas automatizadas, datos de prueba sintéticos y pipelines de CI/CD (GitHub Actions).

3. **Registro de Herramientas de IA (PDF Adjunto):**
   * Documento: `docs/delivery/herramientas-ia-preparacion.pdf` (generado conforme a las bases del hackIAthon con el desglose de Google Antigravity y Gemini API).

4. **Instrucciones para Evaluación Rápida:**
   * Acceder a [https://sentria.fly.dev](https://sentria.fly.dev).
   * **Caso A (Sin discrepancias):** Pulsa "Auditar". El sistema valida precios contra tarifario y confirma consistencia semántica (`CANDIDATE_FOR_APPROVAL`, diferencia $0.00).
   * **Caso B (Discrepancia tarifaria):** Pulsa "Auditar". Detecta sobrecosto en tarifa de pintura: (55 − 45) × 8 = $80.00 USD (`REVIEW_REQUIRED`).
   * **Caso C (Múltiples anomalías):** Detecta duplicado de alineación, sobrecosto y reparación no respaldada ($250.00 USD de impacto).
   * **Caso D (Tarifario ausente):** Identifica falta de información contractual requerida (`INFORMATION_REQUIRED`).
   * En cada caso se puede expandir la traza de auditoría, las citas textuales de la evidencia y descargar el reporte estructurado en JSON.

### Equipo: Sentria

* **Eduardo Valle** (Representante) | [LinkedIn](https://linkedin.com/in/evallesv)
* **Jose Muñoz** | [LinkedIn](https://linkedin.com/in/jose-salcedo-442663293)
* **Santiago López** | [LinkedIn](https://linkedin.com/in/santiago-lopez-software-engineer)

### Alcance Técnico y Salvaguardas
* **Determinismo Financiero:** El LLM no calcula dinero ni define el estado final de pago; solo clasifica y cita evidencia documental.
* **Seguridad y Privacidad:** Datos de prueba 100% sintéticos. Secretos y credenciales protegidos fuera del control de versiones.
* **Trazabilidad:** Toda discrepancia cuenta con ID de documento, ubicación y texto fuente comprobable.
