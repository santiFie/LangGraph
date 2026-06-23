# Playbook: Subir un archivo local a MinIO

## Resumen

Sube un archivo que ya existe en el filesystem del host al almacenamiento de objetos MinIO.

## Cuándo usar este playbook

- El usuario quiere subir/guardar un archivo en MinIO.
- El archivo de origen está en el sistema de archivos del host (no en DSpace).

## Prerequisito crítico

El agente MinIO **solo puede leer archivos que estén dentro de `/Downloads`** (mapeado desde `DOWNLOADS_DIR` del host). Si el archivo no está ahí, el plan debe incluir un paso del agente `filesystem` para moverlo primero.

## Flujo

```
Paso 1 (filesystem): Copiar o mover el archivo de origen a DOWNLOADS_DIR del host.
                 Confirmar que el archivo está allí usando list_directory o search_files.
                 NUNCA leer el contenido del archivo.

Paso 2 (minio):  Subir el archivo usando file_path=/Downloads/<nombre_del_archivo>,
                 especificando bucket_name y opcionalmente object_name.
```

## Parámetros clave para el agente minio

- `file_path`: Siempre `/Downloads/<nombre_del_archivo>` (ruta interna del contenedor).
- `bucket_name`: Nombre del bucket de MinIO destino.
- `object_name`: Nombre del objeto en MinIO (si no se especifica, usa el nombre del archivo).

## Notas

- El agente `filesystem` responde con "File [nombre] has been successfully copied to the shared downloads directory." cuando termina exitosamente.
- Si el bucket destino no existe, agregar un paso previo con el agente `minio` para crearlo.