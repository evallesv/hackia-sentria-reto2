# Checklist de GitHub y entrega

Fuente normativa: bases Panamá §§2-3; filtro adjunto p.1. Inicial y final piden repo, agente funcionando y PDF de herramientas según bases. Video opcional; Notion no es requisito de este PDF.

## Preparado localmente y desplegado

- [x] README, equipo y licencia GPL existente preservada.
- [x] Contratos, datos de prueba sintéticos, motor, UI guiada, pruebas y configuración de CI.
- [x] Gemini detrás de interfaz, CI/CD a Fly.io configurado y plan de tareas.
- [x] Registro y generador PDF de herramientas de preparación.
- [x] Gemini probado con clave/modelo de la cuenta; métricas reales registradas (`gemini-2.5-flash-lite`, 1.6s latencia).
- [x] Build y ejecución local Docker Linux ARM64, usuario no root, A-D correctos.
- [x] Despliegue en la nube (Fly.io ARM64) comprobado desde red externa con HTTPS: https://sentria.fly.dev.
- [x] Cambios publicados en GitHub (`main`); Actions verificadas en remoto (`ci.yml` y `fly-deploy.yml`).
- [x] URL pública HTTPS probada sin sesión, modo real y guía visibles.
- [x] PDF actualizado al trabajo final con ReportLab; equipo y representante completos.
- [x] Borrador de correo de entrega preparado en `docs/delivery/submission.md`.
- [ ] Envío formal de correo realizado por el representante humano (Eduardo Valle).
- [ ] Actividades de difusión en redes / video opcional (si el equipo decide realizarlas).

## Publicar cambios cuando se decida

Remoto ya configurado: https://github.com/evallesv/hackia-sentria-reto2.git. La preparación no hace push ni cambia visibilidad.

```bash
git status --short
make check
git diff --check
git switch -c codex/mvp-foundation
git add README.md AGENTS.md app contracts data docs scripts static templates tests deploy
git add .env.example .gitignore .dockerignore .python-version .github
git add pyproject.toml uv.lock requirements.txt Dockerfile compose.yaml Makefile opencode.json
git diff --cached --stat
git commit -m "Prepare Sentria claims audit foundation and implementation plan"
git push -u origin codex/mvp-foundation
```

Revisar staged diff antes de commit: sin `.env`, expedientes reales, secretos o material ajeno. Abrir PR hacia main con pruebas y estado honesto; no afirmar que todo el MVP está terminado. Si se usa PR, esperar checks y revisión requerida del repositorio antes de merge. Verificar acceso del jurado desde sesión sin autenticación; un enlace privado sin permisos no satisface acceso público.

## Cierre

Completar submission.md y tools-used.json con resultados finales, regenerar PDF y verificar páginas. Registrar fuente/permiso de imágenes, librerías y datos sintéticos. Las bases piden actividades de difusión en redes; el equipo debe coordinar su realización y conservar evidencia. No programarlas ni enviarlas desde esta tarea de preparación.

El requisito de 2-3 miembros está satisfecho por los nombres facilitados. Edad, residencia, experiencia, perfil activo y representante deben confirmarlos los integrantes. No se han investigado sus perfiles ni inferido sus capacidades.
