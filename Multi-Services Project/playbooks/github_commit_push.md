# Playbook: Commit y Push a GitHub

## Resumen

Crea o edita archivos en el sistema de archivos local y los sube (commit + push) a un repositorio GitHub remoto.

## Cuándo usar este playbook

- El usuario quiere guardar cambios en un repositorio GitHub.
- El usuario quiere crear un archivo y commitearlo.
- El usuario quiere actualizar un archivo existente en GitHub.

## Prerequisito CRÍTICO: Mensaje de commit

Las operaciones de commit y push **siempre requieren un mensaje de commit provisto por el usuario**. El agente `github` **nunca inventa** un commit message. Si el usuario no proporcionó un mensaje de commit en su solicitud original, el sistema debe interrumpirse para solicitárselo antes de ejecutar el push.

## Flujo

```
Paso 1 (github): Preparar los cambios.
                 - Crear o editar el/los archivo(s) afectados en el filesystem local.
                 - Confirmar que los cambios están listos.

Paso 2 (github): Ejecutar commit y push.
                 - Usar el mensaje de commit provisto por el usuario.
                 - Repositorio destino: DEFAULT_GITHUB_REPO (o el especificado por el usuario).
                 - Rama: la indicada por el usuario, o la rama por defecto.
```

## Notas

- El agente trabaja en el path raíz `WORKSPACE_PATH` del host.
- Si el usuario no especificó un mensaje de commit, se debe pedir antes de ejecutar el Paso 2.
- Para commits que involucren múltiples archivos, el Paso 1 debe incluir la preparación de todos antes de hacer el push.
