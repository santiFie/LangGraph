# Playbook: Editar y reimportar metadatos de DSpace

## Resumen

Exporta metadatos de una colección DSpace a CSV, los edita localmente, y los reimporta a DSpace.

## Cuándo usar este playbook

- El usuario quiere modificar metadatos en lote de ítems de DSpace.
- El usuario quiere corregir o actualizar campos de metadatos de múltiples ítems a la vez.

## Flujo

```
Paso 1 (dspace): Exportar la colección a CSV.
                 - Herramienta: export_collection_to_csv(collection_uuid=<uuid>)
                 - Obtener la ruta del CSV en el servidor DSpace.

Paso 2 (filesystem): Copiar el CSV desde el servidor DSpace a DOWNLOADS_DIR del host.
                 - Confirmar que el archivo llegó correctamente con list_directory.

Paso 3 (filesystem): Editar el CSV con las modificaciones de metadatos requeridas.
                 - Leer el archivo, aplicar cambios, guardar.

Paso 4 (filesystem): Mover el CSV editado de vuelta a un path accesible por DSpace (si aplica).
                 - Este paso depende de la configuración del servidor DSpace.

Paso 5 (dspace): Importar el CSV actualizado.
                 - Herramienta: import_metadata_from_csv con la ruta del CSV modificado.
```

## Notas

- Si el UUID de la colección no se conoce, agregar un sub-paso de búsqueda antes del Paso 1.
- Los UUIDs de los ítems en el CSV son cruciales; no deben modificarse.
- El proceso de importación también es asíncrono en DSpace.
