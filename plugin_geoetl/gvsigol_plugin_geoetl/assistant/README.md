# Asistente del editor ETL

Chat integrado en el editor ETL de gvSIG Online que construye flujos a partir de una descripción en lenguaje natural. El usuario dice qué datos tiene y qué resultado quiere; el asistente consulta las conexiones y tablas a las que el usuario tiene acceso, dibuja el flujo en el canvas y el usuario lo revisa y lo guarda con el botón de siempre.

El asistente **nunca guarda ni ejecuta** nada: solo modifica el canvas abierto, y cada cambio se puede deshacer.

## Índice

1. [Qué hace](#qué-hace)
2. [Activación](#activación)
3. [Uso](#uso)
4. [Arquitectura](#arquitectura)
5. [Contrato del endpoint](#contrato-del-endpoint)
6. [El catálogo de nodos (YAML)](#el-catálogo-de-nodos-yaml)
7. [Validación de propuestas](#validación-de-propuestas)
8. [Frontend](#frontend)
9. [Seguridad y permisos](#seguridad-y-permisos)
10. [Cómo extenderlo](#cómo-extenderlo)
11. [Traducciones](#traducciones)
12. [Tests](#tests)
13. [Compatibilidad con workspaces existentes](#compatibilidad-con-workspaces-existentes)
14. [Problemas frecuentes](#problemas-frecuentes)

## Qué hace

- **Crear un flujo desde cero** con el canvas vacío: "Carga un CSV en una tabla nueva de PostGIS".
- **Modificar el flujo abierto**: añadir un nodo después del seleccionado, completar lo que falta hasta una salida, cambiar parámetros, quitar nodos o conexiones.
- **Explicar o revisar** el flujo del canvas: qué hace paso a paso, qué parámetros faltan.
- **Consultar las fuentes reales**: lista las conexiones ETL del usuario, sus esquemas, tablas y columnas, y deduce los nodos a partir de la diferencia entre entradas y destino.
- **Preguntar** cuando una regla de negocio no se puede deducir (campo de cruce ambiguo, valor de un filtro…) y **declarar las suposiciones** que sí toma (`n3: cruce por cod_mun, único campo común`).

Responde en el idioma de la interfaz (español por defecto) o en el que le escriba el usuario.

## Activación

Está **apagado por defecto**. Se activa solo si se cumplen todas estas condiciones (`access.assistant_feature_enabled`):

| Condición | Dónde |
|---|---|
| `ETL_ASSISTANT_ENABLED=True` | Variable de entorno del backend, leída en `gvsigol_plugin_geoetl/settings.py` |
| `gvsigol_plugin_geocopilot` instalado | `INSTALLED_APPS` |
| Proveedor de IA de GeoCopilot listo | `DEFAULT_LLM_PROVIDER` es `openai` o `azure_openai`, el proveedor está habilitado (`ENABLE_OPENAI` / `ENABLE_AZURE_OPENAI`) y tiene una clave real (no vacía ni el placeholder). Azure necesita además el endpoint |

Además, el usuario tiene que ser **staff o superusuario**.

El asistente reutiliza las claves y la fábrica de modelos de GeoCopilot (`gvsigol_plugin_geocopilot.services.llm_factory.build_llm`); no hay claves propias.

Variables opcionales:

| Variable | Valor por defecto | Uso |
|---|---|---|
| `GEOETL_LLM_MODEL` | vacío | Modelo concreto para el asistente. Vacío usa el modelo por defecto de GeoCopilot |
| `AGENT_MAX_ITERATIONS` (de `LANGCHAIN_SETTINGS` de GeoCopilot) | 15 | Máximo de llamadas a herramientas por turno |

Ejemplo en docker (`docker-compose.override.yml`, servicio del backend):

```yaml
environment:
  - ETL_ASSISTANT_ENABLED=True
  # - GEOETL_LLM_MODEL=gpt-4.1
```

Tras cambiarlo: `docker restart gvsigol-back` y recarga del navegador con Ctrl+F5.

Si la comprobación falla por cualquier motivo (por ejemplo, un error al importar la configuración de GeoCopilot), se registra en el log y el editor se abre sin asistente.

## Uso

1. Abrir un workspace (nuevo o existente) en el editor ETL. Aparece el botón **Asistente** junto a "Workspaces".
2. El panel lateral muestra sugerencias según el estado del canvas:
   - **Canvas vacío**: CSV a PostGIS, cruzar dos tablas, geocodificar direcciones, reproyectar una capa.
   - **Canvas con nodos**: explicar el flujo, revisarlo, añadir después del nodo seleccionado (o completar el flujo si no hay selección), guardar en PostGIS.
3. Escribir la petición (Enter envía, Mayús+Enter salta de línea).
4. El asistente responde con:
   - un texto,
   - un **resumen** de los cambios (`Añado Filter (n4) entre n2 y n3.`),
   - las **suposiciones** que ha tomado,
   - **avisos** (parámetros quitados, conexiones no disponibles, SQL que hay que revisar…).
5. Aplicación de los cambios:
   - Cambios que solo añaden o modifican: se dibujan directamente y aparece el botón **Deshacer**.
   - Cambios destructivos (sustituir un canvas con nodos, borrar nodos o conexiones): aparecen **Aplicar** y **Descartar**.
6. Revisar los nodos (engranaje de cada uno), completar lo que falte y **guardar** con el botón habitual.

Detalles de la interfaz:

- Los alias `n1`, `n2`… del texto resaltan el nodo al pasar el ratón y lo centran al hacer clic.
- Seleccionar un nodo en el canvas lo pasa como contexto ("después de este").
- El panel se redimensiona arrastrando el borde izquierdo (320–600 px) y recuerda ancho y estado abierto (`localStorage`).
- La conversación se guarda por workspace en `sessionStorage` (`etl-assistant-chat:<id>`); el botón de papelera la borra. Se envían como historial los últimos 16 mensajes.
- Escape cierra el panel (salvo que haya un modal abierto).

## Arquitectura

```mermaid
flowchart LR
    subgraph navegador [Navegador]
        panel["Assistant.js (panel)"]
        canvas["Canvas draw2d"]
        draw["DrawNodes.js"]
    end
    subgraph backend [Django]
        view["views.etl_assistant"]
        agent["agent.run_assistant"]
        tools["tools.py"]
        graph["graph.validate_proposal"]
        catalog["catalog.py + nodes/*.yaml"]
    end
    llm["LLM de GeoCopilot"]
    db["Conexiones ETL del usuario"]

    panel -->|"POST JSON"| view
    view --> agent
    agent <--> llm
    agent --> tools
    tools --> db
    tools --> graph
    graph --> catalog
    agent -->|"propuesta validada"| panel
    panel --> draw
    draw --> canvas
```

Flujo de una petición:

1. `Assistant.js` resume el canvas (nodos con alias `n1…`, parámetros, esquema, aristas y nodo seleccionado) y lo envía con el mensaje y el historial.
2. `views.etl_assistant` comprueba activación, usuario y permisos sobre el workspace (edición completa o restringida).
3. `agent.run_assistant` monta un agente LangChain (`create_tool_calling_agent` + `AgentExecutor`) con el prompt de sistema, el historial y las herramientas.
4. El LLM consulta fichas, conexiones y tablas, y termina llamando a `propose_workspace`.
5. `graph.validate_proposal` limpia la propuesta contra el catálogo y las conexiones del usuario; si queda algo válido lo guarda como resultado del turno.
6. El panel recibe la propuesta y la dibuja con `drawNodes` dentro de una transacción del CommandStack de draw2d (una sola entrada de deshacer).

### Ficheros

Backend (`gvsigol_plugin_geoetl/assistant/`):

| Fichero | Responsabilidad |
|---|---|
| `views.py` | Endpoint `POST /etl/etl_assistant/`. Validación de la petición y permisos. Importa el agente de forma perezosa |
| `access.py` | Reglas puras de activación y permisos (`assistant_feature_enabled`, `user_may_use`, `workspace_edit_mode`, `provider_is_ready`) |
| `agent.py` | Construye el LLM, el prompt y el `AgentExecutor`; recorta historial y canvas; traduce errores del proveedor a mensajes legibles |
| `prompt.py` | Prompt de sistema: reglas de trabajo, idioma e índice del catálogo |
| `tools.py` | Herramientas que puede llamar el modelo |
| `graph.py` | Validación, maquetación (x, y) y resumen de las propuestas |
| `catalog.py` | Carga de las fichas YAML e índice para el prompt |
| `nodes/*.yaml` | Una ficha por tipo de nodo |
| `shapes.py` | Lee `TableShape.js` y la paleta de `etl.html` para generar fichas |
| `scaffold.py` | Genera borradores YAML (lo usa el comando de manage.py) |

Fuera de la carpeta:

| Fichero | Cambio |
|---|---|
| `settings.py` | `ETL_ASSISTANT_ENABLED`, `GEOETL_LLM_MODEL` |
| `urls.py` | Ruta `etl/etl_assistant/` |
| `views.py` (plugin) | `_assistant_enabled(request)` pasa `etl_assistant_enabled` a la plantilla |
| `templates/etl.html` | Botón, panel, CSS y scripts, todo dentro de `{% if etl_assistant_enabled %}` |
| `static/js/Assistant.js` | Panel de chat |
| `static/js/DrawNodes.js` | Dibuja nodos y conexiones de una propuesta en el canvas |
| `static/js/SchemaCanvas.js` | `window.etlApp = app;` para que el panel acceda a la vista |
| `static/css/etl_assistant.css` | Estilos del panel (variables `--pl-*` del editor) |
| `static/js/lib/marked.min.js`, `purify.min.js` | Markdown de las respuestas, saneado con DOMPurify |
| `management/commands/etl_assistant_scaffold.py` | Comando para generar fichas |
| `locale/es/LC_MESSAGES/*.po/.mo` | Traducciones al español |

## Contrato del endpoint

`POST /gvsigonline/etl/etl_assistant/` con `Content-Type: application/json` y cabecera `X-CSRFToken`. Requiere sesión iniciada.

Petición:

```json
{
  "message": "Añade un filtro después de este nodo",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "canvas": {
    "nodes": [
      {"alias": "n1", "id": "<uuid draw2d>", "type": "input_Postgis", "label": "PgSQL/PostGIS",
       "parameters": {"db": "mi_conexion", "schema-name": "public", "tablename": "municipios"},
       "schema": ["cod_mun", "nombre", "geom"]}
    ],
    "edges": [{"source": "n1", "target": "n2", "source_port": 0, "target_port": 0}],
    "selected": "n1"
  },
  "workspace_id": 42
}
```

Respuesta (siempre 200 salvo errores de petición o permisos):

```json
{
  "reply": "Texto en markdown",
  "summary": ["Añado Filter (n2) después de n1."],
  "assumptions": ["n2: filtro por nombre, el usuario no ha dado otro campo"],
  "warnings": ["n2: falta value. Se puede completar en el engranaje del nodo."],
  "needs_confirmation": false,
  "proposal": { "mode": "patch", "name": "", "description": "", "ops": [ ... ] },
  "error": false
}
```

| Código | Cuándo |
|---|---|
| 404 | El asistente no está activo |
| 403 | Usuario sin staff/superusuario, o sin permiso de edición sobre el workspace |
| 400 | Cuerpo no JSON o mensaje vacío |
| 404 (JSON) | `workspace_id` no existe |
| 200 con `error: true` | Fallo del proveedor de IA (tiempo, clave, cuota) o error inesperado. El detalle va al log `gvsigol` |

Límites: mensaje de 8000 caracteres, 16 mensajes de historial, canvas serializado de 24000 caracteres, 40 nodos por propuesta.

### Formato de la propuesta

`replace` sustituye el flujo entero:

```json
{
  "mode": "replace",
  "name": "CSV a PostGIS",
  "description": "",
  "nodes": [
    {"id": "n1", "alias": "n1", "type": "input_Csv", "label": "CSV", "parameters": {...},
     "schema": [], "schemaold": [], "x": 80, "y": 60, "inputs": 0, "outputs": 1}
  ],
  "edges": [{"source": "n1", "target": "n2", "source_port": 0, "target_port": 0}]
}
```

`patch` trae operaciones sobre el canvas abierto: `add_node`, `update_node`, `remove_node`, `add_edge`, `remove_edge`. Los alias de nodos existentes se traducen al id real de draw2d en el servidor.

## El catálogo de nodos (YAML)

Cada fichero de `nodes/` describe un tipo de nodo del editor. Se usa en dos sitios:

1. **Para el LLM**:
   - El prompt de sistema incluye un índice con una línea por tipo (`type: summary`).
   - La herramienta `get_node_specs` devuelve la ficha completa de los tipos que el modelo va a usar (hasta 12 por llamada). El prompt obliga a pedirla antes de usar un tipo.
2. **Para validar** en `graph.py`: tipos, parámetros, valores permitidos, puertos y tipo de conexión.

Ejemplo (`input_Postgis.yaml`):

```yaml
type: input_Postgis            # Nombre de la clase draw2d en TableShape.js
label: PgSQL/PostGIS           # Etiqueta de la paleta
family: input                  # input, transform u output (colores del panel)
summary: Lee una tabla o una consulta de una conexión PostgreSQL o PostGIS.
parameters:                    # Claves de "parameters" del nodo en TableShape.js
- name: db
  summary: Nombre de la conexión.
  required: true               # Aviso si falta
- name: schema-name
  summary: Esquema.
- name: tablename
  summary: Tabla.
- name: clause
  summary: Cláusula SQL adicional (WHERE, etc.).
ports:                         # En orden: el índice 0, 1… es el que usa el modelo
- direction: output
  label: Input
connection_types:              # Tipos de conexión ETL admitidos
- PostgreSQL
- PostGIS
connection_parameter: db       # Parámetro que contiene el nombre de la conexión
sql_parameters:                # Parámetros con SQL: se avisa al usuario que lo revise
- clause
```

Otros campos de parámetro: `choices` (lista de valores permitidos; cualquier otro valor se elimina con un aviso).

Lo que más influye en la calidad de las respuestas son `summary` (de la ficha y de cada parámetro) y `choices`: es lo único que el modelo sabe del nodo. Conviene escribirlos con frases cortas que digan qué hace y qué significa cada puerto (por ejemplo, en `trans_Join`: "Entrada 0 es la principal y la 1 la secundaria").

## Validación de propuestas

`graph.validate_proposal` se ejecuta siempre en el servidor antes de devolver nada al navegador. Lo que el modelo proponga mal se elimina y se explica en `warnings`:

| Regla | Efecto |
|---|---|
| Tipo que no está en el catálogo | Se quita el nodo y sus aristas |
| Parámetro que no existe en la ficha | Se quita el parámetro |
| Valor fuera de `choices` | Se quita el parámetro |
| Conexión que el usuario no tiene | Se quita el parámetro de conexión |
| Conexión de un tipo no admitido (`connection_types`) | Se quita el parámetro de conexión |
| Puerto fuera de rango | Se quita la arista |
| Parámetro `required` vacío | Aviso para completarlo en el engranaje |
| SQL escrito por el asistente (`sql_parameters`, `trans_ExecuteSQL`) | Aviso para revisarlo antes de guardar o ejecutar |
| Más de 40 nodos | Se omiten los sobrantes |
| `update_node` / `remove_node` de un alias que no está en el canvas | Se ignora la operación |
| Edición restringida | No se permite `replace` ni tocar nodos `input_*`, `output_*` y `trans_ExecuteSQL` |

También asigna coordenadas por profundidad topológica (columnas de 280 px, filas de 160 px) y genera el `summary`.

`needs_confirmation` es `true` en un `replace` con el canvas ocupado o en un `patch` con `remove_node` o `remove_edge`.

## Frontend

`Assistant.js` es un IIFE sin dependencias de `Toolbar.js`. Usa:

- `window.etlApp.view` (canvas draw2d), expuesto en `SchemaCanvas.js`. Si aún no existe al iniciar, reintenta durante 5 segundos.
- `jsonParams` (global de `TableShape.js`), la fuente de verdad de los parámetros de cada nodo.
- De `DrawNodes.js`: `drawNodes`, `fillEtlNodeForm`, `etlFindLine`, `etlClearCanvas` y `EtlApplyCommand`.

Al aplicar una propuesta:

1. Abre una transacción del CommandStack con la etiqueta `etl-assistant`.
2. `replace`: vacía el canvas y dibuja nodos y aristas con `drawNodes`. `patch`: añade, actualiza o elimina nodo a nodo.
3. Rellena el formulario de cada nodo (`fillEtlNodeForm`) y actualiza `jsonParams`.
4. Propaga el esquema desde los nodos de entrada.
5. Cierra la transacción: **Deshacer** revierte todo el cambio de una vez (solo si lo último del CommandStack es del asistente).

`DrawNodes.js` solo se carga cuando el asistente está activo. La carga de un workspace guardado sigue usando el código original de `Toolbar.js`.

## Seguridad y permisos

- Solo usuarios staff o superusuario.
- El modo de edición se calcula en el servidor con `can_edit` / `can_edit_restrictedly` del workspace; cualquier flag del cliente se ignora.
- Las herramientas solo ven las conexiones de `get_etl_connections_list(request)`, sin credenciales. Esquemas y tablas se validan como identificadores antes de consultar.
- El asistente no guarda, no ejecuta y no escribe SQL salvo que el usuario lo pida; si lo hace, se avisa.
- Las respuestas en markdown se sanean con DOMPurify antes de pintarse.
- El canvas y el historial que envía el cliente se recortan en tamaño.

## Cómo extenderlo

### Añadir un nodo nuevo al asistente

Cuando se añade un tipo nuevo a `TableShape.js` y a la paleta de `etl.html`:

1. Generar el borrador:

   ```bash
   docker exec -it gvsigol-back python manage.py etl_assistant_scaffold trans_MiNodo
   ```

   Lee la clase en `TableShape.js` (claves de `parameters`, puertos `createPort`, tipos de conexión del desplegable) y la etiqueta de la paleta, y escribe `assistant/nodes/trans_MiNodo.yaml`. Con un tipo concreto sobrescribe la ficha.

   Otras opciones:

   ```bash
   python manage.py etl_assistant_scaffold --all          # Solo las fichas que falten
   python manage.py etl_assistant_scaffold --all --force  # Regenera todas (pisa los cambios manuales)
   ```

2. **Revisar la ficha a mano**: escribir `summary`, describir los parámetros, añadir `choices`, `required`, `sql_parameters` y el significado de cada puerto. Los textos fijos de los nodos existentes están en `SUMMARIES` y `EXTRA_CHOICES` de `scaffold.py`; añadir ahí el nodo nuevo hace que `--all --force` no pierda esos textos.
3. Comprobar que el formulario del nodo se rellena bien al aplicar: `fillEtlNodeForm` busca los campos por `#<parametro>-<id del nodo>`, como hace la restauración de workspaces.
4. Ejecutar los tests: `test_every_palette_shape_has_a_yaml_spec` falla si falta la ficha y `test_parameter_keys_and_port_counts_match_tableshape` si no coinciden parámetros o puertos.

No hace falta tocar el prompt: el índice se genera desde el catálogo.

### Añadir una herramienta

1. Definirla en `tools.build_tools` con `@tool`. El docstring es lo que lee el modelo: decir qué devuelve y cuándo usarla.
2. Devolver siempre JSON (`_json(...)`) y errores como `{"error": "..."}`, nunca excepciones.
3. Filtrar por las conexiones y permisos del usuario (`request`, `connections`, `restricted` llegan como argumentos).
4. Añadirla a la lista que devuelve `build_tools`.
5. Si cambia el modo de trabajo, mencionarla en `prompt.py`.

### Cambiar el comportamiento del modelo

El prompt está en `prompt.system_prompt`. Las llaves `{ }` se escapan al final porque LangChain las interpreta como variables, y `%` se duplica en lo que se inserta con formato. El test `test_prompt_escapes_braces_and_percents` lo comprueba.

### Añadir un idioma de respuesta

Añadir el código a `_LANGUAGE_NAMES` en `prompt.py`. El idioma se toma de `django.utils.translation.get_language()`; si no se reconoce, se usa español.

### Cambiar las sugerencias iniciales

Son botones `.pl-assistant__example` en `templates/etl.html`:

- `data-when="empty"` o `data-when="flow"`: se muestran con el canvas vacío o con nodos.
- `data-selection="yes"` / `"no"`: solo con o sin nodo seleccionado.
- `data-example`: frase que se envía al pulsar (traducible con `{% trans %}`).

`Assistant.js` (`refreshExamples`) las alterna al cambiar el canvas o la selección. Se recomiendan como máximo cuatro visibles a la vez.

### Cambiar el proveedor o el modelo

El LLM se crea con `build_llm` de GeoCopilot; cualquier proveedor que soporte GeoCopilot y admita *tool calling* funciona. `GEOETL_LLM_MODEL` permite usar un modelo distinto al de GeoCopilot. Para un proveedor nuevo hay que añadirlo también en `access.assistant_feature_enabled`.

## Traducciones

Los textos están en inglés en el código (`{% trans %}` en la plantilla y `gettext()` en `Assistant.js`) y traducidos en `locale/es/LC_MESSAGES/django.po` y `djangojs.po`. Tras editar un `.po`:

```bash
docker exec -it gvsigol-back sh -c "cd /opt/gvsigonline/plugin_geoetl/gvsigol_plugin_geoetl && django-admin compilemessages -l es"
```

(requiere `gettext` instalado). Después, reiniciar el backend: el catálogo JS se cachea 24 horas en memoria.

Los mensajes que genera el servidor (avisos, resúmenes, errores) están directamente en español.

## Tests

```bash
cd plugin_geoetl
python3 -m unittest discover -t . -s gvsigol_plugin_geoetl/tests -p 'test_assistant_*.py'
```

| Fichero | Qué cubre |
|---|---|
| `test_assistant_access.py` | Activación, proveedores, permisos de usuario y modo de edición |
| `test_assistant_catalog.py` | Cada nodo de la paleta tiene ficha; parámetros y puertos coinciden con `TableShape.js`; escapado del prompt; comando scaffold |
| `test_assistant_graph.py` | Validación: tipos, parámetros, puertos y conexiones; confirmaciones; alias a UUID; edición restringida |

No necesitan Django ni LLM; el test del comando de manage.py se salta si Django no está instalado.

## Compatibilidad con workspaces existentes

Con el asistente apagado el editor se comporta igual que antes:

- La plantilla no pinta botón, panel, CSS ni scripts del asistente.
- La carga de workspaces guardados es el código original de `Toolbar.js` (con `draw2d.io.json.Reader`), sin cambios.
- El endpoint devuelve 404.
- El formato JSON de los workspaces no cambia: lo que dibuja el asistente se guarda igual que lo que dibuja el usuario.

Para desplegar en producción se recomienda subir primero con el asistente apagado, abrir, guardar y ejecutar algunos flujos complejos, y activarlo después.

## Problemas frecuentes

| Síntoma | Causa probable |
|---|---|
| No aparece el botón Asistente | Falta alguna condición de [Activación](#activación), o el usuario no es staff. Revisar el log por `etl_assistant` |
| "No se ha podido consultar el asistente" | Error del proveedor o del agente. El traceback está en el log `gvsigol` (`etl_assistant: fallo al invocar el agente`) |
| "La clave del proveedor de IA no es válida" | Clave de GeoCopilot caducada o incorrecta |
| "Se ha superado la cuota" | Límite del proveedor de IA |
| El panel aparece sin estilos | Caché del navegador: Ctrl+F5 |
| Textos en inglés | `.mo` sin compilar o catálogo JS cacheado: compilar, reiniciar el backend y Ctrl+F5 |
| El asistente no conoce un nodo | Falta su ficha en `nodes/`; ver [Añadir un nodo nuevo](#añadir-un-nodo-nuevo-al-asistente) |
| Una conversación antigua se ve rara tras actualizar | Borrarla con la papelera del panel (vive en `sessionStorage`) |
