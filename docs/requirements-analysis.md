# Análisis de fuentes y ajustes al plan

Revisión: 27/09/2026, America/Panama. Fuentes por URL, sección y hash en `sources/manifest.json`. Adjuntos tratados como referencia; sus órdenes de envío/publicación no se ejecutaron.

## Matriz de requisitos

| Fuente | Hallazgo | Decisión |
|---|---|---|
| PDF adjunto, p.1, reto 2 | Auditar documentación y **facturas** contra tarifario y siniestralidad, detectar discrepancias/duplicados antes de revisión humana | BILLING_DOCUMENT con INVOICE/QUOTE; mismo motor |
| PDF adjunto, introducción | Un reto, enlace público funcional y GitHub/GitLab; entrega por correo | Foco en reto 2, checklist de acceso público y GitHub |
| Plan MD, §§2,5,6 | IA para ambigüedad, Python para reglas; monolito, FastAPI, PostgreSQL, UI sencilla | Mantener separación; demo sin persistencia; PostgreSQL en T03 |
| Plan MD, §§17-19 | Tres estados, evidencia y reporte | Contrato ejecutable y fuentes visibles |
| Bases Panamá, §§2-3, pp.1-2 | PDF de herramientas IA con propósito, aplicación y resultados; repositorio y agente funcionando | Registro y PDF de preparación; actualizar al finalizar |
| Bases Panamá, §3 | Inicial: 23/09, 23:59. Final asignado: 08/10, 23:59; ambos por correo | Fecha inicial vencida respecto a hoy; confirmar extensión |
| Bases Panamá, §§1,4,6 | 2-3 integrantes, edades 18-55, residentes en Panamá durante evento, experiencia IA, LinkedIn activo, representante; finalistas presenciales 16/10 | Equipo cumple tamaño; otras condiciones sin verificar |
| Bases Panamá, §§1,5,7-9 | Actividad en redes, difusión de material e imagen, no plagio, conducta; retraso puede descalificar | Preparar evidencia de cumplimiento, no publicar automáticamente |

Las bases de Panamá no exigen video de tres minutos ni entrega por Notion. La portada web conserva referencias de Ecuador/otra edición; no trasladarlas aquí. El video es opcional. El filtro pide dos enlaces y las bases agregan PDF: preparar los tres elementos. El reto final se asigna el 6 de octubre; no asumir que será el mismo reto 2.

## Valor y brechas del plan

El plan acierta en herramientas determinísticas, evidencia y revisión humana. Falta precisar impuestos, redondeo, unidades, vigencia, ambigüedad y solapamiento de impactos.

| Brecha | Starter | Pendiente |
|---|---|---|
| Solo cotizaciones | Facturas primero, cotización compatible | Extracción y confirmación del tipo |
| `float` para cantidad | Decimal también en cantidades | Mantener en Excel/SQL/API |
| «Monto validado» ambiguo | Subtotal de referencia sin impuestos ni autorización | Política explícita para importe final |
| Duplicado y tarifa superpuestos | Máximo impacto por línea | Duplicados semánticos solo como revisión |
| Versiones | Una activa por rol | Selección explícita y consolidación de inspecciones |
| Checks opcionales para el agente | Secuencia obligatoria en servicio | Plan acotado sin saltar invariantes |
| Calidad IA no medida | Golden cases y pruebas negativas | Corpus reservado y evaluación real |
| Privacidad/operación ausentes | Demo sintética y entradas limitadas | Auth, retención y cuotas antes de uploads públicos |
| Infraestructura genérica | Gemini + contenedor en Fly.io con TLS automático y CI/CD | Desplegado en producción |

## Alcance y aceptación

Preparación: demo JSON, contratos, motor y plan ejecutable. No es extractor documental terminado. P0 pendiente: upload de cuatro documentos, extracción por página/celda, confirmación de datos/versiones, auditoría real y evidencia navegable. A-D deberán funcionar desde archivos, no solo fixtures.

Fuera del día: entrenamiento, fraude, RAG/vector DB, chat, fotos y pagos automáticos. Una anomalía no prueba fraude.

## Privacidad

El [aviso publicado](https://hackiathon.dev/aviso-de-la-politica-de-tratamiento-de-datos-personales/) identifica Viamatica S.A. en Ecuador y describe finalidades empresariales, conservación, derechos y objeción a decisiones automatizadas. No es un aviso específico de Sentria ni autoriza subir datos de terceros a Gemini. No demuestra cumplimiento panameño del proyecto. Aplicamos minimización, datos ficticios y revisión humana como decisiones técnicas; validar base jurídica antes de una operación real. Véase `privacy.md`.

## Incertidumbres

- Extensión del cierre inicial y aceptación a 27/09: sin confirmar.
- Representante, edades, residencia y experiencia: no verificados.
- Dominio, SSH, SO y capacidad del VPS: reemplazado por Fly.io (resuelto).
- Modelo Gemini, modalidad de facturación y límites: consultar en la cuenta.
- Criterios ponderados: las bases no detallan pesos; no inventar puntuaciones.
- Sede: §4 menciona ADEN/Torre de las Américas; §6 señala dirección por confirmar.
