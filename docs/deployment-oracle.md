# Despliegue en VPS Oracle ARM64

Runbook preparado; no se ha accedido al VPS. Se necesita SO, IP/SSH, dominio, recursos disponibles y permisos operativos. No asumir que tener claves Gemini aprovisiona servidores: Gemini es proveedor de inferencia; Oracle hospeda FastAPI.

## Comprobar infraestructura

En el VPS ejecutar `uname -m` (esperado aarch64), `docker version`, `docker compose version`, `free -h` y `df -h`. Objetivo inicial: 2 vCPU/2 GiB libres y disco para imagen/logs; es una estimación para esta demo, no benchmark. Instalar Docker según la distribución real y verificar soporte ARM64 de cada imagen.

Crear DNS A de un subdominio hacia la IP pública. Añadir AAAA solo si IPv6 funciona. En NSG/security list de Oracle **y** firewall del SO: permitir TCP 80/443; UDP 443 opcional para HTTP/3; SSH solo desde IP administrativa. No abrir 8000 o PostgreSQL a internet. No borrar reglas existentes del VPS.

Fuentes: [Oracle Arm Compute](https://docs.oracle.com/en-us/iaas/Content/Compute/References/arm.htm), [FastAPI en Docker](https://fastapi.tiangolo.com/deployment/docker/), [Caddy HTTPS](https://caddyserver.com/docs/automatic-https).

### Gestión local con OCI CLI (opcional)

Si se dispone de `oci` instalado localmente (`brew install oci-cli`):
```bash
oci setup config                        # configurar tenancy, user, región y clave API
oci compute instance list -c <compartment_ocid> --output table
```
Permite verificar la forma de computación (`VM.Standard.A1.Flex` ARM64) y las Security Lists antes de acceder por SSH.

## Preparar release

Tras publicar el commit deseado, clonar el repositorio en una carpeta nueva del VPS o actualizar una copia dedicada sin pisar otros servicios. Usar commit SHA/tag concreto y registrar `git rev-parse HEAD`.

```bash
git clone https://github.com/evallesv/hackia-sentria-reto2.git
cd hackia-sentria-reto2
cp .env.example .env
chmod 600 .env
```

Editar `.env` con editor local. Clave nunca por chat, historial de comandos o commits:

```dotenv
AI_MODE=gemini
GEMINI_API_KEY=<secreto_local>
GEMINI_MODEL=<modelo_verificado_en_tu_cuenta>
DEMO_DOMAIN=<subdominio_real>
ACME_EMAIL=<correo_del_operador>
```

Los marcadores deben reemplazarse; no vienen preconfigurados. Validar sin volcar valores secretos:

```bash
docker compose --env-file .env -f compose.oracle.yaml config --quiet
docker compose --env-file .env -f compose.oracle.yaml build
docker compose --env-file .env -f compose.oracle.yaml up -d
docker compose -f compose.oracle.yaml ps
```

La imagen se construye ARM64 nativa con requirements y hashes. FastAPI corre como usuario no root y filesystem read-only. Caddy expone HTTPS y guarda certificados en volúmenes. FastAPI no publica puerto directo. No arrancar un segundo proxy en 80/443 si el VPS ya los utiliza: integrar el dominio en el proxy existente.

No usar `docker compose config` sin `--quiet` al compartir salida: puede mostrar secretos interpolados. Tampoco compartir `docker inspect` completo.

## Verificación pública

Desde otro equipo abrir `https://<dominio>/healthz` y la portada. Ejecutar A-D; comprobar que modo Gemini produce modelo/tokens y que no hay SEMANTIC_UNAVAILABLE. Descargar reporte C y abrir evidencia. Confirmar certificado válido, que /api/audits rechaza entrada propia y que no se exponen datos ajenos. Probar acceso desde móvil sin sesión de desarrollador.

Guardar commit, hora, URL y resultados en verification.md. Logs de Caddy no están activados por defecto en este archivo; no añadir bodies/headers de autorización al logging. Ajustar rotación de logs Docker en el host. Configurar presupuesto del proyecto Gemini además del límite por proceso.

## Actualización y rollback

Anotar SHA anterior e imagen anterior antes del cambio. Construir una imagen identificada por commit para cada release. Tras nueva release repetir health y caso B. Si falla, volver al commit/imagen previo y recrear el servicio sin eliminar volúmenes. **No usar `down -v`** como rollback. Cuando T03 agregue PostgreSQL: backup y restauración probada antes de migrar; no asumir downgrade seguro.

La demo stateless pierde cache al reiniciar (también el contador de llamadas). Es aceptable para los cuatro fixtures. El flujo documental público necesita persistencia, auth, cuotas y borrado de T01-T07. El starter no se anuncia como servicio de producción.
