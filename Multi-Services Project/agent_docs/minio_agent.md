# MinIO Agent

## Descripción General

El `minio_agent` gestiona el almacenamiento de objetos en MinIO, una solución de object storage compatible con S3. El agente interactúa con MinIO a través de un servidor MCP que corre dentro de un contenedor Docker.

**RESTRICCIÓN CRÍTICA DE AISLAMIENTO:**  
El agente MinIO opera en total aislamiento. Su contenedor Docker tiene montado **únicamente** el directorio `DOWNLOADS_DIR` del host como `/Downloads` interno. El agente **solo puede leer o escribir archivos que ya se encuentren en `/Downloads`**. No puede acceder a ninguna otra ruta del host ni del sistema de archivos del orquestador.

---

## Capacidades

- **Listar** buckets y objetos dentro de un bucket.
- **Subir** archivos desde `/Downloads/<archivo>` a un bucket de MinIO.
- **Descargar** objetos de MinIO hacia `/Downloads/<archivo>`.
- **Eliminar** objetos o buckets.
- **Crear** nuevos buckets.
- **Obtener información** de un objeto (tamaño, metadatos, fecha de modificación).
- **Obtener la ruta del host** que está mapeada a `/Downloads` (herramienta `get_host_downloads_dir`), útil para coordinar con otros agentes.

---

## Restricciones

- **Toda ruta de archivo debe usar el prefijo `/Downloads/`**, nunca rutas del host ni del sistema de archivos externo.
- Si el archivo que se necesita subir **no está en `DOWNLOADS_DIR`**, el plan SIEMPRE debe incluir un paso previo del agente `github` para moverlo allí. De lo contrario, el agente fallará.
- El servidor MinIO corre en `localhost:9003` con autenticación por access key / secret key (configurado automáticamente).
- No tiene relación con operaciones de DSpace, GitHub o Bots directamente.
