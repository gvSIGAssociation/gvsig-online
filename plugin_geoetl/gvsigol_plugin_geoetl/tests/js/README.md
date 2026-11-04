# Tests JS de los nodos predictivos

Cargan el JS **real** del editor (`TableShape.js` cabecera, `SchemaPropagator.js` y
`PredictiveShapes.js`) en jsdom con jQuery real. Solo draw2d y el backend están simulados, así que
comprueban los diálogos (rellenar, validar, guardar, reabrir), los esquemas y el veto de conexiones
entre puertos de distinto tipo. No comprueban el dibujo en el canvas.

Las dependencias no están en el repositorio. Se instalan fuera del árbol:

```bash
mkdir -p /tmp/etl-js && cd /tmp/etl-js && npm init -y && npm install jsdom@22 jquery@3.6.0
cd <repo>/plugin_geoetl/gvsigol_plugin_geoetl/tests/js
NODE_PATH=/tmp/etl-js/node_modules node run.js
```

## Chat del asistente

`assistant.js` carga el `Assistant.js` real (con `marked` y `DOMPurify` reales) y simula el canvas y el
backend. Cubre el arranque de un workspace nuevo, lo que se envía al servidor, los ids clicables, Detener,
↑/↓, el contador, copiar, editar y reenviar, regenerar, el historial con el estado de las propuestas y la
exportación a Markdown.

```bash
NODE_PATH=/tmp/etl-js/node_modules node assistant.js
```
