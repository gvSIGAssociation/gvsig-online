# Datos de ejemplo de los nodos predictivos

Escena **sintética** (inventada) de 300 × 300 m con un barranco sinuoso: agua en el cauce, vegetación a ambos lados y suelo en el resto, más cuatro manchas de vegetación aisladas lejos del cauce. Sistema de coordenadas **EPSG:25830** (ETRS89 / UTM 30N), píxel de 1 m. Las clases se parecen entre sí a propósito (ruido), como en una imagen real, para que los resultados no sean perfectos.

Sirven para seguir los casos de uso del manual (`../MANUAL_PREDICTIVO_RANDOM_FOREST.md`). Hay que **subirlos al gestor de ficheros** de gvSIG Online (todos los ficheros de cada shapefile: `.shp`, `.shx`, `.dbf`, `.prj` y `.cpg`).

Carpeta `clasificacion_barranco/` (o el zip `datos_ejemplo_barranco.zip`):

| Fichero | Contenido |
|---|---|
| `ortofoto.tif` | Imagen de 3 bandas de 8 bits: **Rojo, Verde, Infrarrojo**. 300 × 300 píxeles de 1 m. |
| `terreno.tif` | Modelo del terreno de 1 banda (**Altura**, en metros) con **píxel de 2 m** (150 × 150): otra resolución, para practicar *Combinar ráster*. |
| `muestras_entrenamiento.shp` | 14 polígonos de entrenamiento (5 suelo, 5 vegetación, 4 agua) con la columna `clase` (`suelo`, `vegetacion`, `agua`). |
| `muestras_validacion.shp` | 11 polígonos **distintos** de los anteriores (4 suelo, 4 vegetación, 3 agua) para evaluar con muestras independientes. Misma columna `clase`. |
| `tramos_barranco.shp` | 3 polígonos (`Tramo 1`, `Tramo 2`, `Tramo 3`, columna `tramo`), cada uno un tercio de la escena, para calcular superficies por zona. |
| `puntos_inventario.shp` | 160 puntos con los valores de la imagen (`rojo`, `verde`, `infrarrojo`) y su `clase` conocida. Para **entrenar con una tabla**. |
| `puntos_nuevos.shp` | 40 puntos con los mismos valores y sin `clase` (la real está en `clase_real`, solo para comprobar). Para **predecir una tabla**. |
| `parcelas_campo.shp` | 45 parcelas de 5 × 5 m con la **biomasa medida** (`biomasa`, en kg/m²). Para **regresión**. |
| `verdad_de_terreno.json` | La superficie real de cada clase, total y por tramo, para comparar con los resultados. |

## Superficie real (la "verdad" de la escena)

| | Suelo | Vegetación | Agua |
|---|---:|---:|---:|
| **Total** | 65 217 m² | 21 784 m² | 2 999 m² |
| Tramo 1 | 21 039 m² | 7 962 m² | 999 m² |
| Tramo 2 | 22 400 m² | 6 600 m² | 1 000 m² |
| Tramo 3 | 21 778 m² | 7 222 m² | 1 000 m² |

## Regenerar los datos

`python generar_datos_ejemplo.py [carpeta_de_salida]` (necesita numpy, scipy, rasterio y geopandas, que ya están en el backend). Es reproducible: siempre produce los mismos ficheros.
