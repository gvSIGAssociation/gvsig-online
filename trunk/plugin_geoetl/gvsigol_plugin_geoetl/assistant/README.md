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
- **Explicar** el flujo del canvas paso a paso, citando cada nodo por su id.
- **Revisar** el flujo con una comprobación exacta (`check_workspace`): nodos sin configurar, parámetros obligatorios vacíos, entradas sin conectar, tipos de puerto que no encajan, ciclos, salidas sin usar, conexiones no disponibles y flujos sin salida.
- **Resolver dudas** sobre los nodos y sus opciones a partir de las fichas.
- **Consultar las fuentes reales**: lista las conexiones ETL del usuario, sus esquemas, tablas y columnas, y los nombres de los ficheros de sus carpetas del gestor de ficheros (nunca el contenido). Deduce los nodos a partir de la diferencia entre entradas y destino.
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
| `AGENT_MAX_ITERATIONS` (de `LANGCHAIN_SETTINGS` de GeoCopilot) | 15 | Máximo de iteraciones del agente por turno (como mínimo se usan 20) |
| `ETL_ASSISTANT_ENGINE` | `legacy` | Motor del agente: `legacy` (`AgentExecutor`, el de siempre) o `langgraph` (`create_react_agent`). Si `langgraph` no está instalado se usa `legacy` y se avisa en el log |
| `ETL_ASSISTANT_EXECUTION` | `inline` | Dónde se ejecuta el turno: `inline` (en el proceso web, como siempre) o `celery` (en un worker, ver [Ejecución en Celery](#ejecución-en-celery)) |
| `ETL_ASSISTANT_CELERY_QUEUE` | `geocopilot` | Cola de Celery del asistente. Por defecto la del worker de GeoCopilot |
| `ETL_ASSISTANT_STREAMING` | `False` | Pasos en vivo en el panel ("Leyendo las columnas de public.municipios…") y Detener real: el turno se corta en el servidor. Usa `/etl/etl_assistant/stream/` (SSE) y `/etl/etl_assistant/cancel/` |
| `ETL_ASSISTANT_TOKEN_STREAMING` | `False` | Texto de la respuesta en vivo mientras se genera. Solo con `ETL_ASSISTANT_STREAMING=True` y `ETL_ASSISTANT_ENGINE=langgraph` |
| `ETL_ASSISTANT_ACTIONS` | `False` | Problemas del flujo con botones en el panel: **Configurar** abre el engranaje del nodo (sin llamar al modelo), **Arreglar** / **Arreglar todo** se lo piden al asistente. Ver [Problemas con botones](#problemas-con-botones) |
| `ETL_ASSISTANT_QUESTIONS` | `False` | El asistente pregunta con opciones para elegir con un clic (herramienta `ask_user`) en lugar de preguntas numeradas en el texto. Ver [Preguntas con opciones](#preguntas-con-opciones) |
| `ETL_ASSISTANT_ALTERNATIVES` | `False` | Las suposiciones sobre un parámetro llevan un desplegable para cambiarlas con un clic, sin llamar al modelo. Ver [Suposiciones cambiables](#suposiciones-cambiables) |
| `ETL_ASSISTANT_PARAM_PICKER` | `False` | Botón **Elegir** en los problemas de parámetros, para completarlos desde el chat sin llamar al modelo. Necesita `ETL_ASSISTANT_ACTIONS=True`. Ver [Completar parámetros](#completar-parámetros) |
| `ETL_ASSISTANT_NEXT_STEPS` | `False` | Sugerencias de siguiente paso tras cada respuesta y arranque guiado de "CSV a PostGIS". Ver [Siguiente paso y arranque guiado](#siguiente-paso-y-arranque-guiado) |
| `ETL_ASSISTANT_COLUMNS` | `False` | El asistente lee las columnas de las entradas (shapefile, CSV, Excel, KML y tablas de PostGIS, Oracle y SQL Server) y pregunta por los campos con sus valores reales. Ver [Columnas de las entradas](#columnas-de-las-entradas) |
| `ETL_ASSISTANT_MAX_SECONDS` | 120 | Solo con `langgraph`: tiempo máximo de un turno. Al agotarse se conserva la propuesta si ya la había. 0 = sin límite |

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

- Cada nodo muestra su id (`n1`, `n2`…) en la cabecera; es el mismo que usa el asistente. Los ids del texto de las respuestas, del resumen y de las suposiciones son etiquetas que resaltan el nodo al pasar el ratón y lo centran al hacer clic.
- Al pasar el ratón por un mensaje aparecen sus acciones: en las preguntas, **copiar**, **editar y reenviar** (la vuelve a poner en el cuadro) y **volver a preguntar**; en las respuestas, **copiar** (texto, cambios, suposiciones y avisos en Markdown) y, en la última, **regenerar** (no se ofrece si sus cambios ya se aplicaron o están pendientes de aplicar).
- Con el cuadro vacío, **↑** recupera las preguntas anteriores y **↓** vuelve hacia las recientes.
- Mientras el asistente piensa se ve el tiempo transcurrido y el botón de enviar pasa a **Detener**, que cancela la petición sin cambiar el canvas.
- Cerca del límite de 8000 caracteres aparece un contador; por encima no se puede enviar.
- El botón de descarga guarda la conversación en Markdown; la papelera la borra (pide confirmación).
- Seleccionar un nodo en el canvas lo pasa como contexto ("después de este").
- El panel se redimensiona arrastrando el borde izquierdo (320–600 px) y recuerda ancho y estado abierto (`localStorage`).
- La conversación se guarda por workspace en `sessionStorage` (`etl-assistant-chat:<id>`). La de un workspace nuevo sin guardar no se conserva al abrir otro nuevo. Se envían como historial los últimos 16 mensajes; cada respuesta lleva los cambios que propuso y si el usuario los aplicó, descartó o deshizo.
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

1. `Assistant.js` resume el canvas (nodos con su id `n1…`, parámetros, esquema, estado de la rueda, posición, aristas, nodo seleccionado y siguiente id libre) y lo envía con el mensaje y el historial.
2. `views.etl_assistant` comprueba activación, usuario y permisos sobre el workspace (edición completa o restringida).
3. `agent.run_assistant` calcula los permisos del usuario (`context.AssistantContext`: conexiones, carpetas del gestor de ficheros, modo de edición, idioma) y monta el agente con el prompt de sistema, el historial y las herramientas. El motor depende de `ETL_ASSISTANT_ENGINE`: `AgentExecutor` + `create_tool_calling_agent` (legacy) o `create_react_agent` de LangGraph (`engine.py`), con la misma interfaz. Las herramientas no usan el `request`: el contexto se puede serializar (`to_payload`) para ejecutar el agente fuera del proceso web.
4. El prompt obliga al modelo a decidir primero la intención (construir o modificar, explicar, revisar, pregunta general). Solo construir o modificar termina llamando a `propose_workspace`.
5. `graph.validate_proposal` limpia la propuesta contra el catálogo y las conexiones del usuario; si queda algo válido lo guarda como resultado del turno. Además `review.check_graph` revisa cómo quedaría el flujo y devuelve al modelo los errores con una instrucción: si la propuesta se rechaza o tiene errores corregibles, el modelo la corrige y la reenvía (como mucho tres intentos; la última válida sustituye a las anteriores).
6. Comprobación de coherencia: si la respuesta final afirma un cambio ("he añadido…") y no hay propuesta, el agente pide al modelo una segunda pasada para que la haga o confirme que no pretendía cambiar nada. Si aun así no hay propuesta, el chat avisa de que el canvas sigue igual.
7. Si se alcanza el límite de iteraciones o falla el proveedor después de validar una propuesta, la propuesta se conserva; sin propuesta, se devuelve un mensaje en español.
8. El panel recibe la propuesta y la dibuja con `drawNodes` dentro de una transacción del CommandStack de draw2d (una sola entrada de deshacer).

### Ficheros

Backend (`gvsigol_plugin_geoetl/assistant/`):

| Fichero | Responsabilidad |
|---|---|
| `views.py` | Endpoint `POST /etl/etl_assistant/`. Validación de la petición y permisos. Importa el agente de forma perezosa |
| `access.py` | Reglas puras de activación y permisos (`assistant_feature_enabled`, `user_may_use`, `workspace_edit_mode`, `provider_is_ready`) |
| `agent.py` | Construye el LLM, el prompt y el `AgentExecutor`; canvas compacto, historial con el resultado de cada propuesta, comprobación de coherencia, límite de iteraciones, traza opcional y errores del proveedor legibles |
| `prompt.py` | Prompt de sistema: intenciones, reglas de trabajo, autocorrección, idioma e índice del catálogo |
| `tools.py` | Herramientas que puede llamar el modelo (cada una protegida: un fallo se devuelve como error y no tumba el turno) |
| `review.py` | Revisión exacta de un flujo, del canvas o de cómo quedaría tras una propuesta |
| `graph.py` | Validación, maquetación (x, y) y resumen de las propuestas. En un patch, cada nodo nuevo se coloca junto al que le da datos sin montarse sobre otro |
| `catalog.py` | Carga de las fichas YAML e índice para el prompt (primera frase de cada ficha) |
| `nodes/*.yaml` | Una ficha por tipo de nodo |
| `shapes.py` | Lee `TableShape.js` y la paleta de `etl.html` para generar fichas |
| `scaffold.py` | Genera borradores YAML (lo usa el comando de manage.py) |

Fuera de la carpeta:

| Fichero | Cambio |
|---|---|
| `settings.py` | `ETL_ASSISTANT_ENABLED`, `ETL_ASSISTANT_TRACE`, `GEOETL_LLM_MODEL` |
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

### Ejecución en Celery

Con `ETL_ASSISTANT_EXECUTION=celery` el turno se ejecuta en un worker de Celery (`assistant/execution.py`, tarea `geoetl.run_assistant` en `tasks.py`). El navegador no nota nada: el endpoint y el JSON son los mismos.

1. La vista calcula los permisos del usuario (`AssistantContext.to_payload()`): conexiones, carpetas del gestor de ficheros, modo de edición e idioma. El worker no tiene `request` ni la sesión de Keycloak.
2. Crea su cola de eventos en RabbitMQ (`event_bus` de GeoCopilot, cola `geocopilot.events.etl-<id>`) y después encola la tarea en `ETL_ASSISTANT_CELERY_QUEUE`.
3. El worker publica `started`, ejecuta `run_assistant` con el contexto y publica `result` con el JSON de siempre.
4. Si en 20 s ningún worker empieza el turno, responde "El asistente no está disponible en este momento" y marca el turno como cancelado en la caché compartida (un worker que lo recoja tarde no lo ejecuta). Si pasa el límite de la tarea (`ETL_ASSISTANT_MAX_SECONDS` + 60 s, o 660 s sin plazo) sin resultado, responde con un error.

Requisitos:

- `GEOCOPILOT_SHARED_CACHE=True` (caché compartida entre el web y los workers). Sin ella se ejecuta en el proceso web y se avisa en el log.
- Un worker escuchando la cola (el nodo `geocopilot` de `CELERYD_NODES`). Tras desplegar código nuevo hay que recrear el contenedor (`docker compose up -d --force-recreate backend`) para que el worker cargue la tarea.
- Recomendado `ETL_ASSISTANT_ENGINE=langgraph`: con `legacy` el turno no tiene plazo propio y solo lo corta el límite de la tarea.

### Pasos en vivo y Detener (streaming)

Con `ETL_ASSISTANT_STREAMING=True` la plantilla marca el panel con `data-streaming="1"` y `Assistant.js` usa `fetch` contra `/etl/etl_assistant/stream/` en lugar de `$.ajax`. Sin el interruptor (o en un navegador sin `fetch`/`AbortController`) se usa la petición de siempre.

- El servidor envía eventos SSE (`data: {...}`): `start` (con el `query_id`), `step` por cada herramienta (`tool` y en `detail` solo conexión, esquema, tabla, tipos de nodo, carpeta o ids; nunca la propuesta, SQL ni rutas completas), `ping` cada 10 s y `result` con el mismo JSON que `/etl/etl_assistant/`.
- Con `ETL_ASSISTANT_TOKEN_STREAMING=True` (y motor `langgraph`) llegan también eventos `answer_delta` `{delta, reset}` con el texto de la respuesta mientras el modelo lo escribe (`engine.AnswerTextStreamer`): solo el texto de los mensajes del modelo, nunca llamadas a herramientas ni sus resultados; el primer trozo de cada mensaje nuevo lleva `reset`. La segunda pasada de la comprobación de coherencia no se enseña en vivo. El texto en vivo es provisional: al llegar `result` el panel lo sustituye por la respuesta definitiva.
- En `inline` el turno corre en un hilo del proceso web; en `celery`, el web retransmite los eventos del worker.
- El texto de cada paso lo compone el navegador con `gettext` (`stepText` en `Assistant.js`).
- **Detener** corta la petición y llama a `/etl/etl_assistant/cancel/` con el `query_id`; solo puede detenerlo quien lanzó el turno. Si el navegador se va, el servidor lo detecta al escribir (como muy tarde con el ping) y también lo cancela. El agente para antes de la siguiente llamada al modelo o herramienta (`streaming.CancelCallbackHandler`) y no se aplica ninguna propuesta.
- Para que Detener funcione entre procesos (uWSGI con varios procesos, o Celery) hace falta `GEOCOPILOT_SHARED_CACHE=True`; sin ella la desconexión sí detiene el turno en el mismo proceso.

### Problemas con botones

Con `ETL_ASSISTANT_ACTIONS=True` la respuesta lleva además `issues`: `[{level, node, code, param?, message}]`, los errores primero.

- Con propuesta: los problemas del flujo tal como quedará al aplicarla (`check_graph` sobre `graph_after`).
- Sin propuesta: los de la última revisión del canvas que hizo el agente en el turno (`check_workspace` sin argumentos). La revisión de una propuesta con `check_workspace(proposal_json)` no se enseña.
- `param` solo aparece en `missing_parameter` e `invalid_choice`.

El panel pinta la tarjeta "Problemas del flujo":

- **Configurar** (`unconfigured`, `missing_parameter`, `invalid_choice`, `invalid_schema`, `unknown_connection`, `connection_type`): centra el nodo y lanza el clic de su engranaje (`etlFindGear` de `NodeHeader.js` + `fireEvent('click')`), igual que si el usuario pulsara la rueda. No llama al modelo. Si el nodo no está en el canvas (propuesta pendiente de aplicar), avisa.
- **Arreglar** (`unconnected_input`, `duplicated_input`, `dead_end`, `no_output`, `cycle`, `kind_mismatch`, `bad_port`, `source`, `target`): envía "Arregla este problema: …" como mensaje del usuario. Con dos o más, **Arreglar todo** los envía juntos.
- Los problemas se guardan con el mensaje en `sessionStorage` y se vuelven a pintar al recargar.

### Preguntas con opciones

Con `ETL_ASSISTANT_QUESTIONS=True` el agente tiene la herramienta `ask_user` y la regla de "Dudas" del prompt le pide usarla (sin el interruptor, ni la herramienta ni el prompt cambian).

- El modelo indica hasta 4 preguntas con `label`, `text`, `node`/`param` y de dónde salen las opciones (`source`): `choices` (ficha del parámetro, también de un nodo de la propuesta del turno), `connections` (las del usuario, filtradas por los tipos del nodo), `datastores` (destino de una tabla PostGIS, ver más abajo), `tables`, `columns`, `workspaces` y `layer_groups` (donde el usuario puede publicar, con `etl_raster_publish.publish_targets`), `files` o `custom` (hasta 8 textos cortos). Los ficheros no se listan: llevan `file_picker: {extensions}` y el panel abre el administrador de archivos, como los nodos, con sus permisos y su subida de ficheros.
- `questions.resolve_questions` genera o valida las opciones con los datos reales: descarta las que no existen y, si una pregunta se queda sin opciones o no se pueden leer, la deja de respuesta libre. Al modelo le devuelve notas de lo descartado.
- Si el modelo no indica bien el origen, se corrige en el servidor: se aceptan sinónimos (`file`, `connection`…) y, sin origen útil, se deduce del parámetro del nodo o del texto de la pregunta ("¿Qué shapefile…?", "¿En qué conexión…?"). Si el origen es correcto pero no hay nada que ofrecer, la pregunta lleva `empty` (`connections`, `workspaces` o `layer_groups`) y el panel lo explica. La traza guarda `asked`: origen y número de opciones de cada pregunta.
- La respuesta lleva `questions: [{id, label, text, node, param, multiple, options: [{value, label}]}]`.
- El panel pinta la tarjeta "El asistente necesita saber": botones de opción (hasta 6), lista con buscador (más de 6), casillas (`multiple`), "Otro…" con texto, y campo libre si no hay opciones. **Responder** se activa cuando todas tienen respuesta (Enter en un texto también responde).
- Para el **destino de una tabla PostGIS** se ofrecen almacenes (`datastores`) en lugar de conexiones, aunque el modelo pregunte por una conexión. Cada uno aporta `db-option` y `schema-name-option`. Solo aparecen los PostGIS con conexión y esquema (los antiguos sin ellos no se pueden traducir a parámetros), si el usuario puede usar el almacén (`can_use_datastore`) y además usar su conexión en ETL (`context.usable_datastores`). **Crear un almacén nuevo…** abre el formulario `datastore_add` en una ventana, con sus permisos y validaciones; al guardar (redirige a `datastore_list`) se cierra, se recarga la lista y queda marcado el nuevo. Las respuestas llevan `connection=X; schema=Y`. Lo mismo vale para **Elegir** en el parámetro de conexión de `output_Postgis` y para el arranque guiado.
- La contestación se envía como mensaje del usuario: `Separador: ; · Fichero: rol_a/padron.csv (file:///…)`. El valor va entre paréntesis cuando es distinto de lo que se ve.
- La tarjeta queda de solo lectura con lo elegido. Si el usuario escribe en el cuadro en lugar de responder, las preguntas abiertas se cierran ("Respondido en el cuadro de texto.").
- En el historial, cada respuesta con preguntas lleva `[Pregunté con opciones: Etiqueta: pregunta | …]` para que el modelo entienda la contestación.

### Suposiciones cambiables

Con `ETL_ASSISTANT_ALTERNATIVES=True` el prompt explica a `propose_workspace` que una suposición sobre un parámetro puede ser un objeto `{text, node, param, source, …}` (orígenes como en `ask_user`, sin `custom`). Sin el interruptor, los objetos se ignoran como siempre.

- `alternatives.split_assumptions` deja en la propuesta solo los textos (`graph.validate_proposal` no cambia).
- Con la propuesta validada, `alternatives.resolve_alternatives` comprueba que el nodo (de la propuesta o del canvas) y el parámetro existen, toma su valor y lee las alternativas reales. Si no hay al menos dos opciones, la suposición queda como texto.
- La respuesta lleva `assumption_choices: [{text, node, param, value, options}]` (como mucho 8).
- El panel pone un desplegable junto a la suposición. Al cambiarlo aplica un `update_node` con el resto de parámetros del nodo intactos (una entrada de Deshacer, sin llamar al modelo) y ofrece **Deshacer** al lado. Con la propuesta pendiente, se activa al pulsar Aplicar; si se descartó o deshizo, queda desactivado.
- Los cambios se guardan en el mensaje (`changes`) y van en el historial como `[El usuario cambió: n3 field = cod_ine]`, para que el modelo los respete.
- En edición restringida no se ofrecen alternativas de entradas, salidas ni SQL (`graph.is_protected`).
- Una suposición sobre un fichero no lleva desplegable: **Cambiar fichero** abre el administrador de archivos.

El administrador entrega la ruta a `window.filemanagerCallback`, una función global que comparten los nodos: `openFileManager` instala la del chat solo mientras se elige y devuelve después la anterior, como el nodo ráster.

### Completar parámetros

Con `ETL_ASSISTANT_PARAM_PICKER=True` (y `ETL_ASSISTANT_ACTIONS=True`), los problemas de un parámetro que tiene una lista cerrada de valores llevan `pick: {type}` y el panel añade **Elegir** junto a Configurar.

- `POST /etl/etl_assistant/options/` con `{type, param, parameters, workspace_id}` devuelve `{options: [{value, label}], needs, error}`, con los permisos del usuario y sin llamar al modelo. `needs` (`connection` o `schema`) indica qué hay que elegir antes.
- `param_options.picker_source` decide el origen: conexión del nodo (filtrada por tipo), opciones de la ficha, esquema o tabla de entrada, y workspace o grupo de capas de `output_RasterPublish`. En un parámetro de fichero (`FILE_EXTENSIONS`, las mismas extensiones que acepta cada nodo) Elegir abre el administrador de archivos y el endpoint no interviene. Los parámetros SQL, los textos libres, las columnas y la tabla de una salida solo se completan en el engranaje.
- En edición restringida no se ofrece Elegir en entradas, salidas ni SQL, y el endpoint responde 403.
- Al elegir se aplica un `update_node` con el resto de parámetros intactos y el problema queda resuelto, con **Deshacer**. El cambio va al historial como `[El usuario cambió: …]`.
- Deshacer repone el valor anterior del parámetro con un cambio nuevo, en lugar de deshacer lo último de la pila, que podría ser otro cambio.
- Los cambios de un parámetro usan la etiqueta de Deshacer `etl-assistant-param`: el botón Deshacer de una propuesta solo actúa si lo último de la pila es esa propuesta.

### Siguiente paso y arranque guiado

Con `ETL_ASSISTANT_NEXT_STEPS=True`:

- La respuesta lleva `next_steps: [{code}]` (`add_output`, `explain`, `review`), calculados por reglas en `next_steps.compute_steps` sobre cómo queda el flujo, sin llamar al modelo. Con problemas de estructura no se sugiere nada (ya está Arreglar). No se añade salida en edición restringida. No se sugiere nada tras un error, con una propuesta pendiente de aplicar o con preguntas abiertas.
- El panel pone el texto y traduce. Solo se ven en la última respuesta, y desaparecen al deshacer su propuesta. Al pulsar uno se envía como mensaje del usuario.
- Con el canvas vacío, el ejemplo "CSV a PostGIS" (`data-guided-start`) abre un formulario para elegir el fichero (en el administrador de archivos) y la conexión de destino (`POST /etl/etl_assistant/options/`), y compone la petición. Si no hay opciones o fallan, avisa y ofrece preguntar igualmente con el texto del ejemplo.

### Columnas de las entradas

Un nodo de entrada solo lee sus columnas al pulsar Aceptar. Con `ETL_ASSISTANT_COLUMNS=True`:

- `columns.read_columns` las lee con los mismos lectores del editor, comprobando antes el acceso del usuario al fichero (dentro del gestor de ficheros y en sus carpetas) o a la conexión. No pulsa Aceptar, para no guardar valores que el usuario no ha elegido, como un EPSG por defecto.
- `propose_workspace` deja las columnas en los nodos de la propuesta y se las devuelve al modelo. Tras Elegir o Cambiar fichero, el panel las pide a `POST /etl/etl_assistant/columns/`.
- Un Excel con una hoja la usa directamente. Con varias, aparece el problema "falta elegir la hoja" con **Elegir** (`sheets` en `param_options`).
- La rueda de una entrada queda en rojo mientras no tenga columnas.
- Herramienta `get_file_columns` y `ask_user` con `source: columns` y `file`, para preguntar el campo de cruce con las columnas reales.
- El cruce se ejecuta con `attr-1` y `attr-2`: son obligatorios en la ficha, y si el modelo solo manda `attr1` y `attr2` se copian. `check_graph` avisa (`unknown_column`) si un campo no llega desde una entrada con columnas conocidas.

### Formato de las fichas

Además de `name`, `summary`, `required` y `choices`, un parámetro puede llevar:

| Clave | Uso |
|---|---|
| `format` | `list` si la ejecución espera una lista, `spaced` si espera un texto separado por espacios. Con `ETL_ASSISTANT_COLUMNS`, el servidor convierte el valor al formato correcto |
| `default` | Valor de los nodos nuevos si el modelo no lo envía. La ejecución lee muchos parámetros directamente y fallaría sin ellos |
| `example` | Ejemplo para el modelo |
| `column` | Puerto de entrada cuyas columnas usa. `check_graph` avisa (`unknown_column`) si la columna no llega |

Las expresiones SQL libres deben estar en `sql_parameters`, para que el panel avise de que hay que revisarlas.

Las herramientas `propose_workspace`, `check_workspace` y `ask_user` tienen argumentos tipados (`tool_schemas.py`). Siguen aceptando `proposal_json` y `questions_json`.

## Contrato del endpoint

`POST /gvsigonline/etl/etl_assistant/` con `Content-Type: application/json` y cabecera `X-CSRFToken`. Requiere sesión iniciada.

Petición:

```json
{
  "message": "Añade un filtro después de este nodo",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "...", "summary": ["Añado Filter (n2)."], "status": "applied"}
  ],
  "canvas": {
    "nodes": [
      {"alias": "n1", "id": "<uuid draw2d>", "type": "input_Postgis", "label": "PgSQL/PostGIS",
       "parameters": {"db": "mi_conexion", "schema-name": "public", "tablename": "municipios"},
       "schema": ["cod_mun", "nombre", "geom"], "status": "", "x": 80, "y": 60}
    ],
    "edges": [{"source": "n1", "target": "n2", "source_port": 0, "target_port": 0}],
    "selected": "n1",
    "next_alias": "n6"
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

Campos opcionales (los editores antiguos no los envían y todo sigue funcionando): `status` del nodo (`""` configurado, `unconfigured` rueda roja, `invalid` configuración que no encaja), `x`/`y`, `next_alias` (el editor no reutiliza los ids de nodos borrados) y, en el historial, `summary` y `status` (`applied`, `discarded`, `undone`, `pending`).

Límites: mensaje de 8000 caracteres, 16 mensajes de historial, 40 nodos por propuesta. El canvas se envía al modelo en JSON siempre válido de hasta 24000 caracteres: si no cabe, primero sin esquemas, luego con los textos largos recortados y, por último, sin parámetros (el modelo los pide con `get_canvas_nodes`). Nunca se pierden nodos ni conexiones.

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

También asigna coordenadas y genera el `summary`. En un `replace`, por profundidad topológica (columnas de 280 px, filas de 160 px). En un `patch`, cada nodo nuevo va a la derecha del nodo del que recibe datos (o a la izquierda del que alimenta) y baja de fila mientras choque con otro; sin posiciones del canvas (editor antiguo) se usa la maquetación topológica.

Después, `review.check_graph` revisa el flujo resultante (no modifica la propuesta): sus errores vuelven al modelo en `issues` para que los corrija. La misma revisión es la herramienta `check_workspace`.

### Herramientas del modelo

| Herramienta | Para qué |
|---|---|
| `list_connections` | Conexiones ETL del usuario (nombre y tipo, sin credenciales) |
| `list_tables`, `get_table_schema` | Esquemas, tablas y columnas de una conexión autorizada |
| `list_files` | Nombres de ficheros de las carpetas del gestor de ficheros a las que el usuario tiene acceso (mismos permisos que el gestor; ocultos excluidos; hasta 200, 4 niveles). Devuelve la ruta lista para el parámetro del nodo. Nunca lee el contenido |
| `get_node_specs` | Ficha completa de hasta 12 tipos |
| `get_canvas_nodes` | Parámetros y esquema completos de nodos del canvas, para canvas grandes |
| `check_workspace` | Revisión exacta del canvas, o de cómo quedaría con una propuesta sin registrarla |
| `propose_workspace` | Registra la propuesta validada; devuelve `accepted`, `errors`/`warnings`, `issues` e `instruction` |

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
2. Envolver el cuerpo con `_guarded(trace, nombre, body)` y devolver siempre JSON (`_json(...)`), con los errores como `{"error": "..."}`.
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
| `test_assistant_agent.py` | Revisión de flujos; colocación de nodos en un patch; canvas compacto; historial con el resultado de las propuestas; bucle del agente con un modelo simulado (autocorrección, comprobación de coherencia, límite de iteraciones, fallo del proveedor); herramientas nuevas y permisos de `list_files`; prompt y esquemas de herramientas válidos |
| `test_assistant_context.py` | Permisos sin `request`: el contexto serializado da lo mismo que el `request` en `list_files` y conexiones; el idioma llega al prompt |
| `test_assistant_engine.py` | Motor LangGraph con un modelo simulado: propuesta, segunda pasada, límites de iteraciones y de tiempo, fallos del proveedor, historial, prompt sin llaves duplicadas, elección del motor y vuelta a legacy |
| `test_assistant_execution.py` | Celery con RabbitMQ y worker simulados: elección del modo y vuelta a inline, tarea registrada sin reintentos, eventos del worker, turno cancelado antes de empezar, sin worker, sin resultado a tiempo, pings y el mismo JSON en la vista en los dos modos |
| `test_assistant_streaming.py` | Pasos y su contenido seguro, Detener a mitad de turno con los dos motores, eventos del stream inline y en Celery, vista SSE, cancelación solo por el dueño y desconexión del navegador |
| `test_assistant_token_streaming.py` | Texto en vivo: los trozos reconstruyen la respuesta, `reset` por mensaje, bloques de la API Responses, sin texto de herramientas, sin la segunda pasada y apagado sin el interruptor, con legacy o sin quien lo reciba |
| `test_assistant_actions.py` | `issues` solo con el interruptor; de la propuesta o de la revisión del canvas (no de la revisión de una propuesta); `param` en los problemas de parámetros; un fallo al prepararlos no rompe la respuesta |
| `test_assistant_questions.py` | Opciones de cada origen (ficha, propuesta, conexiones por tipo, tablas, columnas, ficheros, custom), descarte de opciones inventadas, respuesta libre, límites; herramienta y prompt solo con el interruptor; historial; motor LangGraph |
| `test_assistant_alternatives.py` | Alternativas de nodos actualizados y nuevos, conexiones por tipo, valor actual siempre presente, suposiciones no válidas como texto, fallos de lectura; sin el interruptor nada cambia; prompt e historial |
| `test_assistant_param_options.py` | Origen de cada parámetro, conexiones por tipo, extensiones, esquema y tabla dependientes, conexiones ajenas, `pick` en los problemas, edición restringida y endpoint `options` |
| `test_assistant_next_steps.py` | Reglas de las sugerencias, cuándo no se ofrecen, edición restringida, JSON público y endpoint `options` para el arranque guiado |
| `tests/js/assistant.js` | Chat real en jsdom: workspace nuevo, datos enviados, ids clicables, Detener, ↑/↓, contador, copiar, editar, regenerar, historial y exportar; con streaming, pasos en vivo, frames partidos, Detener con aviso al servidor, texto en vivo (Markdown saneado, `reset` y sustitución por la respuesta final) y stream cortado; problemas con Configurar (abre el engranaje, sin turno nuevo), Arreglar, Arreglar todo y su conservación al recargar; preguntas con opciones (botones, lista con buscador, Otro…, texto libre), Responder, mensaje enviado, tarjeta respondida o cerrada al escribir; suposiciones cambiables (parámetro aplicado conservando el resto, Deshacer, pendiente hasta Aplicar, nodo inexistente); Elegir (carga, aplica, Deshacer, avisos, buscador, propuesta pendiente); sugerencias de siguiente paso y arranque guiado |

Ninguno llama al proveedor de IA. `test_assistant_agent.py` necesita Django (`manage.py test gvsigol_plugin_geoetl.tests.test_assistant_agent`); los demás no. Los JS: `NODE_PATH=<jsdom+jquery>/node_modules node tests/js/assistant.js`.

### Traza para diagnosticar

Con `ETL_ASSISTANT_TRACE=True` cada turno deja una línea `etl_assistant trace {...}` en el log `gvsigol`: herramientas llamadas con su duración y si fallaron, número de propuestas, si hubo propuesta, si se llegó al límite de iteraciones y qué hizo la comprobación de coherencia (`nudged`, `fixed`, `no_change`, `warned`). No incluye textos del usuario ni datos de las tablas.

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
| "El asistente no ha propuesto ningún cambio" | El modelo dijo que cambiaba algo sin hacerlo, incluso tras la segunda pasada. Reformular la petición con más detalle; con `ETL_ASSISTANT_TRACE` se ve qué herramientas usó |
| "No he podido terminar: la petición necesita demasiados pasos" | Límite de iteraciones (`AGENT_MAX_ITERATIONS` de GeoCopilot, mínimo 20). Dividir la petición |
| El panel aparece sin estilos | Caché del navegador: Ctrl+F5 |
| Textos en inglés | `.mo` sin compilar o catálogo JS cacheado: compilar, reiniciar el backend y Ctrl+F5 |
| El asistente no conoce un nodo | Falta su ficha en `nodes/`; ver [Añadir un nodo nuevo](#añadir-un-nodo-nuevo-al-asistente) |
| Una conversación antigua se ve rara tras actualizar | Borrarla con la papelera del panel (vive en `sessionStorage`) |
