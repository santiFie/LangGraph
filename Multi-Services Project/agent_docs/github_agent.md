# GitHub Agent

## Descripción General

El `github_agent` es un agente especialista en operaciones de GitHub (repositorios remotos) y en operaciones de sistema de archivos local. Funciona como el "agente de preparación de archivos" en flujos multi-agente: cuando otros agentes necesitan que un archivo esté disponible en `DOWNLOADS_DIR`, es el `github_agent` quien realiza esa tarea.

---

## Capacidades

### Operaciones de Filesystem Local
- **Leer** archivos del sistema de archivos local.
- **Crear** nuevos archivos en el sistema de archivos local.
- **Editar / sobreescribir** archivos existentes.
- **Mover / copiar** archivos entre directorios del host, incluyendo hacia/desde `DOWNLOADS_DIR`.
- **Listar** contenido de directorios.
- **Buscar** archivos por nombre o contenido.

### Operaciones de GitHub Remoto
- **Listar** repositorios y ramas.
- **Leer** contenido de archivos en repositorios remotos.
- **Crear o actualizar** archivos en repositorios remotos (requiere commit message del usuario).
- **Crear** issues, pull requests, etc.

---

## Notas Importantes

- El `github_agent` trabaja en el path raíz `WORKSPACE_PATH` del host.
- El repositorio remoto por defecto es el configurado en `DEFAULT_GITHUB_REPO`.
- **Nunca debe intentar interactuar con MinIO o DSpace directamente.** Solo prepara archivos y los deja listos en `DOWNLOADS_DIR`.
- Cuando se le pide copiar un archivo a `DOWNLOADS_DIR` y lo hace exitosamente, responde con el formato: "File [nombre] has been successfully copied to the shared downloads directory."
- Las operaciones de commit y push **requieren siempre un mensaje de commit provisto por el usuario**. El agente nunca inventa un commit message.
- Cuando se le pide confirmar que un archivo está en `DOWNLOADS_DIR`, usa `list_directory` o `search_files`. **NUNCA lee el contenido del archivo directamente.**
