# DSpace Agent

## Descripción General

El `dspace_agent` administra el repositorio institucional SEDICI (basado en DSpace 7+). Se comunica con el repositorio a través de un servidor MCP (Model Context Protocol) que expone la API REST de DSpace.

Todos los objetos en DSpace se identifican mediante UUIDs. Las operaciones de administración requieren autenticación, que se gestiona automáticamente.

---

## Capacidades

- **Listar y buscar** comunidades, colecciones e ítems.
- **Crear y actualizar** comunidades, colecciones e ítems con sus metadatos.
- **Exportar metadatos** de una colección completa a un archivo CSV (herramienta: `export_collection_to_csv`).
  - El resultado es un archivo CSV generado en el **servidor DSpace** (no en el host del orquestador).
  - El proceso es asíncrono y puede tardar varios segundos.
  - La herramienta retorna la ruta del archivo CSV en el servidor DSpace y el estado del script.
- **Importar metadatos** a partir de un archivo CSV modificado (herramienta: `import_metadata_from_csv`).
  - El CSV debe estar disponible en el servidor DSpace o en un path accesible por él.
- **Gestionar bitstreams** (archivos adjuntos a ítems).
- **Buscar colecciones o ítems** por nombre o UUID (herramientas: `list_collections`, `search_collections`, `list_items_in_collection`, `search_items`).

---

## Restricciones y Notas

- Los UUIDs son la forma canónica de identificar cualquier objeto en DSpace (comunidades, colecciones, ítems, bitstreams).
- Si el usuario proporciona un nombre en lugar de un UUID, siempre se debe hacer una búsqueda previa.
- El agente opera con permisos de administrador sobre SEDICI.
- El archivo CSV exportado reside en el sistema de archivos **interno del servidor DSpace**, no en el host del orquestador. Para que otros agentes (como `minio`) puedan accederlo, es necesario un paso intermedio con el agente `github`.
- No puede acceder directamente a MinIO ni al filesystem del host del orquestador.
