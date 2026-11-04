# Mejoras pendientes para completar la funcionalidad predictiva de GeoETL

Documento de planificación para el equipo de desarrollo y de producto. Parte del estado actual de la categoría **Predictivo** (ver `MANUAL_PREDICTIVO_RANDOM_FOREST.md`) y lista lo que falta para que la predicción sea una funcionalidad **completa**: reutilizable, aplicable a cualquier dato, medible, escalable y mantenible.

## 1. Estado actual (punto de partida)

**Ya implementado y probado**

| Área | Qué hay |
|---|---|
| Entrada | Ráster GeoTIFF desde el gestor de ficheros; alias de bandas |
| Preparación | Índices espectrales (NDVI, NDWI, NDBI, SAVI, EVI, brillo, diferencia normalizada) |
| Muestreo | Píxeles dentro de polígonos de muestra, reproyección, equilibrado por clase |
| Modelo | Random Forest (clasificación/regresión), parámetros principales, validación aleatoria / por polígono / por bloques |
| Informe | Exactitud, exactitud equilibrada, F1, kappa, métricas por clase, matriz de confusión (tabla), importancia |
| Predicción | Ráster clasificado/estimado + ráster de confianza o incertidumbre |
| Postproceso | Filtro de mayoría, tamaño mínimo de parche, vectorización |
| Salida | Publicación como capa (GeoServer/gvSIG) con estilo automático, reemplazo de capa existente |
| Calidad | 84 tests Django, 33 tests JS, traducción al español, YAML del asistente de IA |

**Qué impide considerarlo completo** (resumen de las carencias, detalladas en los apartados siguientes)

1. El modelo **no se puede guardar ni reutilizar**: cada ejecución reentrena.
2. El modelo **solo se aplica a ráster**; no a tablas ni capas vectoriales.
3. **Un solo algoritmo** y sin ajuste de parámetros.
4. La clasificación es **píxel a píxel**, sin tener en cuenta el contexto espacial.
5. Faltan **entradas y variables** habituales (varios ráster, capas vectoriales, multitemporal, textura, terreno).
6. Los **ráster grandes** tienen límites de memoria en algunos pasos.
7. **Ejecución síncrona** sin progreso ni cancelación; resultados de calidad no persistentes.
8. Aspectos de **interfaz, publicación, documentación e idiomas** por cerrar.

## 1 bis. Estado de implementación de las mejoras prioritarias (3 nov 2026)

Las nueve mejoras P1 están implementadas y probadas. Los cambios son **aditivos**: los valores por defecto y los puertos existentes no cambian, así que los flujos guardados antes siguen funcionando (hay una prueba de integración que ejecuta un canvas con el formato antiguo de puertos).

| Id | Estado | Qué se hizo | Lo que NO se hizo / matices |
|---|---|---|---|
| **A1** Modelos guardados | Hecho | Nodos *Guardar modelo* y *Modelo guardado*; almacenamiento versionado por usuario; firma HMAC de modelo y metadatos verificada antes de cargar; avisos de versión de scikit-learn; borrado desde el editor | La gestión es el diálogo del nodo, no una pantalla propia con comparación de modelos (E1). Compartir modelos entre usuarios es A3 (P2) y no está. |
| **A2** Predecir tabla | Hecho | Nodo *Predecir tabla*: conserva columnas, geometría y tipos; predicción y confianza; transacción única | Lee las variables de toda la tabla de una vez (adecuado hasta cientos de miles de filas). Sin probabilidades por clase (B1, P2). |
| **C1** Combinar ráster | Hecho | Nodo *Combinar ráster* (2-4 ráster), referencia = el primero, reproyección y remuestreo al vuelo, por bloques | Sin variables derivadas (C2, P2) ni nodo de detección de cambios (C3, P2). |
| **D1** Vectorización por bloques | Hecho | Vectorización por franjas con fusión exacta de costuras (equivalente a una sola pasada: probado), inserción por lotes en una transacción | El filtro de *tamaño mínimo de parche* sigue necesitando el ráster entero; se mantiene el límite (ahora configurable) y se recomienda la mayoría. Con conectividad 8, las esquinas exactas sobre una costura no se funden. |
| **D2** Rendimiento y límites | Hecho | Límites configurables, submuestreo con aviso, comprobación de espacio en disco, procesos configurables, medidas con ráster de 36 M px | **No** se escribe en COG con vistas reducidas. **No** se ha medido en el servidor de producción (solo en desarrollo). |
| **E2** Evaluación independiente | Hecho | Nodo *Evaluar clasificación* (polígonos y puntos): exactitud, kappa, exactitud del usuario y del productor, matriz | Sin estimación de áreas con intervalo de confianza (E3, P3). |
| **F1** Publicación | Hecho | Estilo al reemplazar (auto/siempre/nunca), colores estables por clase, banda a publicar, rampa fija, descripción de la capa | No hay opción de no subir el ráster al GeoServer con almacenamiento compartido (depende de la infraestructura). El error `'list' object has no attribute 'cursor'` al borrar workspaces con almacenes ráster está en el repositorio `gvsigol/` y **no se ha tocado**. |
| **G3** Calidad | Parcial | Pruebas de integración con BD y con GeoServer (activables), pruebas de paridad editor/servidor, prueba del canvas con formato antiguo | **No** hay pruebas de navegador extremo a extremo, ni integración en CI, ni revisión de seguridad formal. |
| **G2** Documentación y datos de ejemplo (P2, adelantado) | Hecho en gran parte | Datos de ejemplo reproducibles en `ejemplos/` (ortofoto, terreno, muestras de entrenamiento y validación, zonas, puntos, parcelas de campo y la superficie real) y manual reescrito con tutorial y 8 casos de uso con resultados verificados | Falta integrarlo en el manual general de gvSIG Online y la guía de arquitectura interna para quien mantenga el plugin. |
| **G4** Empaquetado | Preparado | Lista de comprobación (abajo) | La reconstrucción de la imagen y el control de versiones los hace el equipo (ver abajo). |

**Organización de la paleta (4 nov 2026).** Las operaciones con imágenes que no dependen de un modelo se han movido a una categoría propia, **Ráster** (botón, cabecera de nodo y puertos ráster en rosa frambuesa): *Recortar ráster*, *Combinar ráster*, *Índice espectral*, *Limpiar ráster* y *Ráster a polígonos*. *Predictivo* conserva *Muestrear ráster*, *Random Forest*, *Predecir ráster*, *Predecir tabla* y *Evaluar clasificación*. Solo cambia la agrupación en la paleta y el color de cabecera: los tipos de nodo son los mismos, así que los flujos guardados siguen funcionando.

**Revisión de rigor científico (4 nov 2026).** Se corrigieron y documentaron los puntos de una revisión metodológica:
- *Índice espectral*: conversión a reflectancia con escala **y offset** (Sentinel-2 L2A desde 2022, Landsat Colección 2) aplicada a todos los índices; EVI fuera de [−1, 1] como sin dato; advertencia de que las ortofotos no son reflectancia calibrada.
- *Random Forest*: en regresión se prueban p/3 variables por división (Breiman, 2001) en lugar de todas (antes era *bagging*); parámetro *Variables por división*; validación **automática** por defecto (por polígonos cuando la tabla lo permite); importancia **por permutación** sobre los datos de evaluación.
- *Evaluar clasificación*: intervalos del 95 % por *bootstrap* de muestras enteras.
- Nodos nuevos **Muestreo estratificado** y **Estimar superficies** (estimador de Olofsson et al., 2014, que reproduce su ejemplo resuelto). Esto cubre la mejora E3 (antes P3).
- Textos: "Confianza" pasa a "Seguridad" (no es una probabilidad calibrada), kappa desaconsejado, límites de la incertidumbre en regresión y del recuento de píxeles; sección de fundamentos y bibliografía en el manual.
- **Cambia resultados** de los flujos de regresión existentes (por el p/3); la clasificación no cambia. La validación por defecto solo cambia en nodos nuevos.

### Lista de comprobación para el despliegue (G4)

1. **Control de versiones (SVN).** `svn add` de los ficheros nuevos del plugin: `etl_models.py`, `etl_raster.py`, `etl_raster_publish.py`, `static/js/PredictiveShapes.js`, los YAML de `assistant/nodes/` (los de los nodos predictivos), `tests/test_raster_nodes.py`, `tests/test_models.py`, `tests/test_raster_integration.py`, `tests/test_raster_engine.py`, `tests/js/`, los dos manuales `.md` y la carpeta `ejemplos/` (script generador, `LEEME.md`, datos y el zip). Cambios modificados: `settings.py`, `tasks.py`, `etl_tasks.py`, `views.py`, `urls.py`, `templates/etl.html`, `static/css/style_etl.css`, traducciones y tests existentes. En `gvsigol/`: `requirements-django4.txt` (scikit-learn).
2. **Imagen oficial del backend.** Reconstruir con `docker/gvsigol-back/build.sh` tras confirmar el punto anterior, para que scikit-learn esté en la imagen (hoy lo está solo por una capa local de desarrollo).
3. **Permisos de directorios.** Los procesos de Celery corren como `www-data`. Los modelos se guardan por defecto en `<gestor de ficheros>/.geoetl_models` (que `www-data` puede escribir y es persistente). Si se cambia `ETL_MODELS_DIR`, esa ruta debe ser escribible por `www-data` y estar en un volumen persistente. No hace falta tocar el `docker-compose` con la ruta por defecto.
4. **Variables de entorno** (opcionales; ver el manual, apartado *Límites configurables*): `ETL_RASTER_MAX_PIXELS`, `ETL_RASTER_MAX_TRAIN_ROWS`, `ETL_RASTER_N_JOBS`, `ETL_RASTER_POLYGONIZE_STRIP_PIXELS`, `ETL_RASTER_SIEVE_MAX_PIXELS`, `ETL_RASTER_MIN_FREE_MB`, `ETL_MODELS_DIR`, `ETL_MODELS_KEEP_VERSIONS`, `ETL_MODELS_SIGNING_KEY`. Para que los modelos sobrevivan a un cambio de `SECRET_KEY`, fijar `ETL_MODELS_SIGNING_KEY`.
5. **Reiniciar** los servicios Celery (`celery`, `celerybeat`) y el backend tras actualizar; **Ctrl+F5** en el editor.
6. **Pruebas de humo posteriores al despliegue.** Dentro del contenedor: `python manage.py test gvsigol_plugin_geoetl.tests` (sin servicios externos, unos 15 s) y, en un entorno de pruebas, con `GEOETL_INTEGRATION=1` y `GEOETL_INTEGRATION_GEOSERVER=1` las de integración (crean y borran tablas `zzit_*` y un workspace `zz_it_ws`). Y de forma manual: ejecutar un flujo de clasificación, guardar el modelo, reutilizarlo con *Modelo guardado* y publicar con *Reemplazar*.
7. **Medir** en el servidor de producción con un ráster real antes de fijar los límites (D2).

---

## 2. Cómo leer este documento

- **Prioridad:** **P1** imprescindible para considerarlo completo; **P2** muy recomendable; **P3** deseable.
- **Esfuerzo** (orientativo, para una persona conocedora del plugin): **S** ≤ 2 días, **M** 3–7 días, **L** 1–3 semanas, **XL** > 3 semanas.
- **Impacto cruzado** indica si afecta a otros repositorios o al despliegue (este plugin vive en su propio repositorio SVN; los cambios en `gvsigol/`, `docker/` o el frontend se avisan aparte).
- Cada mejora lleva sus **criterios de aceptación** comprobables.

## 3. Resumen y hoja de ruta propuesta

| Id | Mejora | Prioridad | Esfuerzo |
|---|---|---|---|
| A1 | Guardar y reutilizar modelos | P1 | L |
| A2 | Aplicar el modelo a tablas y capas vectoriales | P1 | M |
| A3 | Compartir modelos y permisos | P2 | M |
| B1 | Probabilidades por clase | P2 | M |
| B2 | Selección y evaluación de variables | P2 | M |
| B3 | Ajuste automático de hiperparámetros | P2 | M |
| B4 | Más algoritmos y clasificación no supervisada | P3 | L |
| B5 | Control del equilibrado de clases y de los umbrales | P2 | S |
| C1 | Varios ráster como entrada (apilado y remuestreo) | P1 | M |
| C2 | Variables derivadas: textura, terreno, distancia a capas vectoriales | P2 | L |
| C3 | Clasificación multitemporal y detección de cambios | P2 | L |
| C4 | Clasificación por objetos (segmentación) | P3 | XL |
| D1 | Vectorización y filtrado por bloques (ráster grandes) | P1 | M |
| D2 | Rendimiento y límites documentados | P1 | M |
| D3 | Ejecución en segundo plano con progreso y cancelación | P2 | L |
| E1 | Conservar y consultar los informes de calidad | P2 | M |
| E2 | Evaluación con muestras de validación independientes | P1 | S |
| E3 | Estimación de áreas con intervalo de confianza | P3 | M |
| F1 | Estilo al reemplazar capas y otras opciones de publicación | P1 | S |
| F2 | Ayuda de muestras: dibujo y revisión | P2 | L |
| F3 | Experiencia de usuario del editor | P2 | M |
| G1 | Idiomas restantes | P2 | S |
| G2 | Documentación y datos de ejemplo | P2 | S |
| G3 | Calidad, seguridad y mantenimiento | P1 | M |
| G4 | Empaquetado y despliegue | P1 | S |

**Secuencia recomendada**

1. **Cierre de lo básico (P1):** A1, A2, C1, D1, D2, E2, F1, G3, G4. Con esto la funcionalidad es utilizable en producción con ráster reales y de forma repetible.
2. **Madurez (P2):** A3, B1, B2, B5, E1, D3, F2, F3, G1, G2, C2, C3, B3.
3. **Ampliación (P3):** B4, C4, E3.

---

## 4. Bloque A: modelos reutilizables

### A1. Guardar y reutilizar modelos — P1, L

**Problema.** El modelo vive solo durante la ejecución y se borra al terminar. Para clasificar otra imagen (otra zona o fecha) hay que reentrenar con las mismas muestras. Tampoco se pueden comparar versiones ni auditar qué modelo produjo un mapa.

**Propuesta**

Dos nodos nuevos:

| Nodo | Entradas / salidas | Parámetros |
|---|---|---|
| **Guardar modelo** (*Save Model*) | Entrada: Modelo | Nombre; descripción; si existe: reemplazar / crear versión nueva / fallar |
| **Modelo guardado** (*Saved Model*) | Salida: Modelo | Selector del modelo (con su resumen: tipo, clases, bandas, fecha, exactitud, versión) |

El modelo guardado se conecta a **Predecir ráster** igual que la salida *Modelo* de Random Forest. Así se separa **entrenar** (se ejecuta ocasionalmente) de **aplicar** (se ejecuta cada vez que llega una imagen).

**Diseño**

- **Almacenamiento:** directorio persistente propio, fuera del directorio temporal que se purga (por ejemplo, una subcarpeta bajo el almacenamiento de datos del servidor), con un fichero de modelo y otro de metadatos por versión. Alternativa a valorar: tabla de base de datos con el binario y los metadatos, que simplifica copias de seguridad.
- **Metadatos:** nombre, versión, propietario, fecha, tipo de problema, clases y su orden, variables y su orden, parámetros del modelo, métricas de validación, número de muestras, versiones de scikit-learn y numpy, huella (hash) del fichero.
- **Seguridad (obligatoria).** Un fichero de modelo es un *pickle*: cargar uno manipulado ejecuta código arbitrario. Por tanto:
  - Firmar cada modelo al guardarlo (HMAC con una clave del servidor) y **verificar la firma antes de cargarlo**; rechazar cualquier fichero sin firma válida.
  - Validar nombres y rutas (sin separadores de ruta ni enlaces simbólicos fuera del directorio de modelos).
  - No cargar nunca modelos subidos a través del gestor de ficheros.
  - Valorar un formato sin ejecución de código (por ejemplo, exportar los árboles a un formato propio o a ONNX) si el riesgo se considera inaceptable.
- **Compatibilidad:** al cargar, comparar las versiones de scikit-learn/numpy con las guardadas. Si difieren, avisar con claridad (*"Este modelo se entrenó con scikit-learn X; reentrénalo"*) y no fallar con un error técnico.
- **Validaciones en Predecir ráster:** que las bandas coincidan en nombre (ya existe), que el modelo sea del tipo esperado y, opcionalmente, avisar si los valores del ráster se salen del rango de entrenamiento (posible escala radiométrica distinta).
- **Gestión:** pantalla o diálogo para listar, ver detalle, renombrar, borrar y descargar metadatos de los modelos. Endpoint de listado con el mismo estilo que los existentes.
- **Ciclo de vida:** el barrido por antigüedad de artefactos **no** debe tocar los modelos guardados.

**Criterios de aceptación**

- Guardar un modelo, reiniciar el servidor, cargarlo y predecir da **exactamente** el mismo ráster que el modelo en memoria.
- Un fichero de modelo modificado o sin firma es rechazado con un mensaje claro y **sin ejecutar** su contenido.
- Un modelo guardado con otra versión de scikit-learn produce un aviso comprensible.
- Un flujo "Modelo guardado → Predecir ráster → Publicar" funciona sin ningún nodo de entrenamiento.
- Los modelos sobreviven a la purga periódica de temporales.

**Impacto cruzado.** Requiere definir la ubicación persistente en la configuración del plugin y que esa ruta esté montada como volumen en el despliegue (`docker/`), para no perderla al recrear el contenedor.

### A2. Aplicar el modelo a tablas y capas vectoriales — P1, M

**Problema.** Random Forest acepta cualquier tabla para entrenar, pero **solo se puede aplicar a ráster**. Casos como "predecir la idoneidad de cada parcela", "estimar el riesgo de cada tramo" o "clasificar cada punto de inventario" no tienen salida.

**Propuesta.** Nodo **Predecir tabla** (*Predict Table*): entradas Datos (tabla) y Modelo; salida Tabla con las columnas originales más `prediction` y, en clasificación, `confidence` (probabilidad de la clase elegida).

- Comprobación de columnas: mismos nombres que las variables del modelo; error claro con las que faltan.
- Respetar la geometría y el resto de columnas, de modo que el resultado se pueda publicar o combinar con otros nodos.
- Opción de añadir una columna por cada clase con su probabilidad (ver B1).
- Esquema de salida conocido en el editor (`prediction`, `confidence`), para que los nodos siguientes lo usen.

**Criterios de aceptación**

- Un flujo "Tabla de entrenamiento → Random Forest → Predecir tabla (sobre otra tabla)" produce las columnas esperadas.
- Los valores nulos o no numéricos en las variables se tratan sin romper la ejecución (la fila queda sin predicción y con un motivo).
- Con datos de prueba, el resultado coincide con el de aplicar el modelo directamente en Python.

### A3. Compartir modelos y permisos — P2, M

- Modelos **privados** por defecto, con opción de compartirlos con roles o grupos, siguiendo el mismo esquema de permisos que el resto del plugin.
- Registro de quién entrenó y quién usó cada modelo.
- Impedir que un usuario cargue o borre modelos de otro sin permiso.

---

## 5. Bloque B: modelado

### B1. Probabilidades por clase — P2, M

**Problema.** Hoy solo se obtiene la probabilidad de la clase ganadora. Para análisis de idoneidad o para fijar umbrales hace falta la probabilidad de **cada** clase.

**Propuesta**

- En **Predecir ráster**, opción *"Generar una banda de probabilidad por clase"*: ráster multibanda (una banda por clase, 0–1), con las bandas nombradas con la clase.
- En **Predecir tabla** (A2), una columna `prob_<clase>` por clase.
- Opción de **umbral de decisión** (por ejemplo, "clasificar como vegetación solo si la probabilidad es ≥ 0,7; si no, sin dato / clase 'dudoso'"). Útil cuando el coste de un falso positivo es alto.
- **Publicar ráster** debe poder publicar una sola banda de probabilidad con rampa 0–1 (hoy publica el ráster completo con el estilo de banda 1).

**Criterios de aceptación**

- La suma de las bandas de probabilidad es 1 en cada píxel válido.
- El umbral convierte en "dudoso" exactamente los píxeles con probabilidad máxima por debajo de él.

### B2. Selección y evaluación de variables — P2, M

- **Importancia por permutación** (más fiable que la importancia por defecto, que favorece variables con muchos valores distintos), calculada sobre los datos de validación y añadida al informe.
- **Eliminación recursiva** opcional de variables poco útiles, con informe de cuántas se conservan y con qué efecto sobre la calidad.
- **Aviso de variables muy correlacionadas** (por ejemplo, rojo y verde casi idénticas), con la matriz de correlación en el informe.
- Informe de **cobertura de entrenamiento**: porcentaje del ráster a predecir cuyos valores caen dentro del rango visto al entrenar (*área de aplicabilidad*).

### B3. Ajuste automático de hiperparámetros — P2, M

- Modo **"Optimizar parámetros"** en Random Forest, que prueba combinaciones (número de árboles, profundidad, mínimo por hoja, número de variables por división) mediante **validación espacial** y se queda con la mejor.
- Límite de tiempo configurable y informe de las combinaciones probadas.
- Por defecto desactivado: el comportamiento actual no cambia.

**Cuidado:** el ajuste debe hacerse con la misma validación por polígonos/bloques; ajustar con validación aleatoria premia el sobreajuste.

### B4. Más algoritmos y clasificación no supervisada — P3, L

Las bibliotecas ya instaladas permiten ofrecer, con el mismo flujo de nodos:

- **Gradient Boosting** (boosting de árboles) y **Regresión logística** como alternativas comparables.
- **K-means** (y similares) como clasificación **no supervisada** de ráster, sin muestras, útil para una primera exploración.

Planteamiento recomendado: un parámetro **Algoritmo** en el nodo de entrenamiento (en lugar de un nodo por algoritmo) y un nodo **Agrupar ráster** para la no supervisada. Nombrar con generalidad ("Entrenar modelo") exigiría revisar nombres, traducciones y el asistente de IA.

### B5. Control del equilibrado de clases y de los umbrales — P2, S

Hoy las clases desequilibradas se compensan siempre con el peso `balanced`. Exponerlo como opción avanzada:

- **Equilibrado de clases:** automático (actual) / ninguno / personalizado por clase.
- **Prioridades por clase**, para casos donde omitir una clase cuesta más que confundirla.
- Mostrar en el informe qué pesos se aplicaron.

---

## 6. Bloque C: datos de entrada y variables

### C1. Varios ráster como entrada — P1, M

**Problema.** Todas las bandas deben venir en un único GeoTIFF. Es habitual tener la ortofoto RGB, el infrarrojo y un modelo digital del terreno en ficheros distintos, con distintas resoluciones.

**Propuesta.** Nodo **Combinar ráster** (*Stack Rasters*): entradas ráster (varias), salida un ráster multibanda.

- **Referencia de resolución y extensión:** elegir qué ráster manda; los demás se **remuestrean** (vecino más próximo o bilineal; en capas categóricas, vecino más próximo).
- **Reproyección** automática al sistema del ráster de referencia.
- **Nombres de banda** con prefijo opcional por ráster, para evitar colisiones.
- Tratamiento del **solape parcial**: píxeles fuera de alguno de los ráster quedan sin dato.
- Procesamiento **por bloques** para no cargar todo en memoria.

**Criterios de aceptación**

- Combinar un ráster RGB y un MDT de otra resolución produce un ráster alineado, y los nombres de banda se propagan al editor.
- Los píxeles sin cobertura de alguna capa quedan como sin dato.

### C2. Variables derivadas — P2, L

Nodos o presets que añaden bandas calculadas:

- **Textura** (desviación típica o entropía en ventana, contraste GLCM): clave para distinguir tipos de vegetación con respuesta espectral parecida.
- **Terreno** a partir de un MDT: pendiente, orientación, curvatura, rugosidad.
- **Distancia a una capa vectorial** (cauces, carreteras, edificios) como variable.
- **Variables de zona**: valor de un ráster agregado en una ventana o en polígonos.
- Más **índices espectrales** (ampliables): NDMI, NBR, MSAVI, índices de Sentinel-2 y de Landsat.

Se recomienda definir los presets en un único lugar de la configuración (hoy están repartidos entre la lógica del servidor y la definición del nodo en el editor; mantenerlos sincronizados a mano es frágil).

### C3. Clasificación multitemporal y detección de cambios — P2, L

- **Apilar fechas** con C1 (cada fecha con prefijo) y clasificar el conjunto: ya posible cuando exista C1, pero conviene documentarlo con un ejemplo.
- Nodo **Detectar cambios** (*Change Detection*): entre dos clasificaciones, produce un ráster con las transiciones (*de vegetación a suelo*, etc.) y una **matriz de transición** con las superficies por par de clases.
- Cálculo de superficies de transición por zona (con los nodos existentes de intersección y agregación).

### C4. Clasificación por objetos (segmentación) — P3, XL

La clasificación píxel a píxel produce ruido que hoy se corrige con el filtro de mayoría. Una alternativa de mayor calidad es:

1. **Segmentar** la imagen en objetos homogéneos.
2. Calcular estadísticas por objeto (media, desviación, forma).
3. Clasificar los **objetos** en lugar de los píxeles.

Es un desarrollo grande que añade dependencias (algoritmos de segmentación) y un nuevo flujo; valorar solo si los clientes requieren calidad cartográfica superior a la que da el postproceso.

---

## 7. Bloque D: escala y rendimiento

### D1. Vectorización y filtros por bloques — P1, M

**Problema.** **Ráster a polígonos** y **Tamaño mínimo de parche** leen la banda entera en memoria. Con ráster de cientos de millones de píxeles agotarán la memoria del servidor.

**Propuesta**

- Vectorizar **por bloques** con un margen, y **fusionar** después los polígonos que se cortan en los bordes de bloque (unión por clase a lo largo de las costuras).
- Sustituir el filtrado de parches por una versión **por bloques con reconciliación de bordes** (etiquetado de componentes conectadas por bloques y unión global), o en su defecto mantener el límite actual pero documentarlo y exponerlo en la configuración.
- Escritura de polígonos **por lotes** a la base de datos para no acumularlos todos en memoria.

**Criterios de aceptación**

- El resultado de vectorizar por bloques es **geométricamente equivalente** al de hacerlo de una vez (mismos polígonos tras fusionar).
- Un ráster de 1 000 millones de píxeles se vectoriza sin superar un límite de memoria fijado.

### D2. Rendimiento y límites documentados — P1, M

- **Medir** en un conjunto de ráster reales de distintos tamaños (100 MB, 500 MB, 2 GB): tiempo y memoria de cada nodo, en el entorno de producción, no solo en desarrollo.
- Establecer **límites configurables** (píxeles máximos, muestras máximas, tamaño del modelo) con mensajes comprensibles al superarlos.
- **Submuestreo** automático de las muestras con aviso cuando haya demasiados píxeles de entrenamiento.
- **Escritura de GeoTIFF en formato COG** (con vistas reducidas) para que la publicación sea más rápida en visores.
- **Número de procesos** configurable para el entrenamiento, de modo que un ETL no acapare todos los núcleos del servidor.
- Comprobar el **espacio en disco** del directorio de temporales antes de empezar y avisar si no hay suficiente.

### D3. Ejecución en segundo plano con progreso y cancelación — P2, L

- Mostrar en el estado de la ejecución **qué nodo se está ejecutando y el avance** de los pasos largos (predicción por bloques, validación por rondas).
- Posibilidad de **cancelar** una ejecución en curso sin dejar temporales ni capas a medias.
- **Tiempo máximo** configurable por nodo.
- Registro en el log de métricas de tiempo por nodo.

---

## 8. Bloque E: calidad y evaluación

### E1. Conservar y consultar los informes de calidad — P2, M

Hoy el informe y la matriz de confusión son tablas temporales que se borran al terminar, salvo que el usuario las conecte a una salida. Propuesta:

- Guardar automáticamente, junto al modelo (A1), el informe completo y la matriz.
- Pantalla para **consultar y comparar** modelos: métricas, matriz, importancia, parámetros y muestras usadas.
- Exportar el informe a **CSV/PDF** para entregarlo al cliente.
- Gráficos en la propia pantalla: matriz como mapa de calor, importancia en barras, evolución por rondas.

### E2. Evaluación con muestras de validación independientes — P1, S

**Problema.** La validación cruzada estima la calidad, pero el estándar en teledetección es evaluar con **muestras de validación independientes**, tomadas por separado de las de entrenamiento y, si es posible, con un diseño estadístico.

**Propuesta.** Nodo **Evaluar clasificación** (*Assess Classification*): entradas un ráster clasificado y una tabla de **muestras de validación** (polígonos o puntos con la clase real). Salidas: matriz de confusión, exactitud global, kappa, **exactitud del productor y del usuario** por clase, y la tabla de errores.

- Permite medir el resultado **final**, incluido el postproceso (filtro de mayoría), que la validación del entrenamiento no ve.
- Compatible con el flujo actual: las muestras de validación vienen de otra entrada.

### E3. Estimación de áreas con intervalo de confianza — P3, M

Cuando el objetivo es **cuantificar superficies** (como en el caso de la formación vegetal por cauces), contar los píxeles de cada clase tiene sesgo por los errores de clasificación. El método estándar corrige el área con la matriz de confusión y da un **intervalo de confianza**. Se propone un nodo que reciba la clasificación y la matriz y devuelva la superficie corregida de cada clase con su incertidumbre.

---

## 9. Bloque F: publicación e interfaz

### F1. Estilo al reemplazar capas y otras opciones de publicación — P1, S

**Problema conocido.** Al reemplazar el ráster de una capa existente, **el estilo no se regenera**. Si cambian las clases del modelo, los colores pueden quedar desalineados.

**Propuesta**

- Opción **"Actualizar el estilo"** al reemplazar (por defecto activada si las clases han cambiado, con aviso de que se pierde el estilo manual).
- **Estilo coherente entre ejecuciones:** que una misma clase conserve siempre el mismo color aunque cambie el orden o el número de clases (color asociado al nombre de la clase, no a su posición).
- Opción de **ráster continuo** con elección de rampa de color y de rango (por ejemplo, ver la confianza de 0,5 a 1).
- Elegir qué **banda** publicar de un ráster multibanda.
- Rellenar **resumen y metadatos** de la capa (modelo usado, fecha, métricas).
- Opción de **no cargar el ráster completo** al GeoServer cuando exista un almacenamiento compartido.
- Corregir el error de borrado de espacios de trabajo con almacenes ráster que registra el gestor (`'list' object has no attribute 'cursor'`), de origen anterior a esta funcionalidad pero que aparece al limpiar capas ráster publicadas desde el ETL. Este arreglo está en el repositorio `gvsigol/` y requiere coordinación.

### F2. Ayuda para crear y revisar las muestras — P2, L

La calidad del resultado depende de las muestras, pero hoy hay que prepararlas fuera.

- Nodo o herramienta para **generar muestras de ejemplo** (aleatorias o estratificadas) a partir de una clasificación previa o de un mapa de referencia, para acelerar el etiquetado.
- **Revisión de muestras**: informe previo con el número de polígonos y píxeles por clase, detección de **polígonos que se solapan con clases distintas**, polígonos fuera del ráster y clases con pocas muestras.
- **Detección de valores atípicos**: píxeles de muestra muy distintos al resto de su clase (sombras, nubes, errores de etiquetado), con la opción de excluirlos.
- A más largo plazo, un flujo de **dibujo de muestras sobre la imagen** integrado en el visor.

### F3. Experiencia de usuario del editor — P2, M

- **Vista previa** de la clasificación en una zona reducida antes de ejecutar el flujo completo.
- **Plantillas de flujo** (clasificación de cobertura, detección de una especie, regresión) que crean los nodos ya conectados.
- **Ayuda contextual** en cada campo y enlace al manual.
- Mostrar las columnas `pred_*` de la matriz de confusión al conocerse las clases (hoy el editor solo ofrece las columnas fijas).
- **Resumen del resultado** al terminar (exactitud, clases, número de polígonos) visible en el panel de ejecución, no solo en el log.
- Revisar la **accesibilidad** (contraste, teclado) de los diálogos nuevos.

---

## 10. Bloque G: calidad, idiomas, documentación y despliegue

### G1. Idiomas restantes — P2, S

Solo está traducido el **español**. Faltan catalán, catalán valenciano, alemán, euskera, portugués y portugués de Brasil. Ya existe la lista de cadenas; el trabajo es la traducción y la compilación de los catálogos. Conviene una revisión por hablantes nativos, especialmente de la terminología de teledetección.

### G2. Documentación y datos de ejemplo — P2, S

- Manual de usuario dentro del manual general de gvSIG Online (el actual es un documento aparte).
- **Conjunto de datos de ejemplo** público (ortofoto, muestras y resultado esperado) y una **guía de prueba paso a paso**, para formación y para pruebas de aceptación.
- Guía de **buenas prácticas de muestreo** más extensa, con ejemplos de errores típicos.
- Documentar la **arquitectura interna** para quien mantenga el plugin (cómo se añade un nodo, el contrato con el motor, los tipos de puerto).

### G3. Calidad, seguridad y mantenimiento — P1, M

- **Pruebas de integración automatizadas** del flujo completo con el motor de ejecución (hoy se hacen con scripts manuales): entrenar, predecir, publicar y limpiar, con un GeoServer de pruebas.
- **Pruebas en el navegador** (extremo a extremo) del editor, además de las actuales en jsdom, que no dibujan el lienzo real.
- Ejecutar las pruebas del plugin en la **integración continua** del proyecto.
- **Pruebas de carga** (D2) como parte de la entrega.
- **Revisión de seguridad** de las rutas de fichero, de los permisos y, sobre todo, de la carga de modelos (A1).
- Eliminar la **duplicación entre la lógica del servidor y la del editor** (nombres de banda normalizados, listas de índices) generando una a partir de la otra o añadiendo una prueba que las compare.
- Confirmar el **comportamiento con flujos antiguos**: abrir y ejecutar workspaces guardados antes de los cambios de puertos (los nodos Random Forest y Predecir ráster han ganado salidas).
- Política de **retirada de dependencias**: fijar versiones de scikit-learn, numpy y rasterio y comprobar compatibilidad al actualizarlas.

### G4. Empaquetado y despliegue — P1, S

- Reconstruir la imagen oficial del backend con `docker/gvsigol-back/build.sh` (opción A) para que **scikit-learn quede en la imagen oficial** (hoy se instaló como una capa local de desarrollo). Requiere antes confirmar en SVN `requirements-django4.txt` (repositorio `gvsigol/`) y el plugin.
- Añadir al control de versiones los ficheros nuevos del plugin (módulos, definiciones del asistente, pruebas) y los cambios de traducciones.
- Verificar que el directorio de **artefactos temporales** es escribible por el usuario con el que corren los procesos del ETL y está dimensionado para varias copias de un ráster.
- Si se implementa A1: volumen persistente para los modelos (impacto en `docker/`).
- Documentar la necesidad de **reiniciar los servicios de Celery** tras actualizar el plugin, o automatizarlo en el despliegue.
- Incluir las pruebas de humo (A1, A2, publicación) en la lista de comprobación posterior al despliegue.

---

## 11. Riesgos y consideraciones transversales

| Riesgo | Mitigación |
|---|---|
| **Carga de modelos como vector de ataque** (A1) | Firma y verificación obligatorias; revisión de seguridad; evaluar un formato sin ejecución de código. |
| **Consumo de memoria/CPU del servidor** con ráster grandes (D1, D2) | Procesamiento por bloques, límites configurables, número de procesos limitado, pruebas de carga. |
| **Resultados presentados como más fiables de lo que son** | Validación espacial por defecto en los flujos de ráster, evaluación independiente (E2), mapa de confianza, avisos de área de aplicabilidad (B2). |
| **Deriva entre servidor y editor** (listas de índices, normalización de nombres) | Fuente única o pruebas de consistencia (G3). |
| **Cambios de puertos en los nodos** rompen flujos guardados | Añadir salidas solo al final; probar con workspaces antiguos; evitar renombrar o reordenar puertos. |
| **Dependencias del sistema** (GeoServer, almacenamiento compartido) | Probar en el entorno objetivo antes de dar por cerrada cada mejora de publicación. |
| **Alcance** (C4, B4) | Tratarlas como proyectos separados con decisión explícita de negocio. |

## 12. Decisiones que necesitan respuesta antes de empezar

1. **¿Dónde se guardan los modelos** (A1): ¿ficheros en un volumen persistente o base de datos? ¿Y qué política de retención (número de versiones, caducidad)?
2. **¿Los modelos se comparten** (A3) entre usuarios del mismo rol/grupo, o son siempre privados?
3. **¿Prioridad del caso vectorial** (A2) frente a los casos solo ráster? Determina si A2 va antes que C1.
4. **¿Hay ráster reales de mayor tamaño** (más de 1 000 millones de píxeles) en el uso previsto? Si es así, D1 pasa a ser bloqueante.
5. **¿Se necesita cuantificación de superficies con rigor estadístico** (E3) o basta el recuento de píxeles?
6. **Idiomas obligatorios** para la próxima entrega (G1).
7. **¿Se va a ofrecer más de un algoritmo** (B4)? Cambia el nombre y la estructura de los nodos, así que conviene decidirlo antes de ampliar el catálogo.

## 13. Criterio global de "funcionalidad completa"

Se considerará completa cuando, como mínimo:

- Un modelo entrenado se **guarda, se versiona y se reutiliza** sobre otra imagen sin reentrenar (A1).
- El modelo se aplica tanto a **ráster como a tablas/capas vectoriales** (A2).
- Se pueden usar **varios ráster** como origen de variables (C1).
- Los ráster de **varios cientos de MB a unos pocos GB** se procesan de principio a fin sin agotar memoria, con límites y avisos claros (D1, D2).
- La calidad se mide con **validación espacial y con muestras independientes**, y los informes se conservan (E1, E2).
- La publicación **mantiene estilos coherentes** entre ejecuciones (F1).
- Hay **pruebas automáticas de integración**, documentación de usuario y traducciones a los idiomas del producto (G1–G3).
- La **imagen oficial del backend** incluye las dependencias necesarias (G4).
