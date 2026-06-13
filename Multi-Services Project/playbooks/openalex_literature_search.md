# Playbook: Búsqueda de literatura científica en OpenAlex

## Resumen

Busca literatura científica estructurada a través de OpenAlex según criterios específicos (palabras clave, autores, instituciones) y lista los resultados.

## Cuándo usar este playbook

- El usuario requiere un listado de artículos académicos sobre un tema en particular.
- Se necesita conocer el impacto (citas, índice h) de un autor o institución específica.
- El usuario quiere obtener los DOIs o URLs de publicaciones académicas para revisión.

## Flujo

```
Paso 1 (openalex): [BÚSQUEDA CON RESOLUCIÓN DE ENTIDAD]
                   Si la búsqueda involucra un autor, institución, concepto o fuente identificado por nombre,
                   el agente DEBE primero llamar a la tool de búsqueda/autocompletado para obtener el ID
                   numérico exacto (ej: "I123456789"), y luego usar ese ID para filtrar los works en la
                   misma ejecución. Ambas acciones ocurren dentro de este único paso.
                   NUNCA asumir que el nombre del usuario es un ID válido de OpenAlex.
                   - Si el usuario busca un tema general (sin entidad nombrada), refinar con palabras clave.
                   - Si busca un artículo específico, usar título o DOI directamente.
                   - Aplicar los parámetros de paginación adecuados (ej: per_page, sort) en la misma llamada.
                   - Usar los parámetros cuando se necesiten los resultados ordenados (sort por fecha, titulo, etc.). NO HACER DOS PASOS PARA ORDENAR UN RESULTADO.
```

> ⚠️ **Importante:** NO incluir un paso de "presentar", "recopilar" o "formatear" los resultados.
> Esa responsabilidad es exclusiva del `final_answer_node`, que se ejecuta automáticamente al finalizar el plan.


## Parámetros clave para el agente openalex

- `query`: Términos de búsqueda (palabras clave, nombres de autores, etc.).
- `entity_type`: Tipo de entidad a buscar (works, authors, institutions, concepts, sources).

## Notas

- El agente **no debe sintetizar** la información de los artículos; su objetivo es **solo listar** los metadatos usando el formato requerido en las reglas de operación.
- Si no se encuentran resultados, el agente debe informar al usuario explícitamente en lugar de alucinar u ofrecer literatura inexistente.
