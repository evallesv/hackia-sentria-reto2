# Tratamiento de datos y controles

## Fuente y alcance

El [aviso del organizador](https://hackiathon.dev/aviso-de-la-politica-de-tratamiento-de-datos-personales/) identifica a Viamatica S.A. (Ecuador), remite a la LOPDP ecuatoriana, describe conservación por finalidad y derechos de acceso, rectificación, eliminación, oposición, suspensión, portabilidad y objeción a decisiones automatizadas. Contacto indicado: datoseguro@viamatica.com. Es una lectura del aviso, no certificación legal del proyecto.

Sentria no hereda su consentimiento, finalidades o papel de responsable. La demo usa solo datos ficticios. Una operación con asegurados reales necesitaría definir responsable/encargados, finalidad/base jurídica, ubicación y transferencia de datos, acuerdos con proveedores y derechos aplicables, con asesoría competente en las jurisdicciones involucradas.

## Datos de la preparación

| Dato | Tratamiento actual | Publicación |
|---|---|---|
| Nombres/LinkedIn del equipo | Proporcionados por usuario para atribución | README y material del equipo |
| Expedientes A-D | Sintéticos y versionados | Permitidos en demo/Git |
| Clave Gemini | Variable/SecretStr; no proporcionada en esta sesión | Nunca en Git, UI, prompts o logs |
| Textos enviados a Gemini | Solo al activar modo gemini, contienen evidencia | No enviar reales en esta preparación |
| Resultados | Respuesta HTTP y cache en memoria del proceso | Solo fixtures públicos; sin persistencia de expedientes propios |

La cuota gratuita de Gemini tiene condiciones de tratamiento distintas de servicios pagados; verificar modalidad y [términos de Gemini](https://ai.google.dev/gemini-api/terms). No confundir poseer una API key con tener condiciones de privacidad empresariales. No se promete retención cero.

## Controles implementados

Entradas públicas limitadas a fixtures; custom input deshabilitado por defecto; máximo de bytes y longitud de colecciones; validación de esquema/referencias; escape UI; no herramientas externas arbitrarias; SDK sin reintentos automáticos; error del proveedor seguro. El proceso no guarda prompts ni respuestas crudas en logs propios. El servidor web puede registrar URL/IP según configuración operativa.

## Controles de T01-T07

- Upload: PDF/XLSX permitidos, magic bytes, máximo 10 MiB por archivo/30 páginas PDF/1.000 filas Excel; ajustar tras medir. ZIP expandido XLSX acotado, rechazar macros y fórmulas en celdas críticas. Nombres internos, directorio fuera de static.
- Autorizar por expediente antes de descargar o borrar; impedir IDOR/path traversal. No entregar archivos por rutas del cliente.
- Retención de demo documental: propuesta de borrado 24 h para sesiones sintéticas privadas, con job comprobado. No está implementada aún.
- Borrar originales, extracciones, resultados y referencias de cache juntos. Definir retención separada de backups; no prometer borrado absoluto si hay copias.
- HTTPS, clave en archivo 0600 o secreto del servidor, permisos de volumen, PostgreSQL no público; backups si hay persistencia.
- Cifrado de volumen y control de acceso antes de datos reales. Consentimiento/aviso de Sentria deben ser propios y específicos, no una casilla copiada del evento.
- Evitar datos personales en screenshots, videos, PDFs de entrega, telemetría y prompts de desarrollo.

Las bases permiten difusión promocional de materiales e imagen/voz del evento; no equivalen a cesión de expedientes de terceros. La licencia GPL existente cubre el código conforme a su texto, no los datos personales ni documentos de terceros.
