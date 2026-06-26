# Playbook: Exportar colección de DSpace y subir a MinIO

## Resumen

Exporta los metadatos de una colección DSpace a CSV y lo sube al almacenamiento MinIO.

## Cuándo usar este playbook

- El usuario quiere exportar una colección de DSpace a MinIO.
- El usuario quiere hacer un backup de metadatos de SEDICI en MinIO.

## Arquitectura de rutas: bind mount del DSpace MCP

El contenedor del DSpace MCP tiene el siguiente bind mount definido en `docker-compose.yml`:

```
Host:      {WORKSPACE_PATH}/MCPs/Dspace MCP/data/
               ↕  (bind mount)
Contenedor: /app/data/
```

Cuando `export_collection_csv` retorna `csv_path: /app/data/<archivo>.csv`, el archivo **ya existe en el host** en:

```
{WORKSPACE_PATH}/MCPs/Dspace MCP/data/<archivo>.csv
```

El agente `filesystem` tiene acceso total a `{WORKSPACE_PATH}/*` con su MCP de filesystem, por lo que puede operar directamente sobre esa ruta. **No es necesario copiar desde un servidor remoto.**

## Flujo

```
Paso 1 (sedici): Exportar la colección a CSV.
                 - Si no se conoce el UUID, buscarlo primero con list_collections o search_collections.
                 - Herramienta: export_collection_csv(collection_uuid=<uuid>)
                 - El tool retorna csv_path=/app/data/<archivo>.csv (ruta interna del contenedor).
                 - Comunicar al siguiente agente que el path en el HOST es:
                   {WORKSPACE_PATH}/MCPs/Dspace MCP/data/<archivo>.csv

Paso 2 (sedici): Mover o copiar el CSV al DOWNLOADS_DIR del host.
                 - Path de origen: {WORKSPACE_PATH}/MCPs/Dspace MCP/data/<archivo>.csv
                 - Path de destino: {DOWNLOADS_DIR}/<archivo>.csv
                 - Usar move_file o copy_file del MCP de filesystem.
                 - Confirmar con list_directory o search_files. NUNCA leer el contenido del CSV.

Paso 3 (minio):  Subir el CSV a MinIO.
                 - file_path: {DOWNLOADS_DIR}/<archivo>.csv
                 - bucket_name: el bucket destino (ej: 'dspace-exports')
                 - object_name: nombre deseado del objeto en MinIO
```

## Notas

- El proceso de exportación en DSpace es asíncrono y puede tardar varios segundos.
- Si el UUID de la colección no se conoce de antemano, el Paso 1 debe dividirse: buscar primero, exportar después.
- Si el bucket destino no existe en MinIO, agregar un paso previo al Paso 3 para crearlo.
- El nombre del archivo generado sigue el patrón `collection_<uuid>.csv`.

