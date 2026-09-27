# Checklist de GitHub y entrega

Fuente normativa: bases Panamá §§2-3; filtro adjunto p.1. Inicial y final piden repo, agente funcionando y PDF de herramientas según bases. Video opcional; Notion no es requisito de este PDF.

## Preparado localmente

- [x] README, equipo y licencia GPL existente preservada.
- [x] Contratos, fixtures sintéticos, motor, UI guiada, pruebas y configuración de CI.
- [x] Gemini detrás de interfaz, configuración Oracle ARM64 y plan de tareas.
- [x] Registro y generador PDF de herramientas de preparación.
- [ ] MVP documental T01-T06 y evaluación reservada T07 terminados.
- [ ] Gemini probado con clave/modelo de la cuenta; métricas reales registradas.
- [x] Build y ejecución local Docker Linux ARM64, usuario no root, A-D correctos.
- [ ] Despliegue Oracle comprobado desde red externa.
- [ ] Cambios publicados en GitHub; Actions verificadas en remoto.
- [ ] URL pública HTTPS probada sin sesión, modo real y guía visibles.
- [ ] PDF actualizado al trabajo final; equipo/representante completos.
- [ ] Fecha/extensión confirmada (inicial previsto 23/09, hoy 27/09).
- [ ] Envío realizado por representante con autorización explícita.

## Publicar cambios cuando se decida

Remoto ya configurado: https://github.com/evallesv/hackia-sentria-reto2.git. La preparación no hace push ni cambia visibilidad.

```bash
git status --short
make check
git diff --check
git switch -c codex/mvp-foundation
git add README.md AGENTS.md app contracts data docs scripts static templates tests deploy
git add .env.example .gitignore .dockerignore .python-version .github
git add pyproject.toml uv.lock requirements.txt Dockerfile compose.yaml compose.oracle.yaml Makefile opencode.json
git diff --cached --stat
git commit -m "Prepare Sentria claims audit foundation and implementation plan"
git push -u origin codex/mvp-foundation
```

Revisar staged diff antes de commit: sin `.env`, expedientes reales, secretos o material ajeno. Abrir PR hacia main con pruebas y estado honesto; no afirmar que todo el MVP está terminado. Si se usa PR, esperar checks y revisión requerida del repositorio antes de merge. Verificar acceso del jurado desde sesión sin autenticación; un enlace privado sin permisos no satisface acceso público.

## Cierre

Completar submission.md y tools-used.json con resultados finales, regenerar PDF y verificar páginas. Registrar fuente/permiso de imágenes, librerías y datos sintéticos. Las bases piden actividades de difusión en redes; el equipo debe coordinar su realización y conservar evidencia. No programarlas ni enviarlas desde esta tarea de preparación.

El requisito de 2-3 miembros está satisfecho por los nombres facilitados. Edad, residencia, experiencia, perfil activo y representante deben confirmarlos los integrantes. No se han investigado sus perfiles ni inferido sus capacidades.
