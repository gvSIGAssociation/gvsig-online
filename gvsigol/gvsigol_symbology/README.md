# Simbología de gvSIG Online (`gvsigol_symbology`)

Estilos de las capas (SLD publicados en GeoServer), biblioteca de símbolos y rampas de color. Este documento describe
sobre todo la **simbología avanzada de puntos, líneas y polígonos**: tramas, guiones a medida, marcas a lo largo de
las líneas, flechas en los extremos, desplazamiento lateral, formas nuevas y símbolos predefinidos.

## Principio: lo existente no cambia

- Los simbolizadores `MarkSymbolizer`, `LineSymbolizer` y `PolygonSymbolizer` tienen un campo `options` (JSON en un
  `TextField`, compatible con Django 2). **`options = NULL` es un simbolizador clásico** y se genera exactamente como
  siempre, en el SLD y en el estilo del visor de teselas vectoriales (MVT).
- El editor solo envía opciones si el símbolo usa algo que el clásico no puede expresar. Abrir un símbolo antiguo y
  cambiarle el color lo deja clásico.
- Las columnas del modelo siguen siendo la fuente de los valores básicos (colores, opacidades, grosor, tamaño,
  rotación, `stroke_dash_array`). Las opciones solo añaden lo demás.
- Grosores, tamaño y opacidad de las marcas admiten decimales (`IntegralFloatField`): los valores enteros se siguen
  leyendo como enteros, así que el SLD, el JSON del editor y las exportaciones no cambian (`"1"`, nunca `"1.0"`).

Las etiquetas (`TextSymbolizer.options`) siguen el mismo principio: ver `label_options.py` y `label_sld.py`.

## Qué se puede hacer

| Tipo | Opciones | SLD (GeoServer) | Visor MVT |
|---|---|---|---|
| Punto | 22 formas (`symbol_options.SHAPES`) | `WellKnownName` (`shape://`, `extshape://`, `qgis://`) | icono SVG generado |
| Punto | sin relleno, desplazamiento X/Y, ángulo sumado desde un campo | `Displacement`, `Rotation` con `ogc:Add` | `icon-offset`, `icon-rotate` |
| Línea | extremos, esquinas, guiones a medida y su desfase | `stroke-linecap/linejoin/dasharray/dashoffset` | `line-cap/join/dasharray` + desfase en el SPA |
| Línea | desplazamiento lateral (+ izquierda) | `PerpendicularOffset` | SPA (`symbolExtras.js`) |
| Línea | marcas a lo largo (traviesas, puntos, flechas...) | `GraphicStroke` + guiones | SPA |
| Línea | marcas al inicio y al final | `startPoint`/`endPoint` + `startAngle`/`endAngle` | SPA |
| Polígono | sin relleno; trama (7 dibujos) con o sin fondo | `GraphicFill` con `shape://` o círculos | SPA (`CanvasPattern`) |

**No se ofrece**, por no funcionar en GeoServer 2.28 o en el visor MVT (validado en la fase 0):

- Relleno con imagen (`GraphicFill` + `ExternalGraphic`): GeoServer no pinta nada, sin aviso en el log.
- Trama con rotación libre (sale cortada), `shape://dot` como trama (no pinta), relleno aleatorio y fuentes `ttf://`.
- Formas `qgis://` no validadas: un nombre desconocido **tumba la capa entera** en GeoServer. No añadir nada a
  `SHAPES` sin probarlo antes con `GetMap`.

## Cómo está hecho

```
editor (JS)  --options-->  symbol_options.normalize  -->  BD (options)
                                                         |
                    sld_builder --(options)--> symbol_sld.build_symbolizer --> SLD --> GeoServer (WMS, impresión)
                    mapbox_style_converter --(options)--> mapbox_symbol_converter --> estilo Mapbox + metadata
                                                                                      "gvsigol:symbol" --> SPA
```

| Pieza | Fichero | Qué hace |
|---|---|---|
| Esquema | `symbol_options.py` | Esquema v1, normalización estricta (lista blanca de formas, límites, colores), forma clásica equivalente |
| SLD | `symbol_sld.py` | Un simbolizador nuevo puede dar varios SLD (fondo + trama; trazo + marcas + extremos). El primero lleva la `VendorOption` `gvsigol-symbol` |
| Importación | `services._sld_import_symbolizers`, `services_library.upload_library` | Recuperan las opciones solo si al regenerar el SLD sale **idéntico**; si no, se importa como siempre |
| Guardado | `symbolizer_factory.py` | Normaliza las opciones; en las marcas guarda en `well_known_name` la forma clásica equivalente |
| Vista previa | `symbol_preview.py`, vista `symbol_preview/` | El SLD que se publica, pintado por GeoServer con las capas `preview:preview_*` |
| Conversor MVT | `plugin_featureapi/.../mapbox_symbol_converter.py` | Lo nativo en Mapbox; lo demás en `metadata["gvsigol:symbol"]` |
| Visor MVT | `gvsigol-frontend/apps/common/src/project/symbolExtras.js` | Pinta tramas, desplazamiento, marcas y extremos (OpenLayers) |
| Editor | `static/js/lib/symbology/SymbolOptionsEditor.js` y `*Symbolizer.js` | Pestañas, selectores visuales, vista previa grande |
| Predefinidos | `static/js/lib/symbology/SymbolPresets.js` | 33 símbolos (8 de punto, 15 de línea, 10 de polígono) |

Detalles que conviene conocer:

- **Orden de dibujo.** El SLD se genera de mayor a menor `order` (el de `order` 0 se pinta encima, como la fila de
  arriba del editor). La importación de SLD numera igual.
- **Vista previa.** La leyenda (`GetLegendGraphic`) se pide con la sesión del usuario. Las líneas con decoraciones se
  pintan con un `GetMap` sobre una línea quebrada y con las credenciales de servicio del servidor: solo sobre las
  capas técnicas `preview:preview_*`, por POST (el `SLD_BODY` con las cabeceras de la sesión supera el límite de Tomcat
  en GET) y con el `NamedLayer` cualificado (si no, GeoServer pinta el estilo guardado sin avisar).
- **Exportación de bibliotecas.** Si una biblioteca tiene símbolos avanzados se avisa y se ofrece «Exportar para
  versiones anteriores» (`library_export/<id>/?compat=1`), que genera SLD clásicos: las versiones anteriores de gvSIG
  Online leen los parámetros por posición y no saben importar los avanzados.

## Despliegue

1. Antes de migrar, comprobar que ninguna vista SQL usa las tablas de simbolizadores (si la hubiera, la migración
   fallaría sin aplicar nada):

   ```sql
   SELECT DISTINCT v.relname FROM pg_depend d JOIN pg_rewrite r ON r.oid = d.objid
   JOIN pg_class v ON v.oid = r.ev_class JOIN pg_class t ON t.oid = d.refobjid
   WHERE t.relname IN ('gvsigol_symbology_marksymbolizer', 'gvsigol_symbology_linesymbolizer',
                       'gvsigol_symbology_polygonsymbolizer') AND v.oid <> t.oid;
   ```

2. `python manage.py migrate gvsigol_symbology 0013` (añade `options` y pasa cinco columnas de entero a decimal).
3. Regenerar `gvsigol-compress.js` con `build/compress-js.cfg` (incluye `SymbolOptionsEditor.js` y `SymbolPresets.js`).
4. Desplegar `plugin_featureapi` (conversor, `CONVERTER_VERSION = 7`: las cachés de estilos Mapbox de versiones
   anteriores se regeneran solas) y el frontend (`symbolExtras.js`).
5. Opcional: `python manage.py symbology_symbolizer_stats` (solo lectura) para ver qué se usa en la instalación.

Las capas de vista previa `preview:preview_point/line/polygon` deben existir en GeoServer (las tablas las crea
`docker/gvsigol-postgis/conf/init.sql`; ningún script publica las capas).

## Tests

- Django: `python manage.py test gvsigol_symbology gvsigol_plugin_featureapi`. Los ficheros de referencia están en
  `test_golden/`; para regenerarlos tras un cambio intencionado, `SYMBOLOGY_UPDATE_GOLDEN=1` (y
  `FEATUREAPI_UPDATE_GOLDEN=1`), revisando el diff antes de subirlos.
- `test_golden/symbol_editor_output.json` y `symbol_presets_output.json` son la salida real del editor JS; si cambian
  los editores o los predefinidos hay que volver a capturarla.
- Frontend: `symbolExtras.test.js` y `symbolExtras.olms.test.js` en `apps/common` (el fixture
  `__fixtures__/symbolExtras.layers.json` es una copia de `plugin_featureapi/test_golden/newsym_*.json`).
- E2E: suite `symbology` de `gvsigol-e2e` (solo lectura).
