## 🛠️ Procedimiento Para hacer un Update de un *Workflow* Item
## Cuándo usar este playbook
- El agente revisor detecta un error menor en el título, autor o abstract de un ítem que está en la cola de moderación.
- El usuario solicita explícitamente corregir un dato sin cancelar el proceso de publicación.

## Consideración Crítica (Efecto Secundario)
Al usar la herramienta `update_workflow_item`, el ítem perderá temporalmente su ID de flujo de trabajo original (`workflow_item_id`) y se generará uno **NUEVO** al finalizar el proceso. 

Si el agente tenía una tarea reclamada (`ClaimedTask`) sobre este ítem, esa tarea quedará inválida y el ítem volverá al pool general de revisión en su paso correspondiente.

## Flujo recomendado para el agente
1. Identificar el `workflow_item_id` del ítem erróneo.
2. Invocar directamente a `update_workflow_item` con los campos corregidos.
3. Informar al usuario el NUEVO ID del workflow item retornado por la herramienta.

## Edición Múltiple de Metadatos en un solo paso

Es posible (y altamente recomendado por eficiencia) actualizar múltiples campos de metadatos en una única llamada a la herramienta `update_workflow_item`. Esto evita ciclos repetitivos de sacar y meter el ítem al flujo de trabajo.

La herramienta acepta un esquema fijo con los campos `abstract`, `authors` (lista) y `keywords` (lista). Internamente convierte estos campos a sus equivalentes Dublin Core (`dc.description.abstract`, `dc.contributor.author`, `dc.subject`) y detecta automáticamente la sección de formulario correcta donde debe aplicarse cada campo, sin necesidad de especificar `section`.

### Ejemplo de Prompt / Instrucción para el LLM

#### Estructura de la llamada a la Tool:

```python
update_workflow_item(
    workflow_item_id=456,
    metadata={
        "abstract": "Este trabajo presenta la implementación de un orquestador de servicios usando LangGraph.",
        "authors": ["Fierro, Santiago"],
        "keywords": ["orquestador", "langgraph", "servicios"]
    }
)