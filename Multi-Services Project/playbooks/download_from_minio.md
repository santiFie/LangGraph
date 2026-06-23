# Playbook: Descargar objeto de MinIO al filesystem local

## Resumen

Descarga un objeto desde un bucket de MinIO al directorio compartido `DOWNLOADS_DIR` del host.

## Cuándo usar este playbook

- El usuario quiere obtener un archivo almacenado en MinIO.
- Se necesita recuperar un objeto de MinIO para procesarlo localmente o con otro agente.

## Flujo

```
Paso 1 (minio):  Descargar el objeto del bucket.
                 - El archivo quedará en /Downloads/<nombre> dentro del contenedor,
                   que corresponde a DOWNLOADS_DIR del host.
                 - Si no se conoce el nombre exacto del objeto, primero listar con list_objects.

Paso 2 (filesystem_agent): [Opcional] Mover o copiar el archivo desde DOWNLOADS_DIR
                 a otra ubicación del host si es necesario para procesamiento posterior.
```

## Parámetros clave para el agente minio

- `bucket_name`: Nombre del bucket de origen.
- `object_name`: Nombre del objeto a descargar.
- `file_path`: Destino dentro del contenedor, siempre `/Downloads/<nombre>`.

## Notas

- Después de la descarga, el archivo estará en `DOWNLOADS_DIR` del host.
- Si se necesita procesar el archivo (editar, leer, mover), el agente `filesystem` puede hacerlo en el Paso 2.
