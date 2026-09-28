# Guía de Uso de la Plataforma · Sentria

Esta guía describe cómo utilizar el **Auditor Agéntico de Facturación de Siniestros** tanto en la plataforma web interactiva como en las operaciones diarias de análisis de reclamos automotrices.

---

## 1. Flujo de Trabajo del Analista

El sistema está diseñado como un **copiloto asistencial (Human-in-the-Loop)** para analistas de siniestros y liquidadores. Su objetivo es contrastar de forma automática y transparente la cotización del taller frente a la declaración del asegurado, el informe pericial de inspección y el tarifario pactado por convenio.

El analista cuenta con dos formas de operar la herramienta:
1. **Auditoría Rápida (Expedientes de Referencia):** Permite evaluar con un solo clic casos estándar representativos de la operación diaria.
2. **Gestión y Extracción Documental:** Permite crear nuevos expedientes, cargar archivos digitales (PDF/XLSX) por rol contractual, inspeccionar los ítems y tarifas extraídos con su cita textual comprobable, y auditar en vivo.

---

## 2. Pasos para Operar la Interfaz

### Opción A: Evaluación Inmediata de Casos Tipo
1. Accede a la plataforma web (en vivo en [https://sentria.fly.dev](https://sentria.fly.dev) o en local en `http://127.0.0.1:8000`).
   En la demo pública, introduce el usuario `jurado` y la contraseña `Sentria-Reto2-2026!` cuando el navegador los solicite.
2. En la sección **01 / Selección Rápida**, haz clic sobre cualquiera de los casos preparados:
   - **Caso A (Sin discrepancias):** Caso control donde los precios cumplen el tarifario y los daños corresponden al choque.
   - **Caso B (Sobrecosto tarifario):** Cotización que propone pintura a $55.00/h cuando el convenio fija $45.00/h.
   - **Caso C (Múltiples anomalías):** Cotización con discrepancia de tarifa, cobro duplicado y reparación en zona no afectada.
3. Haz clic en **«Auditar expediente inmediatamente →»**. El sistema ejecutará el cruce documental y mostrará el dictamen al finalizar los controles y la respuesta del proveedor.

---

### Opción B: Gestión y Carga Documental Interactiva
1. Pulsa **«Crear expediente y subir documentos»** junto al identificador del expediente.
   Se generará un expediente nuevo y se abrirán el formulario de carga y los controles de extracción y auditoría.
   Para volver a un caso preparado, selecciona A, B o C.
2. **Tarifario compartido:** El expediente incluye una copia del tarifario estándar. En «Tarifario estándar» puedes descargarlo o reemplazarlo una vez con un XLSX; el cambio se aplica a expedientes nuevos. Los precios iniciales son sintéticos, no contratos comerciales reales.
3. **Carga de tres PDF digitales:** Cotización del taller, declaración del siniestro e inspección. Deja «Detectar automáticamente con Gemini», selecciona el archivo y pulsa «Subir archivo al expediente». El tipo detectado aparece junto al archivo; puedes corregirlo en su selector. La selección manual también está disponible si falla la clasificación.
4. **Extracción y revisión:** Pulsa «Extraer evidencia documental de archivos activos». Gemini interpreta el diseño de cada proveedor. Comprueba descripción, código de servicio, unidad, cantidades, precios, totales declarados y citas. Corrige los campos editables cuando sea necesario. Si cambias el tipo de documento, extrae nuevamente. Un dato ausente conserva su valor pendiente; no significa cero.
5. **Confirmación y auditoría:** Pulsa «Confirmar normalización y auditar expediente en vivo». El motor calcula las diferencias con aritmética exacta y prepara una recomendación para el analista. La cotización se revisa antes de autorizar la reparación y generar la factura.

Los PDF escaneados todavía requieren OCR. La calidad de extracción puede variar por proveedor y siempre exige revisión humana. En modo `mock`, la clasificación automática está deshabilitada y el parser solo reconoce los formatos sintéticos de referencia.

---

## 3. Interpretación del Dictamen de Auditoría

El resultado se presenta en la sección **03 / Dictamen de Auditoría** con tres bloques informativos:

### A. Estado Operativo del Expediente
* **Candidato para aprobación:**  
  Los controles automáticos no detectaron sobrecostos, duplicidades ni reparaciones inconsistentes. El expediente está listo para la firma y autorización final del analista.
* **Revisión requerida:**  
  Se detectaron una o más observaciones que requieren intervención humana (solicitar corrección de la cotización al taller o validar autorizaciones especiales con la aseguradora).
* **Información requerida:**  
  Falta documentación esencial (por ejemplo, el tarifario de convenio) o algún archivo presenta ilegibilidad. El sistema suspende la evaluación hasta contar con la documentación requerida.

### B. Métricas Financieras Clave
* **Importe cotizado:** Monto total de la cotización del taller, incluyendo los impuestos declarados (ej. 7% ITBMS de Panamá).
* **Diferencia potencial (sin impuestos):** Suma exacta de los sobrecostos identificados por discrepancias de tarifa o cobros duplicados. Cada impacto se calcula una sola vez por línea de cobro.
* **Subtotal de referencia:** Monto ajustado que la aseguradora reconocería como base para la liquidación, sujeto a la confirmación de las partidas en observación.

### C. Desglose de Hallazgos con Evidencia
Cada inconsistencia encontrada se explica en lenguaje de negocio claro:
* **Discrepancia en tarifa convenida:** Señala la diferencia matemática entre lo facturado y el precio máximo de convenio, mostrando la fórmula aplicada y la cita de ambas fuentes.
* **Cobro posiblemente duplicado:** Identifica servicios o piezas cobradas más de una vez para la misma intervención física.
* **Reparación ajena o no respaldada en el siniestro:** Alerta sobre reparaciones facturadas en zonas del vehículo que no sufrieron daños según el informe del siniestro y la peritación técnica.

---

## 4. Recorrido Técnico y Auditoría Explicable

Al desplegar **«Ver fases del proceso de auditoría y recorrido técnico»**, el analista y los auditores pueden inspeccionar la trazabilidad completa del dictamen en 5 etapas secuenciales:
1. **Paso 01 · Verificación de Integridad Documental:** Comprueba que todos los documentos requeridos estén presentes y sean legibles.
2. **Paso 02 · Verificación de Cotización y Líneas:** Valida la estructura de conceptos, cantidades e importes unitarios de la factura.
3. **Paso 03 · Control Tarifario Determinista:** Cruza cada línea cotizada contra la tarifa pactada por convenio mediante cálculo financiero en Python.
4. **Paso 04 · Evaluación de Coherencia Semántica con IA:** Valida mediante inteligencia artificial si las piezas reparadas tienen correlación causal con los daños del choque.
5. **Paso 05 · Consolidación Matemática Final:** Aplica reglas de negocio y agrega las diferencias sin duplicar impactos.

El botón **«Descargar reporte JSON»** permite exportar el dictamen completo con estructura normalizada para su integración con sistemas Core de aseguradoras o gestores documentales.

---

## 5. Modos de Ejecución

* **Modo Producción (Google Gemini):** Utiliza `gemini-2.5-flash-lite` para la evaluación semántica contextual de los daños vehiculares, combinada con cálculo determinista en Python para todos los montos en dinero.
* **Modo Simulación Local:** Permite pruebas sin conexión externa ni consumo de cuota de API, evaluando los expedientes de prueba con respuestas predefinidas idénticas para garantizar reproducibilidad total en entornos de desarrollo y evaluación técnica.
