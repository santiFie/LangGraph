# Playbook: Exportar colección de DSpace y subir a MinIO

## Resumen

Exporta los metadatos de una colección DSpace a CSV y lo sube al almacenamiento MinIO.

## Cuándo usar este playbook

- El usuario quiere exportar una colección de DSpace a MinIO.
- El usuario quiere hacer un backup de metadatos de SEDICI en MinIO.

## Consideración crítica

El CSV exportado por DSpace reside en el filesystem **interno del servidor DSpace**, que es inaccesible directamente desde el host del orquestador. El agente `github` actúa como puente: copia el archivo desde el servidor DSpace al `DOWNLOADS_DIR` del host, donde MinIO puede leerlo.

## Flujo

```
Paso 1 (dspace): Exportar la colección a CSV.
                 - Si no se conoce el UUID de la colección, primero buscarla con list_collections o search_collections.
                 - Herramienta: export_collection_to_csv(collection_uuid=<uuid>)
                 - El resultado incluye la ruta del CSV en el servidor DSpace.

Paso 2 (github): Copiar el CSV desde la ruta del servidor DSpace a DOWNLOADS_DIR del host.
                 - Usar copy_file o move_file con la ruta retornada en el paso anterior.
                 - Confirmar con list_directory o search_files. NUNCA leer el contenido.

Paso 3 (minio):  Subir el CSV a MinIO.
                 - file_path: /Downloads/<nombre>.csv
                 - bucket_name: el bucket destino (ej: 'dspace-exports')
                 - object_name: nombre deseado del objeto en MinIO
```

## Notas

- El proceso de exportación en DSpace es asíncrono y puede tardar varios segundos.
- Si el UUID de la colección no se conoce de antemano, el Paso 1 debe estar dividido en dos sub-pasos: buscar primero, exportar después (o el agente dspace lo resuelve internamente).
- Si el bucket destino no existe en MinIO, agregar un paso previo al Paso 3 para crearlo.
