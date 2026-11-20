# Manual de los nodos predictivos de GeoETL (Random Forest)

**Clasificar imágenes, medir superficies y predecir valores en gvSIG Online sin programar.**

Este manual explica, paso a paso y con ejemplos reales, cómo usar las categorías **Ráster** y **Predictivo** del editor ETL: qué hace cada nodo, cómo configurarlo, cómo comprobar que el resultado es fiable y cómo resolver los casos más habituales en un SIG. Está pensado para personas que conocen gvSIG Online y los datos geográficos, pero **no necesitan saber de estadística ni de programación**.

## Cómo usar este manual

| Si quieres… | Ve a… |
|---|---|
| Entender de qué va todo esto | [1. Qué es y para qué sirve](#1-qué-es-y-para-qué-sirve) |
| Hacer tu primer mapa ya | [5. Tutorial: tu primer mapa de cobertura](#5-tutorial-tu-primer-mapa-de-cobertura) (usa los datos de ejemplo) |
| Resolver un caso concreto | [6. Casos de uso](#6-casos-de-uso) |
| Saber qué hace un campo o un nodo | [7. Referencia de los nodos](#7-referencia-de-los-nodos) |
| Saber si el resultado es bueno | [8. Cómo saber si el resultado es bueno](#8-cómo-saber-si-el-resultado-es-bueno) |
| Arreglar un error | [10. Resolución de problemas](#10-resolución-de-problemas) |
| Buscar una palabra | [Glosario](#glosario) |

## Índice

1. [Qué es y para qué sirve](#1-qué-es-y-para-qué-sirve)
2. [Conceptos básicos](#2-conceptos-básicos)
3. [Los nodos en el editor](#3-los-nodos-en-el-editor)
4. [Antes de empezar: preparar los datos](#4-antes-de-empezar-preparar-los-datos)
5. [Tutorial: tu primer mapa de cobertura](#5-tutorial-tu-primer-mapa-de-cobertura)
6. [Casos de uso](#6-casos-de-uso)
7. [Referencia de los nodos](#7-referencia-de-los-nodos)
8. [Cómo saber si el resultado es bueno](#8-cómo-saber-si-el-resultado-es-bueno)
9. [Buenas prácticas](#9-buenas-prácticas)
10. [Resolución de problemas](#10-resolución-de-problemas)
11. [Para el administrador](#11-para-el-administrador)
12. [Preguntas frecuentes](#12-preguntas-frecuentes)
13. [Fundamentos científicos y referencias](#13-fundamentos-científicos-y-referencias)
14. [Glosario](#glosario)

---

## 1. Qué es y para qué sirve

### La idea en tres frases

1. Tú **enseñas** al sistema con ejemplos: "este recuadro de la imagen es agua, este es vegetación, este es suelo".
2. El sistema aprende **qué aspecto tiene cada cosa** en la imagen (qué colores, qué reflectancia en el infrarrojo…).
3. Después **aplica lo aprendido a toda la imagen**, píxel a píxel, y te devuelve un mapa de clases.

Eso es una **clasificación supervisada**. El algoritmo que hay detrás se llama **Random Forest** (bosque aleatorio): construye muchos "árboles de decisión" sencillos, cada uno con una parte distinta de tus ejemplos, y deja que **voten**. El resultado de la votación es más estable que el de un solo árbol. Tiene dos ventajas prácticas: funciona bien sin ajustar casi nada y te dice **qué variables han pesado más** en la decisión.

### Qué puedes hacer con él

| Problema | Qué predice | Ejemplo |
|---|---|---|
| **Clasificación** | Una **categoría** | Cobertura del suelo: agua / suelo / vegetación. ¿Zona quemada o no? |
| **Regresión** | Un **número** | Biomasa en kg/m², altura de la vegetación, humedad del suelo |

Y se puede aplicar a:

- **Imágenes ráster** (ortofotos, satélite, infrarrojo): el resultado es otro ráster que puedes publicar como capa o convertir en polígonos.
- **Tablas** (parcelas, puntos de inventario, tramos de río…): el resultado es la misma tabla con la predicción añadida.

### Qué obtienes al final

```
  Imagen (ráster)  ─┐
                    ├─►  [ aprender ]  ─►  Mapa de clases ──► Capa publicada en gvSIG Online
  Tus ejemplos      ─┘                       │                 Polígonos de cada clase
  (polígonos con clase)                      │                 Superficie por zona (m²)
                                             └─► Informe de calidad + mapa de seguridad del modelo
```

Un caso típico completo, que se desarrolla en este manual: *"Tengo una ortofoto con infrarrojo de un barranco. Quiero saber cuántos metros cuadrados de vegetación hay en cada tramo."* Se dibujan unos recuadros de ejemplo de cada clase, se clasifica la imagen, se convierten los píxeles de vegetación en polígonos y se calcula su superficie por tramo. En los datos de ejemplo, el resultado difiere de la superficie real en **menos de 10 m² por tramo**.

### Qué necesitas

| Ingrediente | Para qué | Dónde se consigue |
|---|---|---|
| Una **imagen ráster** (GeoTIFF) | Es lo que se clasifica | Tu ortofoto o imagen de satélite, subida al gestor de ficheros |
| **Polígonos de ejemplo** con una columna que diga la clase | Es lo que enseña al sistema | Los dibujas en un SIG de escritorio o en gvSIG Online y los exportas como shapefile o tabla PostGIS |
| (Opcional) **Polígonos de validación**, distintos de los anteriores | Para medir la calidad con datos que el sistema no ha visto | Igual que los de ejemplo, pero otros |
| (Opcional) **Zonas** (tramos, parcelas, términos…) | Para medir superficies por zona | Una capa de polígonos |

> **Importante:** el sistema solo reconoce **las clases que le enseñas**. Si en la imagen hay carreteras y no le diste ningún ejemplo de carretera, las meterá en la clase que más se les parezca. Los ejemplos tienen que cubrir todo lo que hay en la imagen.

---

## 2. Conceptos básicos

Esta sección explica las palabras que se usan en los nodos. Cada una tiene un ejemplo con la imagen de muestra del manual (un barranco de 300 × 300 m).

| Concepto | Qué es | Ejemplo |
|---|---|---|
| **Píxel** | Cada cuadradito de la imagen. Es la unidad que se clasifica. | La imagen de ejemplo tiene 300 × 300 = 90 000 píxeles de 1 m. |
| **Banda** | Cada "capa" de la imagen: una medida distinta de cada píxel. | La ortofoto tiene 3 bandas: Rojo, Verde e Infrarrojo. Cada banda es una **variable** con la que el sistema decide. |
| **Clase** | La categoría que quieres reconocer. | `agua`, `suelo`, `vegetacion`. |
| **Muestra (ejemplo)** | Un polígono sobre la imagen del que **sabes** la clase. | Un recuadro de 10 × 10 m dibujado sobre un trozo claro de vegetación. |
| **Píxel de muestra** | Cada píxel cuyo **centro** cae dentro de una muestra. | Un recuadro de 10 × 10 m con píxeles de 1 m da 100 píxeles de muestra. |
| **Entrenar** | El momento en que el sistema aprende de los píxeles de muestra. | Con 14 polígonos de ejemplo se obtienen 1 576 píxeles de muestra. |
| **Modelo** | Lo aprendido. Se puede aplicar a la misma imagen o a otras. | Sale por el puerto morado de *Random Forest*. |
| **Predecir** | Aplicar el modelo a todos los píxeles (o filas). | *Predecir ráster* clasifica los 90 000 píxeles. |
| **Validar** | Medir la calidad con datos que **no** se usaron para entrenar. | "De 100 píxeles que no había visto, acertó 95". |
| **Seguridad del modelo** | Qué proporción de los árboles vota por la clase elegida, de 0 a 1. Es un indicador **relativo**: no es una probabilidad calibrada. | 0,98 en medio de una zona homogénea; 0,55 en el borde entre dos clases. |
| **Sin dato** | Píxel sin información (fuera de la imagen o con valor nulo). | Aparece como transparente en el mapa. |

### Cómo se guarda la clase en un ráster clasificado

El mapa resultante es un ráster en el que **cada píxel guarda un número** (un código) en lugar de un nombre. Los códigos se asignan **por orden alfabético de la clase**, empezando por 1, y el **0 significa sin dato**:

| Código | Clase (ejemplo) |
|---|---|
| 0 | sin dato |
| 1 | agua |
| 2 | suelo |
| 3 | vegetacion |

No tienes que manejar estos códigos: los nodos de después (*Limpiar ráster*, *Ráster a polígonos*, *Publicar ráster*) saben qué clase es cada código y la muestran con su nombre.

### Los tres tipos de datos que viajan entre nodos

Los puertos de cada nodo (los círculos por donde se conectan) tienen un **color según lo que transportan**, y el editor **no deja conectar tipos distintos**:

| Tipo | Color del puerto | Qué es |
|---|---|---|
| **Tabla** | El de siempre | Una tabla de datos (como en el resto de GeoETL). |
| **Ráster** | Rosa frambuesa | Un fichero GeoTIFF, con una o varias bandas. |
| **Modelo** | Morado | El modelo entrenado. |

Si intentas conectar, por ejemplo, una tabla a una entrada rosa (ráster), el editor lo impide y te avisa.

---

## 3. Los nodos en el editor

### Dónde está cada nodo

Los nodos están en la barra superior del editor, agrupados por botones. Haz clic en el botón del grupo y **arrastra** el nodo al lienzo.

| Grupo (botón) | Nodos que contiene |
|---|---|
| **Entradas** | **Ráster (GeoTIFF)** · **Modelo guardado** (y las demás entradas de siempre: Shapefile, CSV, PostGIS…) |
| **Ráster** (botón rosa frambuesa) | **Recortar ráster** · **Combinar ráster** · **Índice espectral** · **Limpiar ráster** · **Ráster a polígonos** |
| **Predictivo** | **Muestrear ráster** · **Random Forest** · **Predecir ráster** · **Predecir tabla** · **Evaluar clasificación** · **Muestreo estratificado** · **Estimar superficies** |
| **Salidas** | **Guardar modelo** · **Publicar ráster** (y PgSQL/PostGIS, Visualizador…) |

**Por qué dos categorías.** *Ráster* reúne las operaciones con imágenes que sirven en cualquier flujo, aunque no haya modelo (recortar, combinar, calcular un índice, limpiar o vectorizar una clasificación). *Predictivo* reúne lo propio del aprendizaje automático: preparar las muestras, entrenar, aplicar y evaluar el modelo. Los nodos de la categoría Ráster tienen la cabecera **rosa frambuesa**, como sus puertos; los predictivos, **morada**.

> *Limpiar ráster* y *Ráster a polígonos* trabajan con ráster **de clases** (la salida de *Predecir ráster*), no con cualquier imagen.

### Resumen de entradas y salidas

| Nodo | Entradas (en este orden) | Salidas (en este orden) |
|---|---|---|
| **Ráster (GeoTIFF)** | — | Ráster |
| **Modelo guardado** | — | Modelo |
| **Recortar ráster** | Ráster, Máscara (tabla de polígonos) | Ráster |
| **Combinar ráster** | Ráster 1 (referencia), Ráster 2, Ráster 3, Ráster 4 | Ráster |
| **Índice espectral** | Ráster | Ráster |
| **Muestrear ráster** | Ráster, Muestras (tabla) | Píxeles (tabla) |
| **Random Forest** | Datos (tabla) | Informe (tabla), Modelo, Matriz de confusión (tabla) |
| **Predecir ráster** | Ráster, Modelo | Resultado (ráster), Seguridad (ráster) |
| **Predecir tabla** | Datos (tabla), Modelo | Tabla |
| **Limpiar ráster** | Ráster | Ráster |
| **Ráster a polígonos** | Ráster | Polígonos (tabla) |
| **Evaluar clasificación** | Ráster, Muestras de validación (tabla) | Informe (tabla), Matriz de confusión (tabla) |
| **Muestreo estratificado** | Ráster clasificado | Puntos (tabla) |
| **Estimar superficies** | Ráster clasificado, Puntos de referencia (tabla) | Superficies (tabla), Informe (tabla) |
| **Guardar modelo** | Modelo | — |
| **Publicar ráster** | Ráster | — |

### Configurar un nodo

1. Cada nodo tiene una **rueda de engranaje** en su cabecera. **Roja** significa "sin configurar".
2. Haz clic en la rueda: se abre el diálogo del nodo.
3. Rellena los campos y pulsa **Aceptar**. La rueda cambia de color: ya está configurado.
4. Algunos nodos (*Predecir ráster*, *Limpiar ráster*, *Ráster a polígonos*, *Combinar ráster*, *Recortar ráster*) **nacen ya configurados** porque funcionan con valores por defecto; aun así puedes abrirlos y cambiarlos.

> **El id del nodo (n1, n2…).** A la derecha del título, junto a la rueda, cada nodo muestra un id corto en una etiqueta blanca. Es el nombre con el que el asistente se refiere a ese nodo ("conecto n3 con n5"), así sabes siempre de cuál habla. El id se asigna al añadir el nodo, se guarda con el workspace y no cambia aunque borres otros nodos; tampoco se reutiliza el de un nodo borrado mientras el editor sigue abierto. Puedes renombrar el título con doble clic sin que el id cambie.

> **Configura los nodos de izquierda a derecha.** Un nodo ofrece en sus desplegables las columnas y bandas que le llegan del anterior. Si el anterior no está aceptado, los desplegables salen vacíos. Es la causa más frecuente de "el desplegable no me deja elegir nada".

> **Parámetros avanzados.** Casi todos los nodos tienen un enlace **Parámetros avanzados** que despliega opciones que casi nunca hace falta tocar. Los valores por defecto están pensados para funcionar bien.

### Ejecutar

Pulsa **Ejecutar** en la barra del editor. El botón muestra el estado:

| Icono | Significado |
|---|---|
| Rueda girando | Ejecutando. Una clasificación grande puede tardar varios minutos. |
| ✓ | Terminó bien. |
| ✗ | Falló. Pasa el ratón por el botón para leer el mensaje: dice **qué nodo** falló y por qué. |

Si algún nodo tiene la rueda roja, la ejecución se detiene antes de empezar con el mensaje *"Hay nodos sin configurar…"*.

### Qué se conserva y qué no

Esto es importante y suele sorprender:

- Todo lo que viaja entre nodos (tablas intermedias, rásteres, modelos) es **temporal**: se borra al terminar la ejecución.
- **Solo se conserva lo que acaba en un nodo de salida:** *PgSQL/PostGIS* para tablas (el informe, la matriz, los polígonos…), *Publicar ráster* para mapas, *Guardar modelo* para modelos.
- Si quieres ver el **Informe de calidad**, la **Matriz de confusión** o los **Polígonos**, conecta esa salida a un nodo *PgSQL/PostGIS* (operación *BORRAR Y CREAR* para poder repetir la ejecución).

---

## 4. Antes de empezar: preparar los datos

El 80 % de la calidad del resultado está en los datos, no en los parámetros. Dedica tiempo a esta sección.

### 4.1 La imagen

| Requisito | Detalle |
|---|---|
| **Formato** | GeoTIFF (`.tif` o `.tiff`), con cualquier compresión (incluidas las ortofotos del PNOA, comprimidas en JPEG con color YCbCr). |
| **Ubicación** | Subida al **gestor de ficheros** de gvSIG Online. No se leen ficheros de otras ubicaciones del servidor. |
| **Sistema de coordenadas** | Obligatorio (la imagen debe estar georreferenciada). Para convertir a polígonos debe ser un sistema con código EPSG (UTM, por ejemplo). |
| **Bandas** | Cualquier número. Cada banda es una variable. |
| **Tamaño** | Cientos de MB sin problema. **Una imagen enorme (por ejemplo, una hoja del PNOA a 25 cm, con más de 2 000 millones de píxeles) no conviene clasificarla entera**: recórtala a tu zona y, si no necesitas tanto detalle, redúcela a 1 m con el nodo **Recortar ráster** ([7.14](#714-recortar-ráster)). Los límites del servidor están en el [apartado del administrador](#11-para-el-administrador). |
| **Una sola fecha y un solo sensor** | Entrena y predice sobre imágenes comparables. Un modelo entrenado con una imagen de verano falla con una de invierno. |

**Ponle nombre a las bandas** cuando añadas el nodo *Ráster (GeoTIFF)* (por ejemplo `Rojo, Verde, IR`). Los nombres se usan después en todos los desplegables y facilitan que el nodo *Índice espectral* proponga las bandas correctas.

### 4.2 Las muestras (lo más importante)

Las muestras son **polígonos con una columna que dice la clase** de cada uno. Puede ser un shapefile, una tabla PostGIS, un KML…

**Cómo dibujarlas bien**

| Haz esto | Evita esto | Por qué |
|---|---|---|
| Dibuja polígonos **dentro** de zonas homogéneas, lejos de los bordes. | Polígonos que cruzan el límite entre agua y vegetación. | Los píxeles de borde son mezcla y confunden al sistema. |
| **Varios polígonos por clase** (mínimo 3-5, mejor decenas) repartidos por toda la imagen. | Un único polígono grande por clase. | Un solo polígono no recoge la variedad: el sistema aprende "ese recuadro", no "la vegetación". |
| Incluye **toda la variedad** de cada clase: vegetación verde y seca, agua clara y turbia, suelo claro y oscuro. | Muestrear solo lo "típico". | Lo que no ha visto, lo clasifica mal. |
| Incluye una clase **para todo lo demás** que hay en la imagen (carreteras, edificios, sombras…). | Dejar fuera clases presentes en la imagen. | Sin ejemplos, esos píxeles caen en otra clase. |
| Unos **cientos de píxeles por clase** como mínimo. | Clases con 10-20 píxeles. | Demasiado pocos para aprender de forma estable. |
| Un **nombre de clase coherente** (`vegetacion`, sin tildes ni mayúsculas variables). | Mezclar `Vegetación`, `vegetacion` y `VEGETACION`. | Para el sistema son tres clases distintas. |

**Una columna de clase, sin huecos.** Los polígonos con la clase vacía se ignoran. La columna **no puede llamarse igual que una banda** (si tu banda se llama `clase`, renombra una de las dos).

**Las clases desiguales no son un problema grave.** Si "suelo" tiene 980 píxeles y "agua" 96, el sistema compensa el desequilibrio internamente. Aun así, puedes limitar el máximo por clase en *Muestrear ráster* (campo *Máximo de píxeles por clase*) para que entrene más rápido.

### 4.3 Las muestras de validación (muy recomendable)

Son otro conjunto de polígonos, **distintos y a ser posible de otras zonas**, que solo sirven para medir la calidad del resultado final. Si usas los mismos para entrenar y para validar, te dará una nota inflada.

### 4.4 Los datos de ejemplo del manual

Para seguir el manual, usa los datos de la carpeta `ejemplos/` del plugin (fichero `ejemplos/datos_ejemplo_barranco.zip`). Es una escena sintética de un barranco. Descomprímelos y **súbelos al gestor de ficheros** (de cada shapefile hay que subir todos sus ficheros: `.shp`, `.shx`, `.dbf`, `.prj` y `.cpg`).

| Fichero | Qué es |
|---|---|
| `ortofoto.tif` | Imagen de 3 bandas (Rojo, Verde, Infrarrojo), 300 × 300 píxeles de 1 m, EPSG:25830. |
| `terreno.tif` | Modelo del terreno (banda Altura) con píxel de 2 m. Otra resolución, para practicar *Combinar ráster*. |
| `muestras_entrenamiento.shp` | 14 polígonos (5 suelo, 5 vegetación, 4 agua). Columna `clase`. |
| `muestras_validacion.shp` | 11 polígonos distintos (4 suelo, 4 vegetación, 3 agua). Columna `clase`. |
| `tramos_barranco.shp` | 3 zonas (`Tramo 1`, `Tramo 2`, `Tramo 3`). Columna `tramo`. |
| `puntos_inventario.shp` | 160 puntos con `rojo`, `verde`, `infrarrojo` y su `clase`. Para el caso de la tabla. |
| `puntos_nuevos.shp` | 40 puntos sin clase (la real está en `clase_real`). |
| `parcelas_campo.shp` | 45 parcelas de 5 × 5 m con `biomasa` medida (kg/m²). Para el caso de regresión. |

La **superficie real** de la escena es conocida, para que puedas comparar tus resultados:

| | Suelo | Vegetación | Agua |
|---|---:|---:|---:|
| **Total** | 65 217 m² | 21 784 m² | 2 999 m² |
| Tramo 1 | 21 039 m² | 7 962 m² | 999 m² |
| Tramo 2 | 22 400 m² | 6 600 m² | 1 000 m² |
| Tramo 3 | 21 778 m² | 7 222 m² | 1 000 m² |

> Los resultados del manual salen de ejecutar estos mismos flujos. **Los tuyos pueden diferir ligeramente** (unas décimas en las métricas) si cambias el orden de las variables o la semilla; las conclusiones son las mismas.

---

## 5. Tutorial: tu primer mapa de cobertura

**Objetivo:** clasificar la ortofoto del barranco en agua, suelo y vegetación, medir la calidad y obtener los polígonos de vegetación.
**Tiempo:** unos 20 minutos. **Datos:** los de ejemplo (apartado 4.4).

### Visión general del flujo

```
 Ráster (GeoTIFF) ──────────────────────────┬──────────────────────────────┐
   ortofoto.tif                             ▼                              ▼
                                   Muestrear ráster ──► Random Forest ──► Predecir ráster ──► Ráster a polígonos ──► PgSQL/PostGIS
 Shapefile ───────────────────────►   (Ráster, Muestras)   (Datos)    (Ráster, Modelo)
   muestras_entrenamiento.shp                                  │ Informe, Matriz
                                                               └────────────────────────────────► PgSQL/PostGIS
```

### Paso 1: sube los datos

Sube al gestor de ficheros `ortofoto.tif` y los ficheros de `muestras_entrenamiento.shp` (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`). Si vas a seguir los casos siguientes, sube también el resto.

### Paso 2: añade los nodos

Abre el editor ETL con un lienzo vacío. Arrastra:

| Nodo | De qué grupo |
|---|---|
| **Ráster (GeoTIFF)** | Entradas |
| **Shapefile** | Entradas |
| **Muestrear ráster** | Predictivo |
| **Random Forest** | Predictivo |
| **Predecir ráster** | Predictivo |
| **Ráster a polígonos** | Ráster |
| **PgSQL/PostGIS** (dos veces) | Salidas |

### Paso 3: configura la imagen (nodo *Ráster (GeoTIFF)*)

Clic en la rueda del nodo.

| Campo | Qué poner | Qué ocurre |
|---|---|---|
| **Fichero GeoTIFF** | Pulsa **Elige fichero** y elige `ortofoto.tif` | Aparece un resumen: *3 bandas · EPSG:25830 · 300 × 300 px*. |
| **Nombres de las bandas (opcional)** | `Rojo`, `Verde`, `IR` (uno por banda) | A partir de aquí las bandas se llaman `rojo`, `verde`, `ir`. |

Pulsa **Aceptar**.

### Paso 4: configura las muestras (nodo *Shapefile*)

| Campo | Qué poner |
|---|---|
| **Elige shapefile** | **Elige fichero** → `muestras_entrenamiento.shp` |
| **Codificación** | `utf-8` |
| **Insertar si no se carga el PRJ** | Si tu shapefile lleva `.prj` (el de ejemplo sí) no hace falta; si no, elige `EPSG:25830` |

**Aceptar**.

### Paso 5: configura *Muestrear ráster*

Conecta primero los dos nodos anteriores (paso 8, o hazlo ahora): *Ráster (GeoTIFF)* → entrada **Ráster**; *Shapefile* → entrada **Muestras**. Luego abre el diálogo:

| Campo | Qué poner | Para qué |
|---|---|---|
| **Columna de clase** | `clase` | La columna del shapefile que dice si cada recuadro es agua, suelo o vegetación. |
| *Máximo de píxeles por clase* (avanzado) | vacío | Sin límite. |
| *Semilla aleatoria* (avanzado) | `42` | Con la misma semilla sale siempre la misma muestra. |

**Aceptar.** Este nodo extrae los píxeles de la imagen que caen dentro de cada recuadro. Con los datos de ejemplo salen **1 576 píxeles**: 980 de suelo, 500 de vegetación y 96 de agua.

### Paso 6: configura *Random Forest*

Conecta *Muestrear ráster* → entrada **Datos** de *Random Forest*. Abre el diálogo:

| Campo | Qué poner | Para qué |
|---|---|---|
| **Variable a predecir** | `clase` | Lo que quieres que aprenda. |
| **Variables para predecir** | Marcadas `rojo`, `verde`, `ir` (por defecto vienen todas marcadas menos la variable a predecir) | Las bandas con las que decidirá. |

Deja el resto como está. **Aceptar.** Con los valores por defecto, la calidad se mide **dejando fuera polígonos de muestra** (*Cómo se mide la calidad* = *Automática*): como la tabla viene de *Muestrear ráster* y cada clase tiene varios polígonos, el nodo evalúa cada polígono con un modelo que no lo ha visto. Es la medida honesta para imágenes (ver [caso 2](#caso-2-mejorar-el-mapa-y-medir-su-calidad-de-verdad)).

### Paso 7: configura *Predecir ráster*, *Ráster a polígonos* y las salidas

- **Predecir ráster:** no tiene parámetros. Al abrirlo te dice si la imagen tiene todas las bandas que necesita el modelo (*"El ráster tiene todas las bandas que necesita el modelo: rojo, verde, ir"*).
- **Ráster a polígonos:** *Clases a conservar* = `vegetacion`; *Área mínima* = `25` (m², descarta los polígonos de menos de 25 m²). Deja lo demás.
- **PgSQL/PostGIS** (primero): elige tu **Conexión BBDD**, pulsa **Obtén esquema** y elige un **Esquema**, escribe el **Nombre de la tabla** `cobertura_vegetacion` y la **Operación** `BORRAR Y CREAR`.
- **PgSQL/PostGIS** (segundo): igual con el nombre `cobertura_informe`.

### Paso 8: conecta los nodos

Arrastra desde el puerto de salida (derecha) al de entrada (izquierda). Los colores deben coincidir.

| Desde | Puerto | Hasta | Puerto |
|---|---|---|---|
| Ráster (GeoTIFF) | Ráster | Muestrear ráster | Ráster |
| Shapefile | (salida) | Muestrear ráster | Muestras |
| Muestrear ráster | Píxeles | Random Forest | Datos |
| Ráster (GeoTIFF) | Ráster | Predecir ráster | Ráster |
| Random Forest | **Modelo** (morado) | Predecir ráster | Modelo |
| Predecir ráster | Resultado | Ráster a polígonos | Ráster |
| Ráster a polígonos | Polígonos | PgSQL/PostGIS (1.º) | (entrada) |
| Random Forest | Informe | PgSQL/PostGIS (2.º) | (entrada) |

> **El error más común:** conectar el puerto equivocado de *Random Forest*. Tiene **tres salidas**: Informe (tabla), **Modelo** (morado) y Matriz de confusión (tabla). *Predecir ráster* necesita la del medio.

### Paso 9: ejecuta

Pulsa **Ejecutar**. En unos segundos el botón mostrará ✓.

### Paso 10: lee los resultados

**El informe (`cobertura_informe`)** es una tabla de tres columnas (`section`, `name`, `value`). Lo más importante, con los datos de ejemplo:

| section | name | value | Qué significa |
|---|---|---:|---|
| validation | polygon | 1 | La calidad se ha medido **dejando fuera polígonos** (lo eligió la opción automática). |
| training | rows | 1 576 | Píxeles con los que entrenó. |
| training | folds · groups | 5 · 14 | 5 rondas repartiendo los 14 polígonos: cada polígono se evalúa una vez con un modelo que no lo vio. |
| metric | accuracy | **0,924** | **Acertó el 92,4 %** de los píxeles, cada uno evaluado por un modelo que no había visto su polígono. |
| metric | balanced_accuracy | 0,865 | Acierto medio por clase: más justo cuando unas clases tienen muchos más píxeles que otras. |
| fold | fold_1 … fold_5 | 0,93 · 0,96 · 0,89 · 0,92 · **0,75** | Nota de cada ronda. Que una baje tanto indica que hay pocos polígonos (ver caso 2). |
| importance_permutation | ir · rojo · verde | 0,226 · 0,065 · 0,017 | Cuánto empeora la nota si se desordena cada banda: **el infrarrojo es, con diferencia, la que más aporta**. |
| importance | ir · rojo · verde | 0,520 · 0,319 · 0,161 | La importancia "por impureza", que suman 1. Más rápida, pero sesgada; fíate más de la de permutación. |

Las clases se entienden mejor en la **matriz de confusión** (salida 3 de *Random Forest*): cada fila es la clase **real** y cada columna lo que **dijo el modelo**:

| real \ predicho | pred_agua | pred_suelo | pred_vegetacion | total | recall |
|---|---:|---:|---:|---:|---:|
| agua | **70** | 24 | 2 | 96 | 0,73 |
| suelo | 16 | **926** | 38 | 980 | 0,94 |
| vegetacion | 0 | 39 | **461** | 500 | 0,92 |

Lo que importa está en la **diagonal** (aciertos). La clase más débil es **agua**: de 96 píxeles de agua, 24 se confundieron con suelo (el agua turbia se parece al suelo oscuro). Es normal: el agua tiene pocas muestras y es la clase que más se mezcla.

> El informe también trae el **kappa** (0,851). Es una medida clásica, pero hoy se desaconseja para evaluar mapas (Pontius y Millones, 2011; Foody, 2020): fíjate en la exactitud global, la equilibrada y las de cada clase.

**Los polígonos (`cobertura_vegetacion`):** 5 polígonos de vegetación con una superficie total de **20 810 m²** (la real es 21 784 m²: un 4,5 % menos). Ojo: esta superficie sale de **contar píxeles** del mapa, que arrastra sus errores. Para dar una superficie con rigor, con su intervalo de confianza, mira el [caso 9](#caso-9-superficie-con-intervalo-de-confianza).

### Paso 11: publica el mapa para verlo

Añade un nodo **Publicar ráster** (Salidas) y conéctalo a **Resultado** de *Predecir ráster*:

| Campo | Qué poner |
|---|---|
| **Workspace** | Un workspace donde tengas permiso. |
| **Grupo de capas** | Un grupo existente. |
| **Título de la capa** | `Cobertura del barranco` |
| **Nombre de la capa** | (se propone solo) `cobertura_del_barranco` |
| **Si la capa ya existe** | `Reemplazar su ráster` |

Ejecuta de nuevo. La capa aparece en el workspace con **un color por clase** y con la leyenda de las clases (agua, suelo, vegetacion). Si vuelves a ejecutar el flujo, **se reemplaza el ráster sin cambiar la capa**, sus permisos ni su dirección.

### Qué has aprendido y qué sigue

Has hecho el ciclo completo: *muestras → modelo → mapa → polígonos → capa*. El 92,4 % es una nota **honesta** porque se mide con polígonos que el modelo no había visto; si hubieras elegido *Reserva aleatoria* habría salido un 94,6 %, más optimista. En el [caso 2](#caso-2-mejorar-el-mapa-y-medir-su-calidad-de-verdad) verás por qué y cómo mejorar el mapa; en el [caso 3](#caso-3-superficie-de-vegetación-por-tramo), cómo obtener metros cuadrados por zona; y en el [caso 9](#caso-9-superficie-con-intervalo-de-confianza), cómo dar esas superficies con rigor estadístico.

### Si algo sale mal en el tutorial

| Síntoma | Causa más probable | Qué hacer |
|---|---|---|
| El desplegable *Columna de clase* está vacío | El nodo *Shapefile* no está aceptado o no está conectado | Acepta el *Shapefile* y conéctalo a **Muestras**; vuelve a abrir *Muestrear ráster*. |
| *Variable a predecir* vacío | *Muestrear ráster* sin aceptar | Acepta *Muestrear ráster* antes. |
| El botón da ✗ con *"Hay nodos sin configurar…"* | Queda alguna rueda roja | Abre los nodos con rueda roja y pulsa **Aceptar**. |
| *"Ningún polígono de muestra intersecta con el ráster…"* | Las muestras y la imagen no están en el mismo sitio o falta el sistema de coordenadas | Revisa el `.prj` del shapefile (o elige EPSG:25830) y que se solapen. |
| *"El ráster no tiene las bandas con las que se entrenó el modelo"* | Se usó un ráster distinto al de *Muestrear ráster* | Conecta el **mismo** *Ráster (GeoTIFF)* a *Muestrear* y a *Predecir*. |

---

## 6. Casos de uso

Cada caso indica **qué problema resuelve, qué datos usa, el esquema del flujo, la configuración paso a paso, el resultado esperado con los datos de ejemplo y los errores típicos**. Los casos 1 a 6 y el 9 se han ejecutado con los datos de ejemplo y sus cifras son reales; el caso 7 se ha verificado con pruebas automáticas de extremo a extremo; el 8 son recetas con los nodos disponibles.

| # | Caso | Tipo |
|---|---|---|
| 1 | [Mapa de cobertura del suelo](#caso-1-mapa-de-cobertura-del-suelo) | Clasificación de ráster |
| 2 | [Mejorar el mapa y medir su calidad de verdad](#caso-2-mejorar-el-mapa-y-medir-su-calidad-de-verdad) | Validación |
| 3 | [Superficie de vegetación por tramo](#caso-3-superficie-de-vegetación-por-tramo) | Clasificación + medición |
| 4 | [Evaluar el mapa con muestras independientes](#caso-4-evaluar-el-mapa-con-muestras-independientes) | Validación |
| 5 | [Predecir sobre una tabla de puntos](#caso-5-predecir-sobre-una-tabla-de-puntos) | Clasificación de tabla |
| 6 | [Estimar biomasa con parcelas de campo](#caso-6-estimar-biomasa-con-parcelas-de-campo) | Regresión |
| 7 | [Entrenar una vez y reutilizar el modelo](#caso-7-entrenar-una-vez-y-reutilizar-el-modelo) | Operación periódica |
| 8 | [Otros casos](#caso-8-otros-casos-recetas) | Recetas |
| 9 | [Superficie con intervalo de confianza](#caso-9-superficie-con-intervalo-de-confianza) | Estimación con rigor estadístico |

---

### Caso 1: Mapa de cobertura del suelo

**Problema.** Tienes una ortofoto con infrarrojo y necesitas un mapa de *agua / suelo / vegetación*.
**Datos.** `ortofoto.tif`, `muestras_entrenamiento.shp`.
**Esquema.** Es el flujo del [tutorial](#5-tutorial-tu-primer-mapa-de-cobertura): *Ráster + Shapefile → Muestrear → Random Forest → Predecir → Publicar*.

**Resultado esperado.** Exactitud ≈ 92,4 % dejando fuera polígonos (la medida por defecto); el infrarrojo es la banda que más aporta; el agua es la clase más débil.

**Qué mirar para saber si es bueno**
- La **matriz de confusión**: ¿qué clases se confunden? Aquí, agua con suelo.
- El **mapa de seguridad del modelo** (2.ª salida de *Predecir ráster*, *Seguridad*): publícalo con otro nodo *Publicar ráster*. Las zonas con valores bajos (cerca de 0,5) son las dudosas: suelen ser los bordes entre clases y las clases con pocas muestras. Úsalo para **localizar** dónde revisar, no como probabilidad de acierto: no está calibrado.

**Errores típicos**
- Dibujar los recuadros de agua abarcando orilla: salen píxeles mixtos y el agua se confunde con suelo.
- Olvidar una clase presente en la imagen.

---

### Caso 2: Mejorar el mapa y medir su calidad de verdad

**Problema.** ¿Cómo sé si el modelo funcionará de verdad en zonas que no ha visto? ¿Y cómo lo mejoro?

**Por qué no vale cualquier forma de medir.** Los píxeles vecinos se parecen muchísimo. Si se aparta un 20 % de los píxeles **al azar** para evaluar, casi todos tienen un "gemelo" en los de entrenamiento, dentro del mismo polígono, y la nota sale inflada. Lo honesto es **dejar fuera polígonos enteros** (Roberts et al., 2017; Ploton et al., 2020). Por eso *Random Forest* lo hace **por defecto** (*Cómo se mide la calidad* = *Automática*) cuando la tabla viene de *Muestrear ráster* y cada clase tiene al menos dos polígonos; si no se puede, usa la reserva aleatoria y lo indica en el informe (sección `validation`).

**Idea para mejorar el mapa:** añadir variables que ayuden, como un índice espectral (NDVI), y limpiar el ruido.

**Esquema**

```
 Ráster ─► Índice espectral (NDVI) ─┬─► Muestrear ráster ─► Random Forest ─► Predecir ráster ─► Limpiar ráster
                                    │      ▲                                    ▲
 Shapefile (muestras) ──────────────┼──────┘                                    │
                                    └───────────────────────────────────────────┘
```

**Pasos**

1. Entre *Ráster (GeoTIFF)* y el resto, añade **Índice espectral**:

   | Campo | Valor | Notas |
   |---|---|---|
   | **Índice** | `NDVI - vegetación` | Realza la vegetación sana. |
   | Bandas | NIR = `ir`, Rojo = `rojo` | El nodo las **propone solo** por su nombre. |
   | **Valores de la imagen** | `Imagen de 8 bits (0-255)` o *usarlos tal cual* | Para el NDVI da igual (no tiene offset); para SAVI o EVI hay que elegir bien. |
   | **Nombre de la banda nueva** | `ndvi` | Se añade como una banda más; las originales se conservan. |

2. Conecta la salida del índice a *Muestrear ráster* **y** a *Predecir ráster* (los dos deben recibir la imagen con la banda `ndvi`).
3. En *Random Forest* marca las variables `rojo`, `verde`, `ir`, `ndvi`. Deja *Cómo se mide la calidad* en *Automática*.
4. Después de *Predecir ráster* añade **Limpiar ráster** (*Método*: filtro de mayoría, *Ventana* 3 × 3, *Repeticiones* 1). Elimina los píxeles sueltos mal clasificados.

**Qué verás en el informe (resultados reales)**

| Modelo | Reserva aleatoria 20 % | Dejando fuera polígonos (por defecto) |
|---|---:|---:|
| 3 bandas (tutorial) | 0,946 | **0,924** |
| 3 bandas + NDVI | 0,949 | **0,941** |

| Notas de las 5 rondas (3 bandas + NDVI) | 0,941 · 0,959 · 0,944 · 0,940 · **0,804** |
|---|---|
| Importancia por permutación | `ir` 0,280 · `ndvi` 0,246 · `rojo` 0,084 · `verde` 0,019 |

- El NDVI **mejora** la nota honesta (0,924 → 0,941) y es la segunda variable que más aporta.
- La reserva aleatoria da siempre más. Aquí la diferencia es pequeña porque los recuadros son muy puros; en imágenes reales no es raro pasar de más de un 95 % al azar a menos de un 80 % dejando polígonos fuera. **Fíate de la segunda.**

**Cómo leer las rondas.** La ronda 5 sale peor (0,804). En cada ronda se dejan fuera algunos polígonos completos; con solo 4-5 polígonos por clase, **depende mucho de cuáles caen fuera**. La señal es: *si las notas de las rondas varían mucho, faltan polígonos de ejemplo*. Añadir más recuadros mejora la fiabilidad de la estimación.

**Resultado del mapa.** Al vectorizar la vegetación con este modelo (+ mayoría 3 × 3 + área mínima 25 m²) salen 5 polígonos con **21 781 m²**, frente a los 21 784 m² reales. (Recuerda que es un recuento de píxeles: para dar la superficie con su intervalo de confianza, ver el [caso 9](#caso-9-superficie-con-intervalo-de-confianza).)

#### Cuándo una variable "que mejora la nota" empeora el mapa

Prueba el mismo flujo añadiendo el modelo del terreno como variable (nodos **Ráster (GeoTIFF)** para `terreno.tif` con la banda `Altura` + **Combinar ráster**; ver [7.9](#79-combinar-ráster)). Resultados reales:

| Modelo | Nota dejando fuera polígonos | Nota con muestras independientes (caso 4) | Polígonos de vegetación | Superficie de vegetación (real: 21 784 m²) |
|---|---:|---:|---:|---:|
| Solo 3 bandas | 0,924 | 0,955 | 5 | 21 786 m² |
| 3 bandas + NDVI | 0,941 | 0,955 | 5 | **21 781 m²** |
| 3 bandas + NDVI + **altura** | 0,872 | 0,988 | **2** | 20 357 m² |

Con la altura, la nota independiente **sube** (0,955 → 0,988), pero el mapa **pierde tres de las cuatro manchas de vegetación aisladas** (salen 2 polígonos en vez de 5) y subestima unos 1 400 m². ¿Por qué? En las muestras, la vegetación siempre estaba cerca del cauce, a baja altura. El sistema aprendió "vegetación = zona baja" y descartó la vegetación que está lejos del cauce, aunque se vea verde en el infrarrojo. Las muestras de validación (que también estaban casi todas cerca del cauce) no lo detectaron.

**Lecciones:**
1. **Más variables no siempre es mejor.** Añade solo variables que se relacionen con la clase **en toda la escena**, no solo en tus muestras.
2. **Una buena nota no garantiza un buen mapa.** Mira siempre el mapa y compáralo con lo que sabes del terreno.
3. **Incluye en las muestras (y en las de validación) los casos raros:** vegetación aislada, agua lejos del cauce, suelo con restos.
4. Si dudas de una variable, **compara** los mapas con y sin ella (cuenta polígonos, mide superficies).

---

### Caso 3: Superficie de vegetación por tramo

**Problema.** Quieres saber **cuántos metros cuadrados de vegetación hay en cada tramo del barranco**, para un informe o para comparar tramos.
**Datos.** Los del caso 2 más `tramos_barranco.shp` (3 zonas con la columna `tramo`).
**Idea.** La clasificación da una imagen; para medir superficies hay que convertirla en polígonos, cortarlos con las zonas y sumar las áreas. Los nodos de GeoETL de siempre hacen esa parte.

**Esquema**

```
 (flujo del caso 2) ─► Limpiar ráster ─► Ráster a polígonos ─┐ Principal
                                                              ├─► Intersección ─► Calcula Área ─► Estadísticas ─► PgSQL/PostGIS
 Shapefile (tramos_barranco.shp) ─────────────────────────────┘ Secundaria
```

**Pasos (a continuación del caso 2)**

| Nodo | Configuración | Para qué |
|---|---|---|
| **Ráster a polígonos** | *Clases a conservar* `vegetacion` · *Área mínima* `25` | Solo los polígonos de vegetación, sin manchas de menos de 25 m². |
| **Shapefile** (tramos) | `tramos_barranco.shp` | Las zonas. |
| **Intersección** | Entrada **Principal** = polígonos de vegetación; entrada **Secundaria** = tramos. Marca *Fusiona atributos de la entrada secundaria a la salida final*. Deja sin marcar *Autointersecta capa*. | Corta la vegetación con cada tramo. Cada trozo conserva su `tramo`. |
| **Calcula Área** | *Nuevo atributo área*: `area_m2` | Mide cada trozo en m² (el sistema de coordenadas es UTM, en metros). |
| **Estadísticas** | *Atributo numérico*: `area_m2` · *Agrupa por*: `tramo` | Suma por tramo. El resultado está en la columna `_sum`. |
| **PgSQL/PostGIS** | Tabla `vegetacion_por_tramo` | Para conservar el resultado. |

**Resultado con los datos de ejemplo (modelo del caso 2: 3 bandas + NDVI)**

| Tramo | Superficie calculada | Superficie real | Diferencia |
|---|---:|---:|---:|
| Tramo 1 | 7 963 m² | 7 962 m² | +1 m² |
| Tramo 2 | 6 603 m² | 6 600 m² | +3 m² |
| Tramo 3 | 7 215 m² | 7 222 m² | −7 m² |
| **Total** | **21 781 m²** | 21 784 m² | −3 m² |

La tabla de salida tiene las columnas `_max`, `_min`, `_count`, `_sum`, `_mean`, `_median`, `_mode`, `_desv` y `tramo`; la que interesa es `_sum`.

**Consejos**
- **Usa un sistema de coordenadas proyectado** (UTM, etc.) para que las áreas salgan en metros. Con coordenadas geográficas (grados) las áreas no tienen sentido métrico.
- El **Área mínima** y **Limpiar ráster** reducen el ruido: sin ellos la vegetación del ejemplo daría **873 polígonos** en lugar de 5 (ver [7.7](#77-ráster-a-polígonos)).
- Una **sobreestimación o subestimación** sistemática suele indicar clases mal muestreadas. Comprueba la matriz de confusión: si "suelo" se confunde con "vegetación", la superficie de vegetación se inflará.
- **Esto es un recuento de píxeles, no una estimación estadística.** Contar los píxeles de una clase arrastra los errores del mapa: si el mapa confunde suelo con vegetación, la superficie de vegetación sale sesgada, y el recuento no dice cuánto. Aquí cuadra casi al metro porque los datos son sintéticos y el mapa es muy bueno; con datos reales **no lo presentes como resultado final**. Para un informe, estima la superficie con su intervalo de confianza como en el [caso 9](#caso-9-superficie-con-intervalo-de-confianza) (Olofsson et al., 2014).

---

### Caso 4: Evaluar el mapa con muestras independientes

**Problema.** Necesitas poder decir *"este mapa tiene una exactitud del X %"* ante un cliente o un revisor, con una medida que no dependa del entrenamiento.
**Idea.** Tomas **otros polígonos**, que no se han usado para entrenar, con su clase real, y comparas con el mapa final (incluida la limpieza). Es lo que mide el nodo **Evaluar clasificación**.
**Datos.** El mapa clasificado y `muestras_validacion.shp` (11 polígonos distintos de los de entrenamiento).

**Esquema**

```
 Predecir ráster ─► Limpiar ráster ─┐
                                    ├─► Evaluar clasificación ─► Informe ─► PgSQL/PostGIS
 Shapefile (validación) ────────────┘                          └► Matriz de confusión ─► PgSQL/PostGIS
```

**Pasos**

1. Añade **Evaluar clasificación** (Predictivo).
2. Conecta el ráster clasificado (de *Predecir ráster* o de *Limpiar ráster*) a **Ráster** y el shapefile de validación a **Muestras de validación**.
3. **Columna de clase** = `clase`.

**Resultado con los datos de ejemplo** (modelo 3 bandas + NDVI; 1 229 píxeles de validación, más 3 sin clasificar):

| | Antes de limpiar | Después del filtro de mayoría 3 × 3 |
|---|---:|---:|
| Exactitud | 0,955 | 1,000 |
| Intervalo del 95 % de la exactitud | 0,939 – 0,966 | 1,000 – 1,000 |
| Vegetación: precisión · recall | 0,952 · 0,943 | 1,000 · 1,000 |
| Intervalo del recall de la vegetación | 0,915 – 0,960 | 1,000 – 1,000 |

**Cómo leer el informe**

- En cada clase, **`precision` es la exactitud del usuario**: de lo que el mapa dice que es vegetación, cuánto lo es de verdad (un valor bajo = el mapa **sobrestima** esa clase). **`recall` es la exactitud del productor**: de lo que realmente es vegetación, cuánto encuentra el mapa (un valor bajo = el mapa **infraestima** esa clase).
- `unclassified_pixels`: píxeles de validación que quedaron sin clasificar (se informan aparte).
- `classes_not_in_model`: si hay una clase de validación que el modelo no conoce, cuenta como error y se avisa.
- **Intervalos (sección `ci`).** Se calculan por *bootstrap* remuestreando **muestras enteras** (cada polígono o cada punto) 1 000 veces, no píxeles sueltos: los píxeles de un mismo polígono no son independientes, y tratarlos como tales daría intervalos falsamente estrechos. Con pocos polígonos, el intervalo es amplio: es la información correcta, no un fallo.

**Qué validez estadística tiene.** El nodo compara el mapa con lo que le des. Para que la exactitud sea **inferible a todo el mapa** (lo que se pide en un informe técnico), las muestras deben ser una **muestra aleatoria estratificada por clase del mapa**, normalmente de puntos (Olofsson et al., 2014; Stehman y Foody, 2019). Unos polígonos dibujados a mano, como los de este ejemplo, solo dan una **orientación**: no se eligieron al azar y no representan proporcionalmente el mapa. El [caso 9](#caso-9-superficie-con-intervalo-de-confianza) muestra el procedimiento riguroso con *Muestreo estratificado* y *Estimar superficies*.

> El informe incluye también el **kappa** por compatibilidad. No lo uses para valorar el mapa: está desaconsejado para evaluar exactitud (Pontius y Millones, 2011; Foody, 2020).

**Cuidado con el 100 %.** Que el mapa limpio salga con 1,000 **no significa que sea perfecto**: las muestras de validación son recuadros pequeños y puros, lejos de los bordes, que es donde el mapa lo hace mejor. Para una nota creíble, tus muestras de validación deben incluir **bordes, zonas de transición, casos raros y toda la extensión de la zona**. Y deben ser **independientes** de las de entrenamiento (idealmente de otra zona).

**Puntos en vez de polígonos.** Las muestras de validación pueden ser **puntos** (por ejemplo, comprobaciones de campo): cada punto cuenta el píxel en el que cae.

---

### Caso 5: Predecir sobre una tabla de puntos

**Problema.** Tienes un inventario de puntos de los que conoces su categoría y otros nuevos de los que no. Quieres clasificar los nuevos (idoneidad, riesgo, tipo de elemento…). **No hay ráster**: son filas de una tabla.
**Datos.** `puntos_inventario.shp` (160 puntos con `rojo`, `verde`, `infrarrojo` y `clase`) y `puntos_nuevos.shp` (40 puntos sin clase).

**Esquema**

```
 Shapefile (puntos_inventario) ─► Random Forest ─┐ Modelo
                                                  ├─► Predecir tabla ─► PgSQL/PostGIS
 Shapefile (puntos_nuevos) ───────────────────────┘
```

**Pasos**

1. **Shapefile** `puntos_inventario.shp` → **Random Forest** (entrada Datos).
2. En *Random Forest*: *Variable a predecir* `clase`; *Variables para predecir* `rojo`, `verde`, `infrarrojo` (desmarca `id`: es un identificador, no una medida).
3. **Shapefile** `puntos_nuevos.shp` → **Predecir tabla** (entrada Datos). La salida **Modelo** de *Random Forest* → entrada **Modelo**.
4. En *Predecir tabla*: *Nombre de la columna de predicción* = `prediction`. El diálogo comprueba que la tabla tiene las columnas del modelo.

**Resultado**

- Calidad del modelo (reserva 20 %): exactitud 0,938, kappa 0,844.
- Sobre los 40 puntos nuevos: **36 aciertos (90 %)**, con una seguridad media del modelo de **0,88** (proporción media de votos; no es una probabilidad de acierto).
- Como la tabla no viene de *Muestrear ráster*, la validación automática usa la **reserva aleatoria**, que aquí es correcta: los puntos están dispersos y no forman grupos de píxeles vecinos.
- La tabla de salida conserva **todas las columnas y la geometría** y añade dos: `prediction` (la clase) y `prediction_confidence` (la seguridad del modelo, de 0 a 1):
  `ogc_fid, id, rojo, verde, infrarrojo, clase_real, wkb_geometry, prediction, prediction_confidence`

**Detalles**

- Las filas con valores vacíos o no numéricos en las variables **se quedan sin predicción** (`NULL`); no rompen la ejecución.
- La tabla de entrada **no se modifica**: se crea una nueva.
- Las columnas de predicción no pueden existir ya en la tabla; si existen, cambia el nombre.
- Con un modelo de **regresión** (números) la segunda columna es la dispersión entre los árboles: cuanto más alta, menos fiable el valor.

---

### Caso 6: Estimar biomasa con parcelas de campo

**Problema.** Has medido en campo la **biomasa** (kg/m²) en 45 parcelas de 5 × 5 m. Quieres un **mapa continuo de biomasa** de toda la zona y saber dónde es más dudoso.
**Tipo.** Regresión (se predice un número, no una categoría).
**Datos.** `ortofoto.tif` y `parcelas_campo.shp` (columna `biomasa`).

**Esquema**

```
 Ráster ─► Índice espectral (NDVI) ─┬─► Muestrear ráster ─► Random Forest (regresión) ─┐ Modelo
                                    │      ▲                                              ├─► Predecir ráster ─► Publicar ráster (valores)
 Shapefile (parcelas) ──────────────┘──────┘                                             │                    └► Publicar ráster (incertidumbre)
                                    └────────────────────────────────────────────────────┘
```

**Pasos**

1. **Índice espectral** NDVI sobre la ortofoto (como en el caso 2).
2. **Muestrear ráster**: *Columna de clase* = `biomasa`. (Aquí la columna no es una clase sino un número; el nodo funciona igual.)
3. **Random Forest**: *Variable a predecir* `biomasa`; *Tipo de problema* → **Regresión (número)** (si lo dejas en "Detectar automáticamente" lo detecta, pero conviene fijarlo); variables `rojo`, `verde`, `ir`, `ndvi`. *Cómo se mide la calidad*: **Dejar fuera polígonos de muestra**, 5 rondas.
4. **Predecir ráster**: la salida **Resultado** es el mapa de biomasa (valores) y **Seguridad** es la **dispersión entre los árboles** (un indicador de incertidumbre).
5. **Publicar ráster** (dos veces): uno para el resultado y otro para la incertidumbre. Para el de valores puedes fijar la **rampa de color** en *Parámetros avanzados* (por ejemplo, mínimo `0`, máximo `6`) para que dos mapas de fechas distintas se vean con la misma escala.

**Resultado con los datos de ejemplo** (45 parcelas → 1 124 píxeles de muestra):

| Métrica | Valor | Cómo leerla |
|---|---:|---|
| R² | 0,464 | Explica el 46 % de la variación (1 = perfecto, 0 = no mejor que la media). |
| RMSE | 1,06 kg/m² | Error típico de cada estimación. |
| MAE | 0,56 kg/m² | Error medio absoluto. |
| Importancia por permutación | `ndvi` 0,268 · `ir` 0,195 · `verde` −0,056 · `rojo` −0,077 | La biomasa se explica por el NDVI y el infrarrojo. **Un valor negativo** significa que desordenar esa variable *mejora* la nota: no aporta nada y solo añade ruido. Aquí se podrían quitar `verde` y `rojo`. |

Es una nota **modesta**, y es honesta: se mide dejando fuera parcelas enteras (la opción automática lo hace porque las parcelas son polígonos), con solo 45 parcelas, y la variación entre rondas es grande (±0,58). Para mejorarla: más parcelas, repartidas por todo el rango de biomasa (de 0 a lo más denso), y mejores variables.

> **Por qué un tercio de las variables.** En regresión, el bosque prueba en cada división un tercio de las variables elegidas al azar (Breiman, 2001). Si probara todas (*Variables por división* = *Todas*), sería *bagging* de árboles: en este ejemplo da R² 0,449, algo peor.

**Cómo interpretar la incertidumbre.** En regresión, la segunda salida de *Predecir ráster* es la **dispersión entre los árboles**, en las mismas unidades que la variable (kg/m²). Un valor alto indica una zona en la que los árboles no se ponen de acuerdo, típicamente donde hay combinaciones de valores poco representadas en las parcelas. Úsala para **comparar zonas**, no como margen de error: subestima la incertidumbre real y no es un intervalo de predicción.

**Restricciones propias de la regresión**
- El modelo **no extrapola**: nunca predice un valor mayor que el máximo medido en las parcelas ni menor que el mínimo.
- Si la columna tiene pocos valores distintos y son enteros (por ejemplo, un código del 1 al 5), el sistema la trata como clases. Fuerza **Regresión** en *Tipo de problema* si en realidad es una cantidad.
- Los polígonos pueden ser parcelas de campo, no hace falta que sean puros: una parcela es el valor medio de lo que hay dentro.

---

### Caso 7: Entrenar una vez y reutilizar el modelo

**Problema.** Cada mes recibes una imagen nueva de la misma zona y quieres actualizar el mapa publicado **sin tener que volver a dibujar muestras ni reentrenar**, y que la capa mantenga su dirección, permisos y leyenda.

**Idea.** Se separa en dos flujos:
- **Flujo de entrenamiento** (se ejecuta una vez, o cuando cambien las condiciones): termina en **Guardar modelo**.
- **Flujo de actualización** (se ejecuta con cada imagen): empieza en **Modelo guardado** y termina en **Publicar ráster** con *Reemplazar su ráster*.

**Flujo 1: entrenar y guardar**

```
 Ráster ─► Muestrear ráster ─► Random Forest ─► Guardar modelo
 Shapefile ──────────────────┘
```

| Nodo | Configuración |
|---|---|
| **Guardar modelo** | *Nombre del modelo* `cobertura_barranco` (el editor muestra cómo se guardará) · *Descripción* `Imagen de mayo 2026, 14 polígonos` · *Si el modelo ya existe*: **Añadir una versión nueva** |

**Flujo 2: actualizar cada mes**

```
 Ráster (imagen nueva) ─► Predecir ráster ─► Limpiar ráster ─► Publicar ráster
 Modelo guardado ───────────┘
```

| Nodo | Configuración |
|---|---|
| **Ráster (GeoTIFF)** | La imagen del mes, con **los mismos nombres de banda** (`Rojo, Verde, IR`). |
| **Modelo guardado** | *Modelo* `cobertura_barranco` · *Versión* **La última** |
| **Publicar ráster** | La misma capa de siempre, *Si la capa ya existe*: **Reemplazar su ráster**. |

**Qué pasa con el estilo.** Con *Estilo al reemplazar* = "Actualizarlo solo si cambian las clases o el rango" (por defecto): si las clases no cambian, no se toca; si cambian, se reescribe **conservando el color de las clases que ya existían**. Un estilo que hayas hecho tú a mano **no se toca nunca**.

**Cosas que conviene saber**

- **El modelo es privado** de quien lo guarda. Si un workspace guardado lo ejecuta otro usuario con permiso de ejecución, usa los modelos del **propietario del workspace**.
- **Versiones.** Cada guardado crea una versión (1, 2, 3…). Se conservan las 10 últimas. En *Modelo guardado* puedes elegir una versión concreta, por ejemplo para repetir un resultado antiguo.
- **Vuelve a entrenar** cuando cambien las condiciones: otro sensor, otra época del año con vegetación muy distinta, un tipo de cobertura nuevo. Un modelo de mayo puede fallar en noviembre.
- **El modelo está firmado.** Un fichero alterado o copiado a mano se rechaza. Si el administrador cambia la clave del servidor, los modelos antiguos dejan de ser válidos y hay que guardarlos de nuevo (ver [apartado 11](#11-para-el-administrador)).
- El editor comprueba, al elegir el modelo, **que la imagen tenga sus bandas**.

---

### Caso 8: Otros casos (recetas)

Son recetas con los nodos disponibles. No se han ejecutado con los datos de ejemplo, pero usan exactamente los mismos pasos. Para cada una: **qué muestrear, qué variables añadir y qué vigilar**.

#### 8.1 Láminas de agua y humedales

| | |
|---|---|
| **Clases** | `agua`, `no_agua` (o `agua`, `vegetacion`, `suelo`, `humedal`). |
| **Variables** | Las bandas + **NDWI** (índice *NDWI - agua*, con Verde y NIR). |
| **Postproceso** | *Limpiar ráster* con filtro de mayoría; *Ráster a polígonos* con *Clases a conservar* `agua`. |
| **Vigilar** | Las **sombras** de relieve y edificios se parecen al agua: dibuja muestras de sombra dentro de `no_agua`. El agua muy turbia se parece al suelo húmedo. Para medir la evolución, repite en varias fechas con *Modelo guardado*. |

#### 8.2 Zonas quemadas

| | |
|---|---|
| **Clases** | `quemado`, `no_quemado`. |
| **Variables** | Bandas + **diferencia normalizada** de NIR y SWIR (índice *Diferencia normalizada de dos bandas*, A = NIR, B = SWIR), o NDVI. |
| **Datos** | Imagen **posterior** al incendio. Para medir el cambio, combina la imagen anterior y la posterior con *Combinar ráster* (prefijos `antes` y `despues`) y clasifica directamente con muestras de zonas quemadas y no quemadas. |
| **Vigilar** | Distingue quemado de sombra y de suelo oscuro: muestrea ambos. |

#### 8.3 Suelo construido / impermeabilizado

| | |
|---|---|
| **Clases** | `construido`, `vegetacion`, `suelo_desnudo`, `agua`. |
| **Variables** | Bandas + **NDBI** (con SWIR y NIR) + **Brillo**. |
| **Postproceso** | *Ráster a polígonos* + intersección con barrios o cuencas (como en el caso 3) para obtener m² impermeables por zona. |
| **Vigilar** | Tejados oscuros y asfalto se parecen al agua; el suelo desnudo se parece a los tejados claros. Muchas muestras de cada. |

#### 8.4 Clasificación multitemporal (dos o más fechas)

1. Una entrada **Ráster (GeoTIFF)** por fecha, con los mismos nombres de banda.
2. **Combinar ráster**: la primera fecha en la entrada 1 (la de referencia) y las demás en las siguientes. En *Prefijo de las bandas del ráster*, `mayo` para la primera y `agosto` para la segunda: las bandas se llaman `mayo_rojo`, `agosto_rojo`, etc.
3. Sigue el flujo normal (muestrear, entrenar, predecir) con las bandas de ambas fechas como variables. Útil para cultivos (cambian durante el año) y para detección de cambios.
4. **Vigila** que las dos imágenes estén bien alineadas y con la misma radiometría (misma corrección atmosférica).

---

### Caso 9: Superficie con intervalo de confianza

**Problema.** Necesitas dar en un informe **cuántos metros cuadrados hay de cada clase**, con una cifra defendible y su margen de error. Contar los píxeles del mapa no vale: el recuento arrastra los errores de clasificación y no dice cuánto se equivoca.

**Idea.** Es el procedimiento recomendado internacionalmente para estimar superficies a partir de mapas (Olofsson et al., 2014):

1. Se elige una **muestra aleatoria estratificada** de puntos sobre el mapa: un número fijo de puntos al azar **dentro de cada clase del mapa**.
2. Se comprueba la **clase real** de cada punto (en campo, o mirando con cuidado una ortofoto de más detalle).
3. Con el cruce entre lo que dice el mapa y lo que es en realidad, se **corrige** la superficie de cada clase y se calcula su **intervalo de confianza**.

**Datos.** Una imagen y sus muestras de entrenamiento (como en el tutorial). En el ejemplo se usa el mapa del tutorial **sin limpiar**, que tiene errores dispersos: así se ve bien la corrección.

**Flujo 1: obtener el mapa y los puntos que hay que revisar**

```
 Ráster ─► Muestrear ─► Random Forest ─► Predecir ráster ─► Muestreo estratificado ─► PgSQL/PostGIS (puntos_referencia)
 Shapefile ──┘                           ▲
 Ráster ─────────────────────────────────┘
```

| Nodo | Configuración |
|---|---|
| **Muestreo estratificado** (Predictivo) | *Puntos por clase* `50` (lo mínimo recomendado; más puntos dan intervalos más estrechos) · *Semilla* `42` |
| **PgSQL/PostGIS** | Tabla `puntos_referencia`, operación *BORRAR Y CREAR* |

La tabla tiene una fila por punto con `id`, `map_class` (lo que dice el mapa), `map_code` y una columna **`reference` vacía**.

**Paso intermedio: anotar la clase real.** Abre la tabla `puntos_referencia` en QGIS o en el editor de capas de gvSIG Online, sobre una ortofoto de detalle, y escribe en `reference` la clase real de cada punto con **los mismos nombres de clase** (`agua`, `suelo`, `vegetacion`). Hazlo sin mirar `map_class` para no dejarte influir. Si de algún punto no puedes saberlo, déjalo vacío: se descarta y se avisa.

> **No vuelvas a ejecutar el Flujo 1 sobre la misma tabla** cuando ya la hayas anotado: *BORRAR Y CREAR* la sustituiría. Cambia el nombre de la tabla o quita el nodo de salida.

**Flujo 2: estimar las superficies**

```
 (el mismo mapa: misma imagen, mismas muestras, misma semilla) ─► Predecir ráster ─┐
                                                                                    ├─► Estimar superficies ─► PgSQL/PostGIS (2 tablas)
 PgSQL/PostGIS (entrada: puntos_referencia ya anotados) ────────────────────────────┘
```

El mapa tiene que ser **exactamente el mismo** sobre el que se sacaron los puntos. Como el entrenamiento usa una semilla fija, volver a ejecutar el mismo flujo da el mismo mapa; para más seguridad, guarda el modelo en el Flujo 1 (*Guardar modelo*) y úsalo aquí con *Modelo guardado*.

| Nodo | Configuración |
|---|---|
| **Estimar superficies** (Predictivo) | *Columna con la clase real* `reference` · *Nivel de confianza* `95 %` |

**Resultado con los datos de ejemplo** (en los datos de ejemplo la clase real se conoce, así que se puede comprobar):

| Clase | Recuento de píxeles del mapa | **Superficie estimada (50 puntos por clase)** | Intervalo del 95 % | Superficie real |
|---|---:|---:|---:|---:|
| Agua | 3 230 m² | **3 861 m²** | 1 332 – 6 391 m² | 2 999 m² |
| Suelo | 63 862 m² | **65 063 m²** | 61 993 – 68 134 m² | 65 217 m² |
| Vegetación | 22 908 m² | **21 075 m²** | 19 335 – 22 815 m² | 21 784 m² |

| Exactitud global | Estimada: **0,958 ± 0,034** | Real (comparando todo el mapa con la verdad): 0,955 |
|---|---|---|

- El mapa **sobrestima la vegetación** (22 908 m² frente a 21 784 reales). La muestra encontró 4 puntos de "vegetación" que eran suelo, y la estimación **corrige** la cifra hacia abajo. El intervalo **contiene** el valor real.
- El intervalo del **agua es muy amplio** (1 332 – 6 391 m²): de los 50 puntos de agua, 10 eran suelo. Con 100 puntos por clase la estimación del agua pasa a **3 190 m² (1 912 – 4 469)**, mucho más precisa.
- La tabla también da, por clase, la **exactitud del usuario** y **del productor** con su intervalo (por ejemplo, agua: usuario 0,80 ± 0,11).

**Columnas de la tabla de superficies:** `class`, `map_area` (recuento del mapa), `estimated_area`, `se_area` (error típico), `ci_low` y `ci_high` (intervalo), `users_accuracy` y `users_ci`, `producers_accuracy` y `producers_ci`, `samples` (puntos en esa clase del mapa) y `reference_samples` (puntos que en realidad son de esa clase). Las superficies van en las unidades del sistema de coordenadas al cuadrado (m² en UTM; divide por 10 000 para hectáreas).

**Buenas prácticas y límites**
- **50 puntos por clase** es el mínimo habitual; para clases pequeñas o que interesan mucho, pon más.
- La clase real debe anotarse con **una fuente de más calidad que el mapa** y con criterios claros escritos de antemano.
- Si la muestra **no encuentra ningún error**, el intervalo sale de anchura 0. Eso no significa que el mapa sea perfecto; el nodo avisa. Aumenta la muestra.
- El mapa debe estar en un sistema **proyectado**: el nodo rechaza los mapas en grados.
- Si una clase del mapa tiene menos de 2 puntos, no se puede calcular su varianza y el nodo lo indica.
- Para medir por **zonas** (tramos, municipios), repite el muestreo y la estimación dentro de cada zona, recortando antes el mapa con *Recortar ráster*.

---

## 7. Referencia de los nodos

En cada nodo: **para qué sirve**, **cómo se conecta**, **qué campos tiene** (con los nombres exactos del diálogo), **qué devuelve** y **cosas que conviene saber**.

### 7.1 Ráster (GeoTIFF)

**Para qué sirve.** Carga una imagen GeoTIFF para usarla en el flujo.
**Grupo:** Entradas. **Entradas:** ninguna. **Salida:** Ráster.

| Campo | Obligatorio | Descripción |
|---|---|---|
| **Fichero GeoTIFF** | Sí | Se elige con **Elige fichero** (abre el gestor de ficheros). |
| **Nombres de las bandas (opcional)** | No | Un nombre por banda. Aparecen al elegir el fichero. |

**Qué muestra.** Al elegir el fichero verás el resumen: número de bandas, sistema de coordenadas y tamaño (`3 bandas · EPSG:25830 · 300 × 300 px`).

**Cosas que conviene saber**

- El fichero debe estar en el **gestor de ficheros** y ser `.tif` / `.tiff`.
- **Los nombres de banda se normalizan** para poder usarlos como nombres de columna: minúsculas, sin tildes, espacios y símbolos pasan a `_`, y si empiezan por un número se les antepone `b_`. Si dos bandas se llaman igual, la segunda recibe `_2`. Una banda sin nombre se llama `b1`, `b2`…  Ejemplo: `Infrarrojo cercano` → `infrarrojo_cercano`.
- No copia el fichero: lo usa donde está durante la ejecución.
- Si supera el tamaño máximo configurado el nodo lo rechaza con un mensaje (ver [administrador](#11-para-el-administrador)).

### 7.2 Modelo guardado

**Para qué sirve.** Entrega un modelo que guardaste antes con **Guardar modelo**, para usarlo sin volver a entrenar.
**Grupo:** Entradas. **Entradas:** ninguna. **Salida:** Modelo (morado).

| Campo | Descripción |
|---|---|
| **Modelo** | Lista de tus modelos guardados. |
| **Versión** | **La última** (por defecto: siempre la más reciente, aunque guardes otra después) o una versión concreta. |

El diálogo muestra la **ficha del modelo** elegido: tipo (clasificación o regresión), fecha, filas de entrenamiento, variables, clases, métricas y descripción. Desde el diálogo se puede **Borrar esta versión** o **Borrar el modelo entero** (pide confirmación).

Ver [7.12](#712-guardar-modelo) para saber cómo se guardan, versionan y protegen.

### 7.3 Índice espectral

**Para qué sirve.** Añade a la imagen una **banda calculada** (un índice) a partir de otras. Las bandas originales se conservan, así que la nueva se usa luego como una variable más.
**Grupo:** Ráster. **Entrada:** Ráster. **Salida:** Ráster (con una banda más).

| Campo | Descripción |
|---|---|
| **Índice** | El índice a calcular (tabla siguiente). |
| *Bandas* (varían según el índice) | Una lista por cada papel del índice. **El nodo propone la banda más probable por su nombre** (`rojo`/`red`, `ir`/`nir`/`infrarrojo`, `verde`/`green`, `azul`/`blue`, `swir`). Puedes cambiarla. |
| **Nombre de la banda nueva** | Por defecto, el del índice. Si ya existe una banda con ese nombre, se le añade `_2`. |
| **Valores de la imagen** | Cómo convertir los valores de la imagen en reflectancia (0-1) antes de calcular. Ver abajo. |
| **Escala de reflectancia** y **Offset** | Solo con la conversión *Personalizada*. |
| **Ajuste del suelo (L)** | Solo en SAVI. De 0 a 1; `0,5` sirve en la mayoría de los casos (Huete, 1988). |

**Índices disponibles**

| Índice | Bandas | Fórmula | Para qué sirve | Referencia |
|---|---|---|---|---|
| **NDVI** | NIR, Rojo | (NIR − Rojo) / (NIR + Rojo) | Vegetación sana (valores altos). | Rouse et al., 1974 |
| **NDWI** | Verde, NIR | (Verde − NIR) / (Verde + NIR) | **Agua libre** (valores altos). | McFeeters, 1996 |
| **NDBI** | SWIR, NIR | (SWIR − NIR) / (SWIR + NIR) | Zonas construidas y suelo desnudo. SWIR = SWIR1 (≈ 1,6 µm: banda 11 de Sentinel-2, 6 de Landsat 8-9). | Zha, Gao y Ni, 2003 |
| **SAVI** | NIR, Rojo | (1 + L) · (NIR − Rojo) / (NIR + Rojo + L) | Como el NDVI, menos sensible al suelo desnudo. **Necesita reflectancia.** | Huete, 1988 |
| **EVI** | NIR, Rojo, Azul | 2,5 · (NIR − Rojo) / (NIR + 6·Rojo − 7,5·Azul + 1) | Vegetación densa (no se satura). **Necesita reflectancia de superficie.** | Huete et al., 2002 |
| **Brillo** | (todas) | Media de todas las bandas | Luminosidad general. Es una media simple, **no** el "brillo" del *tasseled cap*, que depende del sensor. | — |
| **Diferencia normalizada** | Banda A, Banda B | (A − B) / (A + B) | Cualquier otro índice normalizado, por ejemplo NBR (NIR, SWIR2) o el "NDWI de Gao" (NIR, SWIR1), que mide agua **en la vegetación**, no láminas de agua. | — |

**Valores de la imagen (conversión a reflectancia).** Se aplica a todas las bandas antes de calcular el índice: *reflectancia = (valor + offset) / escala*. Las bandas originales que se conservan en la salida no se modifican.

| Opción | Conversión | Cuándo |
|---|---|---|
| **Usarlos tal cual** | ninguna | La imagen ya está en reflectancia 0-1, o solo quieres una variable para clasificar. |
| **Imagen de 8 bits (0-255)** | valor / 255 | Ortofotos y otras imágenes de 8 bits. |
| **Sentinel-2 L2A desde 2022** | (valor − 1000) / 10 000 | Productos con línea base de procesado 04.00 o posterior (desde el 25 de enero de 2022). |
| **Sentinel-2 L2A anterior a 2022** | valor / 10 000 | Productos anteriores. |
| **Landsat Colección 2 nivel 2** | valor × 0,0000275 − 0,2 | Reflectancia de superficie de Landsat 4-9. |
| **Personalizada** | (valor + offset) / escala | Cualquier otro producto: consulta sus metadatos. |

**Por qué importa el offset.** Sin offset, los índices normalizados (NDVI, NDWI, NDBI…) dan lo mismo con o sin escala, porque la escala se anula al dividir. **Con offset ya no**: calcular un NDVI de Sentinel-2 de 2022 o de Landsat Colección 2 con los valores crudos da un resultado **sesgado**. SAVI y EVI necesitan siempre la conversión, porque mezclan constantes con las bandas.

**Rango válido del EVI.** El denominador del EVI puede acercarse a cero (agua, nubes, sombras o datos que no son reflectancia) y dar valores enormes. Los valores fuera de su rango físico, [−1, 1], se marcan **sin dato**.

**Las ortofotos no son reflectancia.** Las ortofotos (como las del PNOA) son valores de 8 bits con ajustes de color para que las hojas casen visualmente; no están calibradas radiométricamente. Un NDVI calculado con ellas es útil **como variable para clasificar esa imagen**, pero **no es un NDVI físico**: no se puede comparar entre hojas, fechas o sensores, ni usar como medida biofísica (vigor, biomasa…). Para eso hacen falta imágenes con reflectancia de superficie (Sentinel-2 L2A, Landsat Colección 2 nivel 2).

**Cosas que conviene saber**
- Para **varios índices**, encadena varios nodos *Índice espectral*.
- El resultado es `float32` con −9999 como sin dato; los píxeles con sin dato en alguna banda utilizada, con divisor cero o fuera del rango válido quedan sin dato en la banda nueva.
- No admite fórmulas libres a propósito (seguridad). Con *Diferencia normalizada* se cubre casi cualquier índice de dos bandas.
- Si añades un índice **antes de muestrear**, el mismo ráster con la banda nueva debe llegar a *Predecir ráster*.

### 7.4 Muestrear ráster

**Para qué sirve.** Convierte tus polígonos de ejemplo en una **tabla de entrenamiento**: una fila por píxel, una columna por banda y la clase.
**Grupo:** Predictivo. **Entradas:** 1.ª Ráster; 2.ª Muestras (tabla con polígonos y una columna de clase). **Salida:** Píxeles (tabla).

| Campo | Descripción |
|---|---|
| **Columna de clase** | Columna de las muestras con la clase de cada polígono (o un valor numérico, para regresión). |
| *Máximo de píxeles por clase* (avanzado) | Limita las clases muy grandes. Vacío = sin límite. |
| *Semilla aleatoria* (avanzado) | Para que la muestra sea la misma cada vez. Por defecto 42. |

**Ejemplo del resultado** (3 bandas, 14 polígonos):

| rojo | verde | ir | clase | (`__x`, `__y`, `__poly_id`) |
|---:|---:|---:|---|---|
| 132 | 118 | 71 | suelo | … |
| 49 | 102 | 177 | vegetacion | … |
| 35 | 60 | 22 | agua | … |

**Cómo decide qué píxeles entran**
- Un píxel entra si su **centro** cae dentro del polígono. Los que solo tocan el borde, no.
- Se descartan los píxeles con dato vacío en alguna banda, los polígonos sin clase y los que no tocan la imagen. Si **ninguno** toca la imagen, el nodo falla y sugiere revisar los sistemas de coordenadas.
- Si el sistema de coordenadas de las muestras y de la imagen son distintos, se **reproyecta automáticamente** (ambos deben estar definidos).

**Columnas internas.** Además de las bandas y la clase, la tabla lleva tres columnas auxiliares (`__x`, `__y`, `__poly_id`: posición del píxel y polígono de origen). **No aparecen en los desplegables** y **nunca se usan como variables**; sirven para la validación por polígonos y por bloques.

### 7.5 Random Forest

**Para qué sirve.** Entrena el modelo y mide su calidad.
**Grupo:** Predictivo. **Entrada:** Datos (tabla). **Salidas:** 1.ª **Informe** (tabla) · 2.ª **Modelo** (morado) · 3.ª **Matriz de confusión** (tabla).

#### Campos básicos

| Campo | Qué hace |
|---|---|
| **Variable a predecir** | La columna que quieres predecir. Si es texto o tiene pocos valores enteros, predice **clases**; si es un número continuo, **estima su valor**. |
| **Variables para predecir** | Casillas con las columnas numéricas disponibles; enlaces **Todas** / **Ninguna**. Por defecto, todas menos la variable a predecir. Deben ser **numéricas**. |

#### Parámetros avanzados

| Campo | Rango | Por defecto | Para qué sirve |
|---|---|---|---|
| **Tipo de problema** | Detectar automáticamente · Clasificación (categorías) · Regresión (número) | Automático | Fuerza el tipo si la detección no acierta. |
| **Número de árboles** | 1 – 2 000 | 100 | Más árboles = resultados más estables pero más lentos. 100-300 suele bastar. |
| **Profundidad máxima** | ≥ 1 o vacío | Sin límite | Limitarla evita que el modelo se aprenda los ejemplos de memoria (sobreajuste). |
| **Mínimo de muestras por hoja** | ≥ 1 | 1 | Subirlo suaviza el modelo; útil si las muestras son ruidosas. |
| **% reservado para evaluar** | 0 – 50 | 20 | Datos que no se usan para aprender sino para medir. 0 = no evalúa. Solo con *Reserva aleatoria*. |
| **Semilla aleatoria** | ≥ 0 | 42 | Mismos datos, misma semilla y mismo orden de variables = mismo modelo. |
| **Variables por división** | Automático · Raíz cuadrada · Un tercio · Todas (bagging) | Automático | Cuántas variables, elegidas al azar, prueba cada división de un árbol. *Automático* sigue a Breiman (2001): la raíz cuadrada del número de variables en clasificación y un tercio en regresión. *Todas* ya no es un bosque aleatorio sino *bagging* de árboles. |
| **Cómo se mide la calidad** | Automática · Reserva aleatoria · Dejar fuera polígonos de muestra · Dejar fuera bloques espaciales | Automática | Ver abajo. |
| **Número de rondas** | 2 – 10 | 5 | Solo al dejar fuera polígonos o bloques. |
| **Tamaño del bloque** | > 0 | — | Solo con bloques. Lado del bloque en las unidades del sistema de coordenadas de la imagen (metros en UTM). |

#### Cómo se decide si es clasificación o regresión

- Si la variable es **texto** o sí/no → **clasificación**.
- Si es un **número entero con 20 valores distintos o menos** → clasificación.
- Si es un número con valores enteros (aunque con decimales) y 20 distintos o menos → clasificación.
- En cualquier otro caso → **regresión**.

> Un código de clase (1, 2, 3) o un conteo de 0 a 5 se trata como **clasificación**. Si en realidad es una cantidad, fuerza **Regresión (número)**.

#### Cómo se mide la calidad

| Modo | Cómo funciona | Cuándo usarlo |
|---|---|---|
| **Automática** (por defecto) | Deja fuera polígonos de muestra si la tabla viene de *Muestrear ráster* y cada clase tiene al menos 2 polígonos; si no, usa la reserva aleatoria. El modo usado queda en el informe (sección `validation`). | Casi siempre. |
| **Reserva aleatoria** | Aparta al azar el % indicado y mide con él. | Tablas sin componente espacial (caso 5). **Optimista con píxeles de una imagen.** |
| **Dejar fuera polígonos de muestra** | Reparte los polígonos en *N* grupos. En cada ronda deja fuera un grupo de polígonos completos y mide con él. | **Recomendado para clasificar imágenes.** Mide la calidad en polígonos que el modelo no ha visto. |
| **Dejar fuera bloques espaciales** | Igual, pero reparte por celdas de una cuadrícula del tamaño indicado, sin tener en cuenta los polígonos. | Para medir si el modelo generaliza a zonas lejanas. Usa un bloque bastante mayor que tus polígonos. |

**Por qué importa.** Los píxeles vecinos se parecen muchísimo. Con la reserva aleatoria, cada píxel de evaluación tiene un "gemelo" casi idéntico en los de entrenamiento y la nota sale alta aunque el modelo falle en una zona nueva. Dejando fuera polígonos o bloques enteros, la medida es mucho más realista.

Detalles:
- El número de rondas se reduce si hay menos grupos que rondas.
- Las métricas se calculan juntando las predicciones de todas las rondas (cada fila se evalúa una vez), y además se informa de la nota de cada ronda y de su dispersión.
- Si una clase tiene muestras en **un solo** polígono (o bloque), no puede validarse por zonas: el nodo falla y dice cuál. Añade más polígonos de esa clase.
- Esos modos **necesitan la tabla de *Muestrear ráster***, que lleva la posición y el polígono de origen de cada píxel.
- El **modelo final siempre se vuelve a entrenar con todos los datos**; la validación solo estima la calidad.
- Base: Roberts et al. (2017) y Ploton et al. (2020) muestran que, con datos espaciales, la validación al azar sobrestima la calidad y que hay que separar el entrenamiento y la evaluación en el espacio. El tamaño de bloque ideal está relacionado con la distancia a la que los datos dejan de parecerse (autocorrelación espacial); si no la conoces, usa un bloque varias veces mayor que tus polígonos.

#### Qué hace con los datos

- Ignora las filas **sin valor** en la variable a predecir. En clasificación hacen falta **al menos 2 clases**.
- Descarta las filas con valores vacíos o no numéricos en las variables.
- Hacen falta **al menos 10 filas válidas** (20 para evaluar con reserva aleatoria; con menos, entrena sin evaluar).
- Si una variable es completamente no numérica, el nodo falla indicando cuál. Quítala de la selección.
- **Compensa las clases desiguales**: da más peso a las clases con menos ejemplos.
- Si hay más de **2 millones de filas**, entrena con una muestra y lo **avisa** (conserva todas las filas de las clases pequeñas).

#### Las tres salidas

**1. Informe** (`section`, `name`, `value`): ver [8.1](#81-el-informe). Incluye dos medidas de importancia de cada variable:
- **Por permutación** (`importance_permutation`): cuánto empeora la nota de evaluación (exactitud equilibrada, o R² en regresión) si se desordena esa variable. Se mide con los datos de evaluación, no con los de entrenamiento. **Es la que conviene mirar.**
- **Por impureza** (`importance`): la que calcula el propio bosque, que suma 1. Es rápida pero **sesgada**: favorece a las variables continuas y reparte la importancia entre variables correlacionadas (Strobl et al., 2007).

Ninguna de las dos indica causalidad.
**2. Modelo:** se conecta a **Predecir ráster**, **Predecir tabla** y **Guardar modelo**.
**3. Matriz de confusión:**
- *Clasificación:* una fila por clase real y una columna `pred_<clase>` por cada clase predicha, más `total` y `recall`. Los nombres se normalizan (`Vegetación` → `pred_vegetacion`).
- *Regresión:* tabla `metric`/`value` con `r2`, `rmse` y `mae`.
- Sin evaluación (porcentaje 0): tabla vacía.

> Las columnas `pred_*` solo se conocen al ejecutar, así que los nodos siguientes no las ofrecen en sus desplegables, aunque existen en la tabla resultante.

### 7.6 Predecir ráster

**Para qué sirve.** Aplica el modelo a **todos los píxeles** de la imagen.
**Grupo:** Predictivo. **Entradas:** 1.ª Ráster; 2.ª Modelo. **Salidas:** 1.ª **Resultado** · 2.ª **Seguridad**. **Campos:** ninguno.

El diálogo comprueba y avisa si la imagen **no tiene las bandas** con las que se entrenó el modelo.

| Salida | Qué es |
|---|---|
| **Resultado** | *Clasificación:* un ráster de códigos de clase (1, 2, 3…; el 0 es sin dato). *Regresión:* un ráster de valores estimados. |
| **Seguridad** | Se genera **siempre**; conéctala solo si la necesitas. *Clasificación:* la **proporción de votos** de los árboles para la clase elegida, de 0 a 1. *Regresión:* la **dispersión entre los árboles**, en las unidades de la variable. |

**Cómo interpretar la seguridad.**
- En clasificación es un **indicador relativo**: sirve para ver **dónde** el modelo duda (bordes, clases poco muestreadas) y priorizar la revisión. **No es una probabilidad calibrada**: un 0,9 no significa "acierta 9 de cada 10 veces". Las puntuaciones de un Random Forest no están calibradas (Niculescu-Mizil y Caruana, 2005), y el reequilibrado de clases que se aplica al entrenar las desplaza todavía más. La exactitud real se mide con *Evaluar clasificación* o, mejor, con *Estimar superficies*.
- En regresión, la dispersión entre árboles **subestima** la incertidumbre real: no es un intervalo de predicción. Úsala para comparar zonas, no como margen de error. (Un intervalo de predicción requeriría un *quantile regression forest*, Meinshausen, 2006, que no está incluido.)

**Cosas que conviene saber**
- Un píxel queda **sin dato** si alguna banda que usa el modelo no tiene valor.
- La imagen puede tener **más bandas** que el modelo (se ignoran las que sobran) pero **no menos**: los nombres de banda deben coincidir.
- Trabaja **por bloques**: no carga la imagen entera en memoria.

### 7.7 Ráster a polígonos

**Para qué sirve.** Convierte un ráster clasificado en **polígonos**: agrupa los píxeles contiguos de una clase.
**Grupo:** Ráster. **Entrada:** Ráster clasificado. **Salida:** Polígonos (tabla).

| Campo | Rango | Por defecto | Descripción |
|---|---|---|---|
| **Clases a conservar** | Nombres separados por comas | Vacío = todas | Por ejemplo `vegetacion` o `agua,vegetacion`. Si un nombre no existe, el nodo falla y dice cuáles hay. |
| **Área mínima** | ≥ 0 | 0 | Descarta polígonos más pequeños, en unidades **al cuadrado** del sistema de coordenadas (m² en UTM). **Es la forma más rápida de quitar ruido.** |
| *Simplificar* (avanzado) | ≥ 0 | 0 | Suaviza los bordes en escalera (en unidades del sistema de coordenadas). 0 = tal cual. |
| *Los píxeles son vecinos* (avanzado) | Solo por los lados (4) · También por las esquinas (8) | 4 | Con 8, los píxeles que solo se tocan en una esquina forman un solo polígono. |

**Columnas del resultado**

| Columna | Contenido |
|---|---|
| `class_name` | Nombre de la clase. |
| `class_code` | Código de la clase en el ráster. |
| `area` | Área del polígono, en unidades del sistema de coordenadas al cuadrado. |
| `wkb_geometry` | La geometría, con el EPSG de la imagen. |

**El efecto de limpiar**, con la vegetación del ejemplo (modelo con todas las variables del caso 2, que es el que más ruido da):

| Qué se hace antes de vectorizar | Polígonos de vegetación | Superficie |
|---|---:|---:|
| Nada | **873** | 20 537 m² |
| Solo área mínima de 25 m² | 2 | 19 520 m² |
| Solo filtro de mayoría 3 × 3 | 14 | 20 327 m² |
| Mayoría 3 × 3 + área mínima 25 m² | **2** | 20 310 m² |

Sin limpiar, el ruido de píxeles sueltos genera cientos de polígonos diminutos. Se recomienda **mayoría + área mínima**. (Con el modelo recomendado de 3 bandas + NDVI el resultado limpio son 5 polígonos y 21 781 m²).

**Cosas que conviene saber**
- El ráster debe tener **código EPSG**. Usa un sistema **proyectado** para que el área sea en metros.
- No admite ráster de regresión (no hay clases que vectorizar).
- Trabaja **por franjas**: admite ráster grandes sin agotar memoria.
- **El resultado es temporal.** Conéctalo a *PgSQL/PostGIS* para conservarlo.

### 7.8 Limpiar ráster

**Para qué sirve.** Quita el "ruido de sal y pimienta": píxeles sueltos mal clasificados dentro de una zona homogénea. Va entre *Predecir ráster* y *Ráster a polígonos* o *Publicar ráster*.
**Grupo:** Ráster. **Entrada:** Ráster **clasificado**. **Salida:** Ráster clasificado.

| Campo | Valores | Por defecto |
|---|---|---|
| **Método** | **Filtro de mayoría (suaviza)** · **Tamaño mínimo de parche (conserva los bordes)** | Mayoría |

**Método: Filtro de mayoría.** Cada píxel pasa a tener la clase más frecuente de sus vecinos.

| Campo | Valores | Por defecto | Descripción |
|---|---|---|---|
| **Ventana** | 3 × 3 · 5 × 5 · 7 × 7 | 3 × 3 | Más grande limpia más, pero difumina zonas pequeñas y estrecha los elementos lineales (cauces, caminos). |
| **Repeticiones** | 1 – 5 | 1 | Aplicarlo varias veces elimina manchas más grandes. |

En caso de empate, el píxel conserva su clase. Los píxeles sin dato no se rellenan.

**Método: Tamaño mínimo de parche.** Elimina los grupos de píxeles conectados más pequeños que el umbral: los absorbe el vecino más grande. **No altera los bordes** de las zonas grandes.

| Campo | Valores | Por defecto |
|---|---|---|
| **Tamaño mínimo del parche (píxeles)** | ≥ 2 | 4 |
| **Los píxeles son vecinos** | Solo por los lados (4) · También por las esquinas (8) | 4 |

**¿Cuál elegir?** Mayoría para ruido disperso en general. Tamaño mínimo de parche si quieres conservar los bordes exactos y solo quitar islotes. Se pueden encadenar los dos. **Mayoría 3 × 3, una vez, suele ser suficiente**: subir la ventana difumina lo que quieres conservar.

**Cosas que conviene saber:** solo funciona con ráster **clasificados** (salida de *Predecir ráster*); el método de tamaño mínimo de parche carga la imagen entera en memoria y tiene un límite de tamaño (el de mayoría trabaja por bloques).

### 7.9 Combinar ráster

**Para qué sirve.** Une las bandas de **varios ráster** (de 2 a 4) en uno solo. Por ejemplo, una ortofoto y un modelo del terreno que están en ficheros distintos y con distinta resolución.
**Grupo:** Ráster. **Entradas:** *Ráster 1 (referencia)*, *Ráster 2*, *Ráster 3*, *Ráster 4* (conecta cada ráster a una entrada distinta; deja vacías las que no uses). **Salida:** Ráster.

| Campo | Descripción |
|---|---|
| **Remuestreo** | **Bilineal** (por defecto): suave, para imágenes y valores continuos. **Vecino más próximo**: conserva los valores originales; el adecuado para clases. |
| **Prefijo de las bandas del ráster** (uno por ráster conectado) | Opcional. Se antepone a los nombres de banda (`mayo` + `rojo` = `mayo_rojo`). Útil cuando hay bandas con el mismo nombre. |

**Cómo funciona**
- **El primer ráster conectado es la referencia:** el resultado tiene su sistema de coordenadas, su extensión y su tamaño de píxel. Los demás se **reproyectan y remuestrean** a esa cuadrícula.
- Donde un ráster **no cubre** la referencia, sus bandas quedan **sin dato**. Si un ráster no se solapa nada, el nodo falla y lo dice.
- Todos deben tener sistema de coordenadas.
- Los nombres de banda se normalizan; si se repiten, la segunda recibe `_2`, etc. (por eso conviene usar prefijos).
- Resultado `float32`, −9999 como sin dato. Procesa por bloques.

**Ejemplo:** `ortofoto.tif` (3 bandas, píxel de 1 m) + `terreno.tif` (banda `Altura`, píxel de 2 m) → un ráster de 4 bandas (`rojo, verde, ir, altura`) a 1 m. El terreno se remuestrea de 2 m a 1 m.

> Mira en el [caso 2](#cuándo-una-variable-que-mejora-la-nota-empeora-el-mapa) por qué conviene comprobar que una variable nueva mejora el mapa antes de usarla.

### 7.10 Evaluar clasificación

**Para qué sirve.** Mide la calidad de un ráster clasificado con **muestras de validación independientes**.
**Grupo:** Predictivo. **Entradas:** 1.ª Ráster **clasificado**; 2.ª Muestras de validación (tabla con polígonos **o puntos** y la clase real). **Salidas:** 1.ª Informe (tabla); 2.ª Matriz de confusión (tabla).

| Campo | Descripción |
|---|---|
| **Columna de clase** | Columna de las muestras de validación con la clase real. |

**Cosas que conviene saber**
- Con **polígonos** se evalúan todos sus píxeles; con **puntos**, el píxel que los contiene. Se pueden mezclar. Las líneas y geometrías vacías se ignoran y se cuentan.
- Las muestras se reproyectan al sistema de la imagen. Las que quedan fuera, se cuentan aparte.
- Los píxeles **sin clasificar** no cuentan en las métricas, pero se informan.
- Una clase de validación que el modelo no conoce **cuenta siempre como error** y se avisa.
- El informe usa el mismo formato que el de *Random Forest* y añade la sección `assessment` (píxeles evaluados, sin clasificar, unidades de muestreo…) y la sección `ci` con **intervalos del 95 %** de la exactitud global y de la precisión y el recall de cada clase, por *bootstrap* de muestras enteras (1 000 repeticiones).
- Para que sea una evaluación válida, las muestras deben ser **distintas** de las de entrenamiento y cubrir bordes y casos raros (ver [caso 4](#caso-4-evaluar-el-mapa-con-muestras-independientes)).
- Para una exactitud **estadísticamente inferible al mapa**, las muestras deben venir de un muestreo aleatorio estratificado (*Muestreo estratificado*) y es mejor usar *Estimar superficies*, que pondera cada clase por su superficie. Con polígonos dibujados a mano, el resultado es solo orientativo.

### 7.11 Predecir tabla

**Para qué sirve.** Aplica un modelo a **cada fila de una tabla** (parcelas, puntos, tramos…).
**Grupo:** Predictivo. **Entradas:** 1.ª Datos (tabla); 2.ª Modelo. **Salida:** Tabla.

| Campo | Descripción |
|---|---|
| **Nombre de la columna de predicción** | Por defecto `prediction`. La seguridad del modelo va en otra columna con el mismo nombre seguido de `_confidence` (proporción de votos en clasificación, dispersión entre árboles en regresión; ver [7.6](#76-predecir-ráster)). No deben existir ya en la tabla. |

**Cosas que conviene saber**
- Devuelve **la misma tabla, con todas sus columnas, la geometría y sus tipos**, más las dos columnas nuevas. La tabla de entrada no se modifica.
- La tabla debe tener **las columnas con las que se entrenó el modelo**, con el mismo nombre. El diálogo avisa de las que faltan.
- Las filas con valores **vacíos o no numéricos** en las variables se quedan sin predicción (`NULL`); la ejecución indica cuántas.
- Las clases enteras se guardan como número, las de texto como texto y la regresión como decimal.
- Se ejecuta en una sola transacción: si falla, no queda nada a medias.
- Lee las variables de **toda la tabla** a la vez: va bien con cientos de miles de filas; con muchos millones, hazlo por partes.
- El modelo puede venir de *Random Forest* (mismo flujo) o de *Modelo guardado*.

### 7.12 Guardar modelo

**Para qué sirve.** Guarda el modelo de forma **permanente** para reutilizarlo.
**Grupo:** Salidas. **Entrada:** Modelo. **Salidas:** ninguna.

| Campo | Descripción |
|---|---|
| **Nombre del modelo** | Se guarda en minúsculas, con dígitos y guion bajo (máx. 60). El editor muestra *Se guardará como: …*. |
| **Descripción** | Opcional: la imagen, la fecha, las muestras… |
| **Si el modelo ya existe** | **Añadir una versión nueva** (por defecto; conserva las anteriores) · **Reemplazarlo** (borra las versiones anteriores) · **Parar con un error**. |

**Cómo funciona**

- Cada guardado crea una **versión** numerada (1, 2, 3…). Por defecto se conservan las **10 últimas**.
- Cada versión guarda el modelo y sus **metadatos**: variables, clases, métricas de validación, parámetros, filas de entrenamiento y las versiones de las librerías con que se entrenó.
- **Privado por usuario.** Cada usuario ve y usa solo sus modelos. Al ejecutar un workspace guardado, se usan los del **propietario del workspace**.
- **Seguridad.** Un fichero de modelo manipulado podría ejecutar código, así que el servidor **solo carga modelos que él mismo ha firmado**. Al guardar se calcula la huella del fichero y se firma junto con todos sus metadatos; al cargar se verifican las dos cosas. Un modelo modificado, copiado de otro usuario o renombrado se **rechaza** con un mensaje claro.
- **Compatibilidad.** Si el servidor se actualizó y tiene otra versión de las librerías de aprendizaje que la del entrenamiento, el sistema avisa; si ya no se puede leer, el mensaje pide volver a entrenar.
- **Dónde.** En una carpeta oculta del gestor de ficheros, organizada por usuario y modelo (el administrador puede cambiarla).

### 7.13 Publicar ráster

**Para qué sirve.** Publica el mapa como una **capa de gvSIG Online**, con estilo automático, lista para añadir a un proyecto.
**Grupo:** Salidas. **Entrada:** Ráster. **Salidas:** ninguna.

| Campo | Obligatorio | Descripción |
|---|---|---|
| **Workspace** | Sí | Donde se crea la capa. Se elige de una lista; debe existir y debes tener permiso. |
| **Grupo de capas** | Sí | Grupo donde se incluye. Se elige de una lista; debe existir. |
| **Título de la capa** | No | El nombre visible. |
| **Nombre de la capa** | Sí | Nombre técnico (minúsculas, dígitos y `_`). Se propone a partir del título. Máx. 60 caracteres. |
| **Si la capa ya existe** | — | **Reemplazar su ráster** (por defecto) o **Parar con un error**. |
| **Capa pública** | No | Por defecto es privada. |

**Parámetros avanzados**

| Campo | Descripción |
|---|---|
| **Estilo al reemplazar** | **Actualizarlo solo si cambian las clases o el rango** (por defecto) · **Regenerarlo siempre** · **No tocarlo nunca**. |
| **Banda a publicar** | Solo aparece si el ráster tiene varias bandas. Por defecto se publica tal cual. |
| **Rampa de color: mínimo / máximo** | Fija el rango de colores de un ráster de **valores**. Rellena los dos o ninguno; el máximo debe ser mayor. La seguridad del modelo va siempre de 0 a 1. |
| **Descripción de la capa** | Texto opcional que se guarda como resumen de la capa. |

**El estilo**

| Tipo de ráster | Estilo automático |
|---|---|
| **Clasificado** | Un color por clase (paleta apta para daltonismo) y la leyenda con el nombre de cada clase. |
| **De valores** (regresión, incertidumbre) | Rampa de blanco a verde oscuro entre el mínimo y el máximo. |
| **De seguridad del modelo** (salida 2 de *Predecir ráster*) | La misma rampa, fija de 0 a 1. |

**Al reemplazar una capa existente**

- Cambia **solo el ráster**; la capa conserva su grupo y sus permisos.
- El estilo **propio** del nodo (el que se llama `<workspace>_<capa>_classes`) se actualiza si cambian las clases o el rango. **Las clases que ya existían conservan su color**, aunque cambie el orden o aparezcan clases nuevas.
- Un estilo hecho por ti **no se toca nunca**.
- La actualización del estilo es atómica; y si el ráster ya se había reemplazado y el estilo falla, la publicación no se estropea: se avisa para que revises el estilo.
- Requiere permiso para gestionar la capa y que sea una capa ráster GeoTIFF.

Si la publicación falla al crear una capa nueva, el nodo **deshace** lo que haya creado, sin dejar elementos a medias.

### 7.14 Recortar ráster

**Para qué sirve.** Se queda solo con tu **zona de estudio**: recorta la imagen con una **capa de polígonos** (la máscara) y, si quieres, **cambia a la vez el tamaño de píxel**. Es el primer paso recomendado con imágenes grandes.
**Grupo:** Ráster. **Entradas:** 1.ª Ráster; 2.ª **Máscara** (tabla con los polígonos de recorte: un shapefile, una capa PostGIS…). **Salida:** Ráster.

| Campo | Valores | Por defecto | Descripción |
|---|---|---|---|
| **Qué conservar** | **Solo dentro de los polígonos** · **El rectángulo que los contiene** | Solo dentro de los polígonos | El primero deja **sin dato** lo que queda fuera de los polígonos; el segundo solo corta la imagen al rectángulo que los contiene. |
| **Nuevo tamaño de píxel** | Número > 0 o vacío | Vacío (mantener el original) | En las unidades del sistema de coordenadas de la imagen (metros en UTM). `1` en una ortofoto de 25 cm da **16 veces menos píxeles**. |
| **Remuestreo al cambiar el tamaño** (avanzado) | **Media** · **Bilineal** · **Vecino más próximo** | Media | La media es la mejor forma de reducir. |

**Cómo funciona**

- La máscara se **reproyecta automáticamente** al sistema de coordenadas de la imagen. Se usan solo los polígonos; los puntos y líneas se ignoran. Si hay varios polígonos, se recorta a su extensión conjunta.
- **Sin cambiar el tamaño de píxel**, el recorte se ajusta a la malla de la imagen original, sin remuestrear ni mover los píxeles.
- Si la máscara **sobresale** de la imagen, se recorta a la zona común. Si **no se solapa** nada, el nodo falla y lo dice.
- **Conserva el tipo de dato y las bandas.** Una ortofoto de 8 bits sigue siendo de 8 bits (no se convierte a decimal), así que el resultado ocupa poco, y los nombres de banda pasan tal cual. Funciona con las ortofotos del PNOA (JPEG con color YCbCr).
- Un ráster **de clases** (salida de *Predecir ráster*) usa siempre vecino más próximo al cambiar de tamaño, para no inventar clases intermedias, y conserva sus clases.
- Procesa **por bloques**: no carga la imagen entera en memoria.

**Sobre el valor de sin dato.** Si la imagen no declara un valor de sin dato, el nodo usa **0** en las de enteros sin signo (lo habitual en ortofotos) para marcar lo que queda fuera de la máscara, y lo **avisa**. Cuidado: en ese caso un píxel negro puro (0 en la banda) dentro de la zona también se tratará como sin dato. En ortofotos reales es muy raro. Si prefieres no tener este problema, usa el modo **El rectángulo que los contiene**, que no marca nada.

**Ejemplo con el PNOA** (imagen de 58 880 × 38 912 píxeles a 25 cm):

| Operación | Resultado |
|---|---|
| Un cuadrado de 1 km a 1 m, con máscara triángulo | 1 000 × 1 000 píxeles, 1 MB, 0,1 s |
| Un cuadrado de 1 km sin cambiar el tamaño de píxel | 4 000 × 4 000 píxeles, 36 MB, 1,8 s |
| Un cuadrado de 2 km a 1 m | 2 000 × 2 000 píxeles, 9 MB, 0,6 s |

**Flujo típico con una imagen grande**

```
 Ráster (PNOA, 25 cm) ─► Recortar ráster (zona de estudio, 1 m) ─► Índice espectral ─► Muestrear / Predecir ...
 Shapefile (zona) ───────────────┘
```

### 7.15 Muestreo estratificado

**Para qué sirve.** Elige **puntos al azar dentro de cada clase** de un mapa clasificado, para comprobar después su clase real. Es el diseño de muestreo que da validez estadística a la exactitud y a las superficies (Olofsson et al., 2014). Se usa junto con *Estimar superficies* ([caso 9](#caso-9-superficie-con-intervalo-de-confianza)).
**Grupo:** Predictivo. **Entrada:** Ráster **clasificado**. **Salida:** Puntos (tabla).

| Campo | Por defecto | Descripción |
|---|---|---|
| **Puntos por clase** | 50 | Al menos 2; se recomiendan 50 o más. Con más puntos, los intervalos son más estrechos. Una clase con menos píxeles que puntos aporta todos sus píxeles. |
| *Semilla aleatoria* (avanzado) | 42 | La misma semilla da siempre los mismos puntos. |

**Cómo funciona**
- Todos los píxeles de una clase tienen **la misma probabilidad** de salir, y cada píxel sale como mucho una vez. Los píxeles sin dato no se muestrean.
- Cada punto está en el **centro** de su píxel.
- Recorre el mapa por bloques, así que funciona con mapas grandes.

**Tabla de salida**

| Columna | Contenido |
|---|---|
| `id` | Número de punto. |
| `map_class` · `map_code` | Lo que dice el mapa en ese punto. |
| `reference` | **Vacía**: aquí se escribe la clase real. |
| `wkb_geometry` | El punto, con el EPSG del mapa. |

Guárdala con *PgSQL/PostGIS* y anota `reference` en QGIS o en el editor de gvSIG Online.

### 7.16 Estimar superficies

**Para qué sirve.** Estima la **superficie real de cada clase**, corrigiendo los errores del mapa con puntos de referencia, y da su **intervalo de confianza**, junto con las exactitudes del usuario y del productor y la exactitud global con sus intervalos. Aplica el estimador estratificado de Olofsson et al. (2014). Es la forma recomendada de **dar superficies en un informe**.
**Grupo:** Predictivo. **Entradas:** 1.ª Ráster **clasificado**; 2.ª Puntos de referencia (tabla de **puntos** con la clase real). **Salidas:** 1.ª **Superficies** (tabla); 2.ª **Informe** (tabla).

| Campo | Por defecto | Descripción |
|---|---|---|
| **Columna con la clase real** | `reference` si existe | La columna donde anotaste la clase real de cada punto. |
| **Nivel de confianza** | 95 % | 90 %, 95 % o 99 %. |

**Cómo funciona**
- Cuenta los píxeles de cada clase del mapa (los "estratos") y toma, para cada punto, la clase del mapa **del propio ráster** (no de la tabla).
- Con el cruce mapa/realidad calcula la proporción de superficie de cada clase real, su error típico y el intervalo (± 1,96 errores típicos al 95 %).
- Los puntos sin clase real, fuera del mapa o en píxeles sin dato se descartan y se cuentan en el informe.
- Una clase real que el mapa no tiene también recibe superficie estimada (y su exactitud del usuario queda vacía).

**Requisitos**
- Puntos de una **muestra aleatoria estratificada por clase del mapa** (la de *Muestreo estratificado*). Con polígonos el nodo se niega: cada polígono no es una unidad de muestreo independiente.
- Al menos **2 puntos en cada clase del mapa** (se recomiendan 50).
- Mapa en un sistema de coordenadas **proyectado**; las superficies salen en sus unidades al cuadrado (m² en UTM).
- El mapa debe ser **el mismo** sobre el que se sacaron los puntos.

**Tablas de salida**
- *Superficies:* `class`, `map_area`, `estimated_area`, `se_area`, `ci_low`, `ci_high`, `users_accuracy`, `users_ci`, `producers_accuracy`, `producers_ci`, `samples`, `reference_samples` (ver [caso 9](#caso-9-superficie-con-intervalo-de-confianza)).
- *Informe:* `overall_accuracy`, `overall_accuracy_ci`, `total_area`, `samples`, puntos descartados y nivel de confianza. Si la muestra no tiene ningún error, añade `no_errors_in_sample` y avisa de que el intervalo de anchura 0 no es realista.

**Comprobado** con el ejemplo resuelto del artículo de Olofsson et al. (2014): reproduce sus superficies estimadas y sus exactitudes.

---

## 8. Cómo saber si el resultado es bueno

### 8.1 El informe

La salida **Informe** de *Random Forest* (y de *Evaluar clasificación* y *Estimar superficies*) es una tabla de tres columnas: `section`, `name`, `value`. Se puede guardar con *PgSQL/PostGIS*. Estas son sus secciones:

| `section` | `name` | Qué es |
|---|---|---|
| `validation` | `auto`→ `polygon`, `random` o `block` | Cómo se ha medido la calidad (el modo realmente usado). |
| `class_balance` | Cada clase | Cuántas filas (píxeles) hay de cada clase. |
| `training` | `rows` | Filas con las que entrenó (o evaluó). |
| `training` | `test_rows` | Filas con las que midió. |
| `training` | `folds`, `groups` | Rondas y número de polígonos/bloques (solo en validación espacial). |
| `metric` | `accuracy` | **Exactitud global**: fracción de aciertos. |
| `metric` | `balanced_accuracy` | Exactitud media por clase (no engaña con clases muy desiguales). |
| `metric` | `f1_weighted` | F1 ponderado por el tamaño de cada clase. |
| `metric` | `kappa` | Se incluye por compatibilidad; desaconsejado para valorar mapas (ver 8.2). |
| `metric` | `fold_score_std` | Cuánto varía la nota entre rondas. |
| `metric` | `r2`, `rmse`, `mae` | Solo en regresión. |
| `fold` | `fold_1`… | Nota de cada ronda. |
| `per_class` | `<clase>:precision`, `:recall`, `:f1`, `:support` | Métricas de cada clase. |
| `confusion` | `<real> -> <predicha>` | Número de muestras por cada par. |
| `importance_permutation` | Cada variable | Cuánto empeora la nota de evaluación al desordenar la variable. **La importancia recomendada.** |
| `importance` | Cada variable | Importancia por impureza (suman 1). Sesgada; solo orientativa. |
| `assessment` | `validation_pixels`, `unclassified_pixels`, `sample_units`… | Solo en *Evaluar clasificación*. |
| `ci` | `accuracy:low`, `accuracy:high`, `<clase>:recall:low`… | Intervalos del 95 % por bootstrap de muestras (solo en *Evaluar clasificación*). |
| `area_estimation` | `overall_accuracy`, `overall_accuracy_ci`, `total_area`… | Solo en *Estimar superficies*. |

### 8.2 Cómo leer cada métrica

| Métrica | Cómo se lee | Cuidado con… |
|---|---|---|
| **Exactitud** (`accuracy`) | "Acertó el 95 % de los píxeles." Fácil de entender. | Engaña si una clase domina: con un 90 % de suelo, decir siempre "suelo" da 90 %. Mírala junto a la exactitud equilibrada y a las de cada clase. |
| **Exactitud equilibrada** | La media de lo bien que va cada clase por separado. | Es la nota justa si hay clases desiguales. |
| **Precisión de una clase** (exactitud del usuario) | De lo que el mapa dice que es vegetación, cuánto lo es de verdad. | Baja = el mapa **sobrestima** esa clase. |
| **Recall de una clase** (exactitud del productor) | De lo que realmente es vegetación, cuánto encuentra el mapa. | Baja = el mapa **infraestima** esa clase. |
| **F1** | Resume precisión y recall en un número. | |
| **Matriz de confusión** | Qué clases se confunden con cuáles. | Es la herramienta más útil para saber **qué muestras añadir**. |
| **Intervalos** (`ci`, `overall_accuracy_ci`) | El rango en el que, con un 95 % de confianza, está el valor real. | Un intervalo ancho significa **pocas muestras**: la cifra central es poco segura. |
| **Kappa** | Se incluye por compatibilidad con informes antiguos. | **No lo uses para valorar el mapa**: depende de las proporciones de las clases, se confunde con la exactitud y sus umbrales clásicos ("> 0,8 muy bueno") no tienen fundamento para mapas (Pontius y Millones, 2011; Foody, 2020). |
| **Importancia por permutación** | Cuánto empeora la nota si se "rompe" una variable. | No es causalidad. Si dos variables se parecen mucho, cada una puede salir baja porque la otra la sustituye. |
| **Importancia por impureza** | La que calcula el propio bosque (suma 1). | **Sesgada** hacia variables continuas y correlacionadas (Strobl et al., 2007). Solo orientativa. |
| **R², RMSE, MAE** (regresión) | R² cercano a 1 = buen ajuste. RMSE y MAE están en las unidades de la variable. | |

### 8.3 Cómo desconfiar de una nota demasiado buena

| Señal | Qué puede pasar | Qué hacer |
|---|---|---|
| 98-99 % con **reserva aleatoria** | Espejismo: vecinos de entrenamiento y de evaluación. | Repite con **Dejar fuera polígonos de muestra**. |
| Notas muy distintas entre **rondas** (0,55 … 0,99) | Pocos polígonos: la nota depende de cuáles caen fuera. | Añade polígonos de ejemplo; usa más muestras de validación. |
| 100 % en **Evaluar clasificación** | Muestras de validación pequeñas, puras y fáciles. | Añade bordes, transiciones y casos raros; mejor, usa *Muestreo estratificado*. |
| Intervalo de **anchura 0** en *Estimar superficies* | La muestra no ha encontrado ningún error. | No significa mapa perfecto: aumenta los puntos por clase. |
| Nota alta pero el **mapa** no cuadra con el terreno | Una variable que solo correlaciona en tus muestras (caso de la altura). | Compara el mapa con y sin esa variable; mira el mapa. |
| Una clase con **recall muy bajo** | Pocos o poco variados ejemplos de esa clase. | Más muestras de esa clase (en la matriz verás con cuál se confunde). |

### 8.4 Una lista de comprobación antes de dar el mapa por bueno

1. ¿Tengo ejemplos de **todas** las clases que hay en la imagen?
2. ¿He medido con **polígonos fuera** o con **muestras independientes**, no solo con reserva aleatoria?
3. ¿Las notas **por clase** son aceptables, no solo la global?
4. ¿He mirado el **mapa** y las zonas donde el modelo está **menos seguro**?
5. ¿Las muestras de validación incluyen **bordes y casos raros**?
6. Si voy a dar **superficies**, ¿las he estimado con una **muestra estratificada** y su intervalo (*Estimar superficies*), en lugar de contar píxeles?
7. Si uso **índices espectrales**, ¿he convertido bien la imagen a reflectancia, y tengo claro que con ortofotos no son medidas físicas?

---

## 9. Buenas prácticas

### Muestras

- **Calidad antes que cantidad:** recuadros sobre zonas homogéneas, lejos de los bordes.
- Varios polígonos por clase (mínimo 3-5, mejor decenas), repartidos por toda la zona.
- Toda la **variedad** de cada clase.
- Una clase para **todo lo demás** presente en la imagen.
- Unos cientos de píxeles por clase; si hay clases muy desiguales, usa *Máximo de píxeles por clase* (por ejemplo, 5 000).
- Las muestras deben tomarse sobre la **misma imagen** (o una de condiciones muy parecidas) a la que se aplica el modelo.

### Variables

- Empieza con las **bandas originales**. Añade un índice (NDVI, NDWI…) si la clase se define por vegetación, agua o suelo.
- **Más variables no siempre es mejor.** Comprueba el efecto (caso 2). Mira la importancia y quita las que no aportan.
- Si SAVI o EVI dan valores raros, revisa la **conversión a reflectancia** (*Valores de la imagen*). Con Sentinel-2 posterior a 2022 o Landsat Colección 2, elige su opción: tienen offset.

### Validación

- Para imágenes, mide **dejando fuera polígonos de muestra** (es lo que hace la opción automática). La reserva aleatoria, solo para tablas sin componente espacial.
- Mira la **matriz de confusión** y añade muestras de las clases que se confunden.
- Con **bloques**, usa un tamaño mayor que tus polígonos (por ejemplo, el doble) y que haya varios bloques por clase.
- Para la nota final y las superficies de un informe, usa una **muestra aleatoria estratificada** (*Muestreo estratificado* + *Estimar superficies*).

### Parámetros del modelo

Los valores por defecto (100 árboles, sin profundidad máxima) funcionan bien casi siempre. Cámbialos solo si el informe lo aconseja:

| Síntoma | Qué probar |
|---|---|
| Nota muy alta al entrenar pero mala al dejar polígonos fuera (sobreajuste) | Reducir la **Profundidad máxima** o subir el **Mínimo de muestras por hoja**. |
| Resultados que cambian mucho entre ejecuciones | Subir el **Número de árboles** (y mantener la semilla). |
| Una clase pequeña se pierde | Más muestras de esa clase; no tocar parámetros. |

### Postproceso

- **Mayoría 3 × 3** una vez suele bastar. Más ventana o más repeticiones difuminan lo pequeño.
- Para vectorizar, combina **Limpiar ráster** + **Área mínima** (la superficie de 5-10 píxeles, por ejemplo).
- Publica también el mapa de **seguridad** junto al clasificado: muestra dónde el modelo duda (es un indicador relativo, no una probabilidad).

---

## 10. Resolución de problemas

### 10.1 "No me deja…" (el editor)

| Problema | Causa | Solución |
|---|---|---|
| Un desplegable está vacío | El nodo anterior no está aceptado o no está conectado | Configura los nodos de izquierda a derecha. |
| No puedo conectar dos nodos | Los tipos de puerto no coinciden (tabla/ráster/modelo) | Mira los colores: solo se conectan puertos del mismo color. |
| *Predecir ráster* no me deja elegir nada | No tiene parámetros: está bien. | Solo comprueba el mensaje de bandas que muestra. |
| La rueda sigue roja tras pulsar Aceptar | El diálogo mostró un error | Lee el mensaje en rojo dentro del diálogo y corrígelo. |
| Los nodos nuevos no aparecen | Caché del navegador | **Ctrl+F5** para recargar el editor. |

### 10.2 Errores al ejecutar

| Mensaje | Causa | Solución |
|---|---|---|
| *Hay nodos sin configurar…* | Algún nodo con rueda roja. | Ábrelo, revísalo y pulsa **Aceptar**. |
| *El fichero debe estar en el gestor de ficheros.* | El GeoTIFF está fuera. | Súbelo al gestor y elígelo desde ahí. |
| *El fichero debe ser un GeoTIFF (.tif / .tiff).* | Otra extensión. | Convierte el fichero. |
| *Ningún polígono de muestra intersecta con el ráster…* | Sistemas de coordenadas mal definidos o muestras fuera de la imagen. | Revisa el EPSG y que se solapen. |
| *La columna de clase "x" coincide con el nombre de una banda.* | Clase y banda se llaman igual. | Renombra una. |
| *La variable predictora "x" no es numérica.* | Se marcó una columna de texto. | Desmárcala. |
| *Se necesitan al menos 2 clases distintas…* | Solo hay una clase. | Añade muestras de otras clases. |
| *Hay N filas válidas para entrenar y se necesitan al menos 10.* | Muy pocas muestras. | Añade polígonos. |
| *La clase "x" solo tiene muestras en 1 de los polígonos de muestra…* | Validación espacial con una clase de un único polígono. | Más polígonos de esa clase, o usa la reserva aleatoria. |
| *Solo hay 1 bloques…* | El bloque es mayor que la zona. | Reduce el tamaño del bloque. |
| *La validación por polígono necesita la tabla que genera "Muestrear ráster"…* | La tabla no viene de *Muestrear ráster*. | Conecta *Random Forest* a *Muestrear ráster*. |
| *El ráster no tiene las bandas con las que se entrenó el modelo…* | Ráster distinto al del entrenamiento. | Usa el mismo ráster (con los mismos índices) en *Muestrear* y *Predecir*. |
| *El ráster no es una clasificación…* / *El filtro solo se aplica a un ráster clasificado.* | Se conectó un ráster que no es la clasificación. | Conecta la salida **Resultado** de un modelo de clasificación. |
| *Clases que no existen en el ráster…* | Nombre mal escrito en *Clases a conservar*. | Usa los que indica el mensaje. |
| *El ráster es demasiado grande para el modo "tamaño mínimo de parche".* | Supera el límite. | Usa el filtro de mayoría. |
| *El ráster tiene N píxeles y el máximo permitido es M…* | Supera el máximo configurado. | Recorta o reduce la resolución; o pide al administrador subir el límite. |
| *No hay espacio suficiente en el directorio temporal…* | Disco casi lleno. | Libera espacio / avisa al administrador. |
| *El ráster N no se solapa con el ráster de referencia (el primero).* | En *Combinar ráster*, los ráster no coinciden en el espacio. | Revisa los sistemas de coordenadas y que el primero sea el de la zona. |
| *La máscara no se solapa con el ráster…* | En *Recortar ráster*, los polígonos están fuera de la imagen. | Revisa que sean de la misma zona y que la máscara tenga sistema de coordenadas. |
| *La máscara debe ser una capa de polígonos…* | La máscara solo tiene puntos o líneas. | Usa una capa de polígonos (por ejemplo, un buffer). |
| *La máscara es más pequeña que un píxel del ráster…* | Un polígono diminuto que no contiene el centro de ningún píxel. | Usa un polígono mayor o el modo *El rectángulo que los contiene*. |
| *Conecta al menos dos ráster para combinarlos.* | Solo hay uno conectado. | Conecta otro a una entrada distinta. |
| *La tabla ya tiene una columna llamada "x".* | En *Predecir tabla*, la columna de predicción ya existe. | Cambia el nombre. |
| *La tabla no tiene las columnas con las que se entrenó el modelo…* | Tabla distinta a la de entrenamiento. | Usa una con las mismas columnas. |
| *Ninguna muestra de validación cae sobre píxeles clasificados…* | Las muestras no se solapan con el mapa. | Revisa solape y sistema de coordenadas. |
| *Ya existe un modelo llamado "x".* | *Guardar modelo* con "Parar con un error". | Cambia el nombre o permite crear una versión. |
| *No existe el modelo "x" del usuario…* | No hay un modelo con ese nombre para el propietario. | Guárdalo con *Guardar modelo* (cuenta el propietario del workspace, no quien ejecuta). |
| *El modelo "x" no es de confianza: su firma no es válida…* | Modelo modificado/copiado o cambió la clave del servidor. | Guárdalo de nuevo desde un flujo de este servidor. |
| *No se ha podido cargar el modelo… otra versión de scikit-learn* | El servidor se actualizó después de guardarlo. | Vuelve a entrenarlo y guárdalo. |
| *Ya existe la capa "x" en el workspace…* | *Publicar ráster* con "Parar con un error". | Cambia a *Reemplazar* o usa otro nombre. |
| *No tienes permiso para publicar en el workspace…* | Faltan permisos. | Pide acceso al administrador. |
| *Conversión a reflectancia desconocida…* | Valor no válido en *Valores de la imagen*. | Elige una de las opciones del desplegable. |
| *Valor no válido para las variables por división…* / *…entre 0 y 1* | *Variables por división* mal indicado. | Usa una de las opciones del desplegable. |
| *Hacen falta al menos 2 muestras de referencia en cada clase del mapa…* | En *Estimar superficies*, alguna clase del mapa tiene 0 o 1 puntos. | Genera los puntos con *Muestreo estratificado* (50 por clase o más). |
| *La estimación de superficies necesita PUNTOS…* | Se conectó una tabla de polígonos. | Usa los puntos de *Muestreo estratificado* con la clase real anotada. |
| *El ráster está en coordenadas geográficas (grados)…* | Mapa en EPSG:4326 u otro sistema geográfico. | Trabaja en un sistema proyectado (UTM). |
| *AVISO: la muestra no contiene ningún error…* | La muestra no encontró errores: el intervalo sale 0. | Aumenta los puntos por clase. |
| *Permission denied* al leer un ráster | El directorio temporal del servidor no es escribible por el proceso del ETL. | Avisa al administrador. |

### 10.3 "Funciona, pero el mapa sale mal"

| Lo que ves | Causa probable | Qué hacer |
|---|---|---|
| Muchísimos polígonos diminutos | Ruido de píxeles sueltos | *Limpiar ráster* (mayoría 3 × 3) y *Área mínima*. |
| Una clase aparece donde no debe (por ejemplo, agua en sombras) | Falta una clase de "sombra" o el modelo confunde clases parecidas | Añade muestras de lo que se confunde (mira la matriz). |
| Se pierden elementos pequeños aislados | Una variable que solo explica la clase cerca de tus muestras (altura, distancia…), o muestras que no los incluyen | Quita esa variable; añade muestras de esos elementos. |
| Toda una zona sale con una clase "rara" | Esa zona no se parece a ninguna de tus muestras | Añade ejemplos de esa zona. |
| Bordes en escalera | Es la resolución de la imagen | *Simplificar* en *Ráster a polígonos*. |
| La superficie sale sistemáticamente alta/baja | Una clase sobrestimada (precisión baja) o infraestimada (recall bajo) | Mira la precisión y el recall de esa clase. |
| Seguridad baja en todos los bordes | Normal: son píxeles mezcla | Tenlo en cuenta al usar el mapa; no la uses como probabilidad de acierto. |

---

## 11. Para el administrador

### Requisitos y despliegue

- El backend necesita **scikit-learn** en la imagen (viene en `requirements-django4.txt`).
- Tras actualizar el plugin: **reiniciar los servicios Celery** (`celery`, `celerybeat`) y el backend, y **Ctrl+F5** en el editor.
- Los procesos del ETL corren como `www-data`. Los directorios nuevos que cree `root` dentro del contenedor pasan a ser del dueño de su carpeta padre.

### Límites configurables

Variables de entorno (o `settings.py` del plugin). **0 = sin límite.** Al superar un límite, el nodo falla con un mensaje claro en lugar de agotar el servidor.

| Variable | Por defecto | Qué limita |
|---|---|---|
| `ETL_RASTER_MAX_PIXELS` | 4 000 000 000 | Píxeles (alto × ancho) de un ráster en cualquier nodo. |
| `ETL_RASTER_MAX_TRAIN_ROWS` | 2 000 000 | Filas de entrenamiento; por encima se submuestrea con aviso. |
| `ETL_RASTER_N_JOBS` | −1 (todos los núcleos) | Procesos al entrenar. Bájalo para no acaparar el servidor. |
| `ETL_RASTER_POLYGONIZE_STRIP_PIXELS` | 25 000 000 | Píxeles por franja al vectorizar (memoria frente a velocidad). |
| `ETL_RASTER_SIEVE_MAX_PIXELS` | 150 000 000 | Tamaño máximo del filtro de tamaño mínimo de parche. |
| `ETL_RASTER_MIN_FREE_MB` | 200 | Margen libre mínimo en el directorio temporal. |
| `ETL_MODELS_DIR` | `<gestor de ficheros>/.geoetl_models` | Dónde se guardan los modelos (debe ser escribible por `www-data` y persistente). |
| `ETL_MODELS_KEEP_VERSIONS` | 10 | Versiones conservadas por modelo (0 = todas). |
| `ETL_MODELS_SIGNING_KEY` | (vacía: se deriva de la `SECRET_KEY`) | Clave con la que se firman los modelos. Fíjala si no quieres perder los modelos al cambiar la `SECRET_KEY`. |

### Rendimiento de referencia

Medido en un servidor de desarrollo con una imagen de 6 000 × 6 000 píxeles (36 millones, 358 MB) combinada con un modelo del terreno de otra resolución:

| Paso | Tiempo | Memoria máxima |
|---|---:|---:|
| Combinar ráster | 21 s | ≈ 820 MB |
| Índice espectral | 24 s | ≈ 820 MB |
| Predecir ráster (50 árboles) | 17 s | ≈ 1 190 MB |
| Limpiar ráster (mayoría 5 × 5, 2 repeticiones) | 2 s | ≈ 1 190 MB |
| Ráster a polígonos (36 M px) | 0,4 s | sin aumento |
| Ráster a polígonos de una clasificación muy ruidosa (9 M px, 94 000 polígonos) | 7 s | sin aumento |

Mide en el servidor de producción antes de fijar límites.

### Seguridad y permisos

- El editor ETL requiere un usuario de personal (*staff*).
- *Publicar ráster* exige permiso sobre el workspace y el grupo de capas, y para reemplazar una capa, permiso para gestionarla.
- Los modelos guardados están **firmados**; solo se cargan si la firma coincide. Cada usuario gestiona los suyos; un superusuario puede consultar y borrar los de otro.
- En el modo de edición **restringida**, los nodos de entrada y salida no son editables.
- Los resúmenes de ejecución (métricas, avisos) también se escriben en el log de Celery, que es donde los ve el administrador; el usuario los consulta guardando el *Informe* en PostGIS.

### Pruebas

Dentro del contenedor, sin servicios externos: `python manage.py test gvsigol_plugin_geoetl.tests`. Con la base de datos y GeoServer, de integración: `GEOETL_INTEGRATION=1` y `GEOETL_INTEGRATION_GEOSERVER=1` (crean y borran tablas `zzit_*` y un workspace temporal). Los datos de ejemplo se regeneran con `ejemplos/generar_datos_ejemplo.py`.

---

## 12. Preguntas frecuentes

**¿Cuántos polígonos de ejemplo necesito?**
Como mínimo 3-5 por clase, repartidos por toda la zona; mejor decenas. Lo importante es la **variedad** más que el tamaño. Un buen indicador: si al dejar polígonos fuera las notas de las rondas varían mucho, faltan polígonos.

**Mi imagen es enorme (una hoja del PNOA a 25 cm). ¿La clasifico entera?**
No conviene: son miles de millones de píxeles y el flujo tardaría horas y ocuparía decenas de GB de temporales. Empieza con **Recortar ráster** a tu zona de estudio y, si no necesitas tanto detalle, a 1 m (16 veces menos píxeles). Es una sola operación y tarda segundos.

**¿Puedo usar más de un ráster?**
Sí: *Combinar ráster* une de 2 a 4 (con distinta resolución o sistema de coordenadas) y el primero es la referencia.

**¿Puedo usar variables que no sean bandas (pendiente, distancia a un río)?**
Sí, si las conviertes en una banda de un ráster y la combinas con *Combinar ráster*. Pero cuidado con el [caso de la altura](#cuándo-una-variable-que-mejora-la-nota-empeora-el-mapa): usa solo variables que se relacionen con la clase en **toda** la escena.

**¿Funciona con imágenes de satélite (Sentinel, Landsat)?**
Sí, son GeoTIFF multibanda. Pon nombres a las bandas (`azul`, `verde`, `rojo`, `nir`, `swir`…) y, en *Índice espectral*, elige en *Valores de la imagen* el producto: **Sentinel-2 L2A desde 2022** (con offset −1000), **anterior a 2022** o **Landsat Colección 2 nivel 2**. Sin esa conversión, con los productos que llevan offset ni siquiera el NDVI es correcto.

**¿Puedo dar en un informe la superficie que sale de contar píxeles?**
No es lo recomendable: arrastra los errores del mapa y no tiene margen de error. Usa *Muestreo estratificado* y *Estimar superficies* (caso 9), que corrigen la superficie y dan su intervalo de confianza.

**¿La "seguridad" de un píxel es la probabilidad de que esté bien clasificado?**
No. Es la proporción de árboles que votan por esa clase, un indicador relativo para ver dónde duda el modelo. Las puntuaciones de un Random Forest no están calibradas como probabilidades.

**¿Por qué no sale lo mismo si lo repito?**
Con la misma semilla, las mismas muestras y el mismo orden de variables, sale lo mismo. Si cambias alguna de ellas, hay pequeñas diferencias; es normal.

**¿Puedo clasificar sin muestras?**
No hay clasificación no supervisada (sin ejemplos) en estos nodos.

**¿Cuánto tarda?**
Entrenar con unos miles de píxeles es cuestión de segundos. Lo que más tarda es predecir sobre imágenes grandes (decenas de segundos por cada decenas de millones de píxeles).

**El modelo que guardé no aparece**
Los modelos son **privados**: solo los ve quien los guardó. Si ejecutas un workspace de otro usuario, se usan los modelos del propietario.

**¿Qué hago si cambia la imagen (otro sensor, otra época)?**
Vuelve a entrenar con muestras de la nueva imagen. Un modelo solo vale para condiciones parecidas a las que usó para aprender.

**¿Puedo medir cambios entre dos fechas?**
Sí, de dos maneras: clasificar cada fecha por separado y comparar los polígonos (con *Intersección* o *Diferencia*), o combinar las dos fechas con *Combinar ráster* y entrenar directamente el cambio (receta 8.4).

---

## 13. Fundamentos científicos y referencias

Esta sección resume en qué se basa cada método, qué límites tiene y dónde está publicado, para poder justificarlo en un informe técnico.

### Qué hace cada nodo y en qué se basa

| Nodo / método | Base | Notas |
|---|---|---|
| Random Forest | Breiman (2001) | Árboles de decisión con *bootstrap* y elección al azar de variables en cada división: √p en clasificación y p/3 en regresión. En clasificación se compensan las clases desiguales con pesos inversos a su frecuencia. |
| Validación por polígonos y por bloques | Roberts et al. (2017); Ploton et al. (2020) | Con datos espaciales, la validación al azar sobrestima la calidad por la autocorrelación. Se usa validación cruzada agrupada y estratificada. |
| Importancia por permutación | Breiman (2001); Strobl et al. (2007) | Medida sobre los datos de evaluación. La importancia por impureza se conserva, pero está sesgada. |
| NDVI, NDWI, NDBI, SAVI, EVI | Rouse et al. (1974); McFeeters (1996); Zha et al. (2003); Huete (1988); Huete et al. (2002) | Fórmulas originales. EVI con G = 2,5; C1 = 6; C2 = 7,5; L = 1; valores fuera de [−1, 1] sin dato. Requieren reflectancia para ser medidas físicas. |
| Evaluación con intervalos | Congalton y Green (2019); Efron y Tibshirani (1993) | Exactitudes del usuario y del productor; intervalos por *bootstrap* de unidades de muestreo enteras. |
| Muestreo estratificado y estimación de superficies | Olofsson et al. (2013, 2014); Stehman y Foody (2019) | Estimador estratificado de proporciones de superficie, exactitudes y sus varianzas. Reproduce el ejemplo resuelto de Olofsson et al. (2014). |

### Límites conocidos

- **Las ortofotos no son reflectancia calibrada**: sus índices sirven para clasificar una imagen, no como medidas físicas comparables entre fechas, hojas o sensores.
- **La seguridad del modelo no es una probabilidad calibrada** (Niculescu-Mizil y Caruana, 2005). Calibrarla requeriría datos de calibración independientes y no está incluido.
- **La incertidumbre de la regresión** (dispersión entre árboles) subestima la real; un intervalo de predicción requeriría un *quantile regression forest* (Meinshausen, 2006), que no está incluido.
- **Evaluar clasificación** con polígonos dibujados a mano no es un diseño probabilístico: su exactitud es orientativa. Para inferencia válida, *Muestreo estratificado* + *Estimar superficies*.
- **Contar píxeles** da superficies sesgadas por los errores de clasificación; la superficie con intervalo es la de *Estimar superficies*.
- **Kappa** se calcula por compatibilidad, pero no se recomienda para valorar mapas (Pontius y Millones, 2011; Foody, 2020).
- El **tamaño de bloque** de la validación espacial lo elige el usuario; idealmente debería basarse en el alcance de la autocorrelación espacial (por ejemplo, con un variograma), que el nodo no calcula.

### Referencias

- Breiman, L. (2001). Random forests. *Machine Learning*, 45(1), 5-32.
- Congalton, R. G. y Green, K. (2019). *Assessing the Accuracy of Remotely Sensed Data: Principles and Practices* (3.ª ed.). CRC Press.
- Efron, B. y Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
- Foody, G. M. (2020). Explaining the unsuitability of the kappa coefficient in the assessment and comparison of the accuracy of thematic maps obtained by image classification. *Remote Sensing of Environment*, 239, 111630.
- Huete, A. R. (1988). A soil-adjusted vegetation index (SAVI). *Remote Sensing of Environment*, 25(3), 295-309.
- Huete, A., Didan, K., Miura, T., Rodriguez, E. P., Gao, X. y Ferreira, L. G. (2002). Overview of the radiometric and biophysical performance of the MODIS vegetation indices. *Remote Sensing of Environment*, 83(1-2), 195-213.
- McFeeters, S. K. (1996). The use of the Normalized Difference Water Index (NDWI) in the delineation of open water features. *International Journal of Remote Sensing*, 17(7), 1425-1432.
- Meinshausen, N. (2006). Quantile regression forests. *Journal of Machine Learning Research*, 7, 983-999.
- Niculescu-Mizil, A. y Caruana, R. (2005). Predicting good probabilities with supervised learning. *Proceedings of the 22nd International Conference on Machine Learning*, 625-632.
- Olofsson, P., Foody, G. M., Stehman, S. V. y Woodcock, C. E. (2013). Making better use of accuracy data in land change studies: estimating accuracy and area and quantifying uncertainty using stratified estimation. *Remote Sensing of Environment*, 129, 122-131.
- Olofsson, P., Foody, G. M., Herold, M., Stehman, S. V., Woodcock, C. E. y Wulder, M. A. (2014). Good practices for estimating area and assessing accuracy of land change. *Remote Sensing of Environment*, 148, 42-57.
- Ploton, P. et al. (2020). Spatial validation reveals poor predictive performance of large-scale ecological mapping models. *Nature Communications*, 11, 4540.
- Pontius, R. G. y Millones, M. (2011). Death to Kappa: birth of quantity disagreement and allocation disagreement for accuracy assessment. *International Journal of Remote Sensing*, 32(15), 4407-4429.
- Roberts, D. R. et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography*, 40(8), 913-929.
- Rouse, J. W., Haas, R. H., Schell, J. A. y Deering, D. W. (1974). Monitoring vegetation systems in the Great Plains with ERTS. *Third ERTS Symposium*, NASA SP-351, 309-317.
- Stehman, S. V. y Foody, G. M. (2019). Key issues in rigorous accuracy assessment of land cover products. *Remote Sensing of Environment*, 231, 111199.
- Strobl, C., Boulesteix, A.-L., Zeileis, A. y Hothorn, T. (2007). Bias in random forest variable importance measures: illustrations, sources and a solution. *BMC Bioinformatics*, 8, 25.
- Zha, Y., Gao, J. y Ni, S. (2003). Use of normalized difference built-up index in automatically mapping urban areas from TM imagery. *International Journal of Remote Sensing*, 24(3), 583-594.

---

## Glosario

| Término | Significado |
|---|---|
| **Banda** | Cada capa de una imagen (rojo, verde, infrarrojo…). Cada una es una variable para el modelo. |
| **Clase** | Categoría que se quiere reconocer (agua, vegetación…). |
| **Clasificación supervisada** | Clasificar una imagen aprendiendo de ejemplos con la clase conocida. |
| **Código de clase** | Número que representa a una clase en el ráster clasificado (1, 2, 3…); el 0 es sin dato. |
| **Bagging** | Entrenar muchos árboles, cada uno con una muestra al azar de los datos, y promediarlos. Un Random Forest es *bagging* más la elección al azar de variables en cada división. |
| **Bootstrap** | Repetir un cálculo muchas veces con remuestras al azar de los datos para medir cuánto varía el resultado (de ahí salen intervalos). |
| **Intervalo de confianza** | Rango en el que, con una confianza dada (por ejemplo 95 %), está el valor real. Cuanto más ancho, menos preciso. |
| **Muestreo aleatorio estratificado** | Elegir al azar un número fijo de puntos dentro de cada clase del mapa. Es el diseño recomendado para medir exactitud y superficies. |
| **Offset** | Valor que se suma a los datos de una imagen antes de dividir por la escala para obtener reflectancia (por ejemplo −1000 en Sentinel-2 desde 2022). |
| **Probabilidad calibrada** | Puntuación que coincide con la frecuencia real de acierto (un 0,9 acierta 9 de cada 10 veces). La seguridad de un Random Forest **no** lo es. |
| **Seguridad del modelo** | Proporción de árboles que votan por la clase elegida (de 0 a 1), o dispersión entre árboles en regresión. Indicador relativo, no probabilidad. |
| **Entrenar** | Que el modelo aprenda de los ejemplos. |
| **Exactitud del productor (recall)** | De lo que realmente es una clase, cuánto encuentra el mapa. |
| **Exactitud del usuario (precisión)** | De lo que el mapa dice que es una clase, cuánto lo es de verdad. |
| **Índice espectral** | Una banda calculada a partir de otras (NDVI, NDWI…). |
| **Kappa** | Medida clásica de acuerdo por encima del azar. Desaconsejada hoy para evaluar mapas. |
| **Matriz de confusión** | Tabla que cruza la clase real con la clase predicha; la diagonal son los aciertos. |
| **Modelo** | Lo aprendido durante el entrenamiento; se aplica a una imagen o tabla. |
| **Muestra (o ejemplo)** | Polígono del que se conoce la clase. |
| **Muestras de validación** | Polígonos distintos de los de entrenamiento, usados solo para medir la calidad. |
| **NDVI** | Índice de vegetación: (NIR − Rojo) / (NIR + Rojo). |
| **Píxel de muestra** | Píxel cuyo centro cae dentro de una muestra. |
| **Random Forest** | Algoritmo que combina muchos árboles de decisión por votación. |
| **Reflectancia** | Fracción de luz que refleja una superficie; en una imagen se guarda como un valor por píxel. |
| **Regresión** | Predecir un número (biomasa, altura…) en vez de una categoría. |
| **Remuestreo** | Cambiar el tamaño de píxel de un ráster. |
| **Ruido de sal y pimienta** | Píxeles sueltos mal clasificados dentro de una zona homogénea. |
| **Sin dato** | Píxel sin información. |
| **Sobreajuste** | Cuando el modelo se aprende los ejemplos de memoria y falla con datos nuevos. |
| **Validación** | Medir la calidad con datos que no se usaron para entrenar. |
| **Validación espacial** | Medir dejando fuera polígonos o bloques enteros, para que los vecinos del entrenamiento no inflen la nota. |
| **Variable (o predictora)** | Dato con el que el modelo decide: una banda, un índice, una columna numérica. |
| **Versión (de un modelo)** | Cada vez que se guarda un modelo con el mismo nombre, se crea una versión nueva. |
