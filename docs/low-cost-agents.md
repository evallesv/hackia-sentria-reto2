# Implementar con OpenCode Go y agentes de menor coste

## Preparar el editor

Usar OpenCode Go para desarrollo; Gemini para la aplicación desplegada. Las claves tienen fines distintos y nunca se copian al repositorio ni a prompts. `opencode.json` carga arquitectura e ingeniería; `AGENTS.md` fija invariantes.

En OpenCode ejecutar `/connect`, seleccionar OpenCode Go y autenticar localmente. Ejecutar `/models` y seleccionar un modelo realmente disponible. La documentación publica IDs con prefijo `opencode-go/`; la lista cambia. Consultar [Go](https://opencode.ai/v2/docs/console/go) y [selección de modelos](https://opencode.ai/v2/docs/models), verificadas el 27/09/2026. No se fijan precios, cuotas ni disponibilidad de tu cuenta.

Ejemplos que figuran en la lista oficial consultada: MiMo-V2.5, DeepSeek V4 Flash, MiniMax M2.7 y Kimi K2.7 Code. **No se han benchmarkeado para este proyecto.** Elegir primero uno económico para T08/T06; promover a uno con mejor resultado local para T02/T05 si falla la prueba. Los endpoints de Go varían según modelo; no apuntar el SDK Gemini a Go ni asumir una interfaz universal.

## Estrategia de coste

1. Un agente implementador por tarea; entregarle solo AGENTS, arquitectura, contrato y su ficha. No repetir adjuntos ni todo el historial.
2. Ejecutar primero el comando de baseline indicado. Si ya pasa, identificar qué comportamiento falta antes de editar.
3. Obtener una entrega pequeña (idealmente 1-4 archivos de lógica más tests), revisar y continuar. Dividir T02 por parser PDF, parser Excel y mapeo IA si crece demasiado.
4. Dos intentos sobre un mismo fallo son suficientes para registrar diagnóstico y escalar a integrador. Enviar error, caso mínimo y diff, no reiniciar el proyecto.
5. Revisión independiente solo en contratos, cálculos, privacidad y orquestación; no gastar otro modelo revisando textos triviales.
6. Usar fixtures para UI/motor; reservar llamadas Gemini para evaluación explícita y extracción. El CI normal no consume tokens.
7. Registrar modelo, tarea, tiempo, tokens/coste si la plataforma los muestra. No inventarlos si no están disponibles.

La eficiencia se mide por **tarea aceptada y sin regresiones**, no solo por precio de token. No activar concurrencia sin separar archivos/ramas y dueño del contrato.

## Prompt de encargo

```text
Implementa únicamente docs/tasks/TXX-nombre.md en Sentria.
Lee AGENTS.md, docs/architecture.md y docs/contracts.md.
Estado base: <commit>; contexto adicional: <archivos relevantes>.
Verifica la situación actual antes de cambiarla. Conserva comportamiento que ya pase.
Respeta archivos permitidos, invariantes y condiciones de aceptación de la ficha.
No inventes endpoints, evidencia, estado de pruebas, modelos disponibles ni despliegues.
No leas credenciales ni envíes documentos reales. Usa fixtures sintéticos.
Si hace falta cambiar contrato, explica el cambio mínimo al integrador.
Entrega diff, pruebas relevantes, resultado de make check, límites y siguiente dependencia.
Presupuesto de trabajo: una tarea y dos intentos por fallo; si no avanza, deja diagnóstico reproducible.
```

En la terminal, después de elegir el ID desde `/models`:

```bash
opencode run --model '<ID_SELECCIONADO>' 'Implementa docs/tasks/T04-engine.md siguiendo AGENTS.md. Ejecuta make check y reporta el diff y los límites.'
```

No ejecutar ese ejemplo con el marcador literal. Para varios desarrolladores, crear ramas `codex/t01-intake`, `codex/t04-engine`, etc. Trabajar en clones/worktrees separados; integrar uno a la vez. El equipo decide quién opera cada sesión, sin compartir claves o asumir derechos de uso entre miembros.

## Contrato de respuesta del agente

```text
Tarea: TXX
Cambios: <archivos y comportamiento>
Contrato: <sin cambios o revisión acordada>
Validación: <comandos + resultados reales>
IA: <mock / SDK simulado / llamada real>
Riesgos: <fallos o funciones pendientes>
Consumo: <medido o no disponible>
Siguiente: <tarea desbloqueada>
```

Rechazar entregas con «listo» sin validación, catches que aprueban por defecto, imports del LLM en motor, importes float, citas inventadas, cambios de licencia o dependencias sin justificar. La revisión debe encontrar defectos concretos; no reescribir por preferencias de estilo.
