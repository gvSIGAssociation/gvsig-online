# Simbología

La **simbología** define cómo se dibujan las capas en el mapa: colores, símbolos, etiquetas y a qué
escalas se ven. Cada capa puede tener varios **estilos**; uno de ellos es el estilo por defecto, el
que usan el visor y la leyenda. Los estilos se guardan en GeoServer como SLD, el formato estándar de
estilos de mapas, y se pueden descargar.

La simbología se gestiona desde el panel de administración, en el menú **Simbología**, que tiene
tres apartados: **Estilos de capa**, **Bibliotecas de símbolos** y **Rampas de color**.

## Quién puede hacer qué

| Acción | Quién |
|---|---|
| Ver la lista de estilos de capa | Personal (*staff*) y superusuarios. Los superusuarios ven todas las capas; el resto, las capas que crearon y aquellas en las que alguno de sus roles tiene permiso de gestión |
| Crear, modificar, descargar o eliminar estilos de una capa | Quien gestiona la capa: los superusuarios, quien la creó y el personal con un rol que tenga permiso de gestión sobre ella (ver [Capas](capas.md)) |
| Crear, modificar y eliminar **Bibliotecas de símbolos** y **Rampas de color** | Personal y superusuarios. Son recursos comunes: lo que se cambia afecta a todos |
| Usar los símbolos y rampas de las bibliotecas al editar un estilo | Quien puede editar el estilo |

Las capas externas no aparecen en la lista de estilos: su estilo lo define el servidor de origen.

## Lista de estilos de capa

![Lista de estilos de capa](img/simbologia-lista-estilos.png)

**Estilos de capa** muestra una fila por capa con su identificador, su **Nombre de la capa**, el
grupo al que está **Asignado** y un desplegable **Estilos** con todos sus estilos; el estilo por
defecto aparece marcado como **(por defecto)**. El buscador filtra por el nombre y el título de la
capa y por los de su grupo, y la tabla se pagina.

Los botones de cada fila actúan sobre el estilo elegido en el desplegable de esa fila:

- **Añadir estilo**: crea un estilo nuevo para la capa (ver [Crear un estilo](#crear-un-estilo)).
- **Actualizar estilo**: abre el editor del estilo seleccionado.
- **Descargar SLD**: descarga el estilo, tal como está publicado en GeoServer, en un fichero `.sld`.
- **Eliminar estilo**: borra el estilo de gvSIG Online y de GeoServer.

!!! warning "Eliminar un estilo"
    El estilo se borra tras confirmarlo; no se puede deshacer. No se puede eliminar el estilo por
    defecto (**No puede eliminar un estilo por defecto**) ni el único estilo de una capa (**La capa
    debe contener al menos un estilo**). Para quitar el estilo por defecto, marque antes otro como
    estilo por defecto.

## Crear un estilo

Pulse **Añadir estilo** en la fila de la capa. La pantalla **Crear nuevo estilo** pide elegir el
tipo de leyenda. Los tipos que se ofrecen dependen de la capa:

![Selección del tipo de leyenda](img/simbologia-tipo-leyenda.png)

| Tipo | Para qué sirve | Capas |
|---|---|---|
| **Símbolo único** | Todos los elementos con el mismo símbolo | Vectoriales |
| **Valores únicos** | Un símbolo distinto para cada valor de un campo (usos del suelo, tipos de vía…) | Vectoriales |
| **Intervalos** | Agrupa los valores de un campo numérico en rangos, cada uno con su símbolo | Vectoriales |
| **Expresiones** | Cada regla tiene su propio filtro (combinando campos y condiciones con Y / O), su símbolo y sus escalas | Vectoriales |
| **Mapa de calor** | Densidad de los elementos como una superficie de color continua | Vectoriales |
| **Agrupación de puntos** | Agrupa los puntos cercanos en un símbolo que indica cuántos hay | Vectoriales de puntos |
| **Tabla de color** | Asigna colores a los valores del ráster | Ráster |
| **Personalizada** | Se escribe o pega directamente el SLD | Todas |

### Datos comunes a todos los estilos

En **Propiedades del estilo**:

- **Nombre**: lo asigna el sistema a partir del espacio de trabajo y el nombre de la capa; no se puede
  cambiar.
- **Título**: el nombre que se muestra del estilo.
- **Escala min** y **Escala max**: el rango de escalas (denominador, `1:` *n*) en el que se dibuja la
  capa con este estilo. Déjelos vacíos (**Sin límite**) para que se vea a cualquier escala.
- **Fijar como estilo por defecto** (ver [Estilo por defecto](#estilo-por-defecto)).

A la derecha, **Vista previa en el mapa** muestra la capa sobre un mapa de OpenStreetMap. Pulse
**Actualizar previsualización** para ver los cambios antes de guardar, y **Guardar** para publicar el
estilo.

### Símbolo único

![Editor de símbolo único](img/simbologia-editor-simbolo-unico.png)

Hay una sola regla, en el apartado **Símbolo**, con la lista de sus simbolizadores (ver
[Reglas y simbolizadores](#reglas-y-simbolizadores)). El botón **Etiquetado** de la cabecera abre la
configuración de las etiquetas (ver [Etiquetado](#etiquetado)).

### Valores únicos

1. En **Seleccionar campo para generar valores únicos**, elija el campo. Se crea una regla por cada
   valor distinto del campo, con un color al azar. Los elementos sin valor tienen su propia regla,
   **Sin valor**.
2. **Añadir valor** crea a mano una regla para un valor concreto del campo elegido.
3. **Aplicar rampa de color** colorea todas las reglas con una rampa (ver
   [Aplicar una rampa de color](#aplicar-una-rampa-de-color)).

Arrastre las reglas por su asa (**Arrastrar para reordenar**) para cambiar su orden en la leyenda.

### Intervalos

1. En **Seleccionar un campo numérico**, elija el campo.
2. En **Nº intervalos**, indique cuántos rangos quiere. El rango entre el valor mínimo y el máximo
   del campo se divide en intervalos **iguales**, y se crea una regla por intervalo.
3. Si lo necesita, ajuste los límites de cada intervalo en **Editar regla** (**Intervalo mínimo** e
   **Intervalo máximo**) y aplique una rampa de color.

### Expresiones

**Añadir nueva regla** crea una regla vacía. En el menú de la llave de cada regla, **Editar filtro**
abre el editor de condiciones:

- Cada condición tiene un campo (**Seleccionar campo**), una operación (**Seleccionar operación**) y
  un **Valor**. Las operaciones son **Es igual a**, **Es nulo**, **Contiene**, **No es igual**,
  **Es mayor que**, **Es mayor que o igual**, **Es menor que** y **Es menor que o igual**.
- **Añadir** › **Expresión AND** o **Expresión OR** encadena más condiciones.
- **Guardar filtro** aplica el filtro a la regla.

### Mapa de calor

En **Configuración del mapa de calor**:

- **Radio (píxeles)** y **Píxeles por celda**.
- **Usar un campo para ponderar el mapa de calor**: cada elemento pesa según el valor de un campo
  numérico.
- **Gradiente de color**, entre un **Color frío** y un **Color caliente**, o **Tabla de color**, con
  varios **Pasos** (**Añadir paso**) o una rampa de color. La tabla necesita al menos dos pasos.

### Agrupación de puntos

La regla **Entidad simple** dibuja los puntos aislados. **Añadir nueva regla** crea reglas para los
grupos; su filtro (**Editar filtro**) se basa en el número de puntos agrupados (**Contar
registros**). **Añadir simbolizador de texto** añade un texto al símbolo; eligiendo como campo
**Contar registros** se muestra el número de puntos del grupo.

### Tabla de color (ráster)

- **Nº intervalos** crea ese número de entradas de color repartidas por igual entre el valor mínimo
  y el máximo del ráster. Cada entrada tiene **Color**, **Cantidad** (el valor del ráster),
  **Etiqueta** y **Opacidad**.
- **Estadísticas del raster** muestra el mínimo, el máximo, la media y la desviación típica de cada
  banda.
- **¿Tiene leyenda propia?** permite subir una imagen PNG que se usará como leyenda.

### Personalizada

En **Definición del estilo (SLD)** escriba o pegue el SLD completo; el editor parte de un SLD vacío.
Es la opción para estilos preparados en gvSIG Desktop, QGIS o GeoServer, o para usar opciones que el
resto de leyendas no ofrecen. El SLD se publica tal cual: compruébelo con **Actualizar
previsualización** antes de guardar.

## Reglas y simbolizadores

Cada **regla** de un estilo es una entrada de la leyenda: un filtro (qué elementos dibuja), un rango
de escalas y uno o varios **simbolizadores** superpuestos. Por ejemplo, una carretera puede dibujarse
con una línea gruesa oscura y encima otra más fina y clara.

En cada regla:

- La llave ofrece **Editar regla**: **Nombre de la regla**, **Título de la regla** (el texto de la
  leyenda) y, salvo en símbolo único, **Visible por escala** con el **Denominador mínimo de la escala**
  y el **Denominador máximo de la escala** propios de esa regla.
- **Añadir simbolizador** añade una capa más al símbolo.
- **Predefinidos** sustituye los simbolizadores de la regla por un símbolo ya preparado (ver
  [Símbolos predefinidos](#simbolos-predefinidos)).
- **Importar desde librería** copia un símbolo de una biblioteca. Debe ser del mismo tipo de geometría
  que la capa.
- En la tabla de simbolizadores, el lápiz abre el simbolizador y la aspa lo elimina. Arrastre las
  filas por su asa para cambiar el orden: **la fila de arriba se dibuja encima** de las demás.

### Editar un simbolizador

![Simbolizador de línea con marcas](img/simbologia-simbolizador-linea.png)

La ventana **Editar simbolizador** muestra encima una **Vista previa del símbolo**, generada por
GeoServer con el mismo SLD que se publicará. Cuando el símbolo usa opciones que los estilos clásicos
no tenían, se indica como **Símbolo avanzado**. Las pestañas dependen de la geometría de la capa.

**Puntos** (pestañas **Forma**, **Relleno** y **Línea**):

- **Forma**: 22 formas, entre ellas círculo, cuadrado, triángulo, estrella, cruz, X, rombo, pentágono,
  hexágono, flechas, punta de flecha y formas de solo trazo (línea vertical, barra, más, aspa). Además,
  **Tamaño**, **Opacidad del símbolo**, **Rotación**, **Sumar el ángulo de un campo** (gira cada punto
  según un campo numérico) y **Desplazamiento** **Horizontal** y **Vertical (hacia arriba)** en píxeles.
- **Relleno**: **Rellenar la forma**, **Color del relleno** y **Opacidad del relleno**. Las formas de
  solo trazo no tienen relleno.
- **Línea**: color, anchura y opacidad del contorno.

**Líneas** (pestañas **Línea** y **Decoración**):

- **Línea**: **Dibujar la línea** (desmárquelo para dejar solo las marcas), color, anchura y opacidad;
  **Patrón de guiones**, con doce patrones o un **Patrón personalizado** (longitudes de guion y hueco
  en píxeles separadas por espacios, p. ej. `10 4 2 4`); **Extremos** (**Recto**, **Redondeado**,
  **Cuadrado**); **Esquinas** (**En ángulo**, **Redondeado**, **Biselada**); **Desfase del guion** y
  **Desplazamiento lateral**, que mueve la línea a la izquierda (positivo) o a la derecha (negativo) de
  su sentido, por ejemplo para dibujar líneas paralelas.
- **Decoración**: **Marcas a lo largo de la línea** (traviesas, puntos, flechas…, con su **Separación
  entre marcas** y **Desplazamiento inicial**) y marcas en el **Inicio de la línea** y en el **Final de
  la línea**. Las marcas siguen el sentido de la línea: sirven para ferrocarriles, flechas de sentido
  de la corriente o límites.

**Polígonos** (pestañas **Relleno** y **Línea**):

- **Tipo de relleno**: **Sólido**, **Trama** o **Sin relleno**. La trama tiene siete **Patrones**
  (diagonales en los dos sentidos, horizontal, vertical, **Cuadrícula**, **Cuadrícula diagonal** y
  **Puntos**), con su **Color de la trama**, **Grosor de línea** y **Separación**; con **Color de fondo
  bajo la trama** se pinta además un fondo.
- **Línea**: el contorno, con las mismas opciones de guiones, extremos y esquinas que las líneas.

![Relleno de polígono con trama](img/simbologia-simbolizador-trama.png)

!!! note "Compatibilidad de los símbolos avanzados"
    Un símbolo que no usa ninguna opción nueva se guarda exactamente igual que antes: abrir un estilo
    antiguo y cambiarle el color no lo transforma. Los símbolos avanzados se ven en los mapas WMS y en
    las capas que el visor muestra como teselas vectoriales. Las versiones anteriores de gvSIG Online
    no saben importarlos (ver [Exportar e importar bibliotecas](#exportar-e-importar-bibliotecas)).

### Símbolos predefinidos

**Predefinidos** abre **Símbolos predefinidos**, con 33 símbolos listos para usar según la geometría:
8 de puntos (punto de interés, vértice geodésico, flecha hacia arriba…), 15 de líneas (carretera
principal, ferrocarril, río con sentido de la corriente, línea eléctrica, límite administrativo…) y
10 de polígonos (edificación, zona inundable, área protegida, cultivos…). Al elegir uno se sustituyen
los simbolizadores de la regla; la etiqueta se conserva, y los simbolizadores se pueden editar
después.

## Etiquetado

El botón **Etiquetado** de los editores de símbolo único, valores únicos, intervalos, expresiones y
agrupación de puntos abre la configuración de las etiquetas de la capa:

- **General**: **Activar etiquetado**, el **Título de la regla** y las escalas mínima y máxima en las
  que se muestran las etiquetas.
- **Fuente**: **Campo de etiqueta**, **Familia de fuente**, **Tamaño de fuente**, **Color de fuente**,
  **Grosor de fuente** y **Estilo de fuente**.
- **Halo**: el contorno que mejora la lectura sobre el mapa: **Color de halo**, **Opacidad de halo** y
  **Radio de halo**.
- **Filtro**: **Mostrar etiquetas** solo en los elementos que cumplan unas condiciones
  (**Etiqueta filtrada por expresión**), que se construyen como en las expresiones.

![Opciones avanzadas de etiqueta](img/simbologia-etiqueta-avanzada.png)

Una etiqueta se crea como **Etiqueta clásica**. En la pestaña **General**, **Usar opciones avanzadas**
añade tres pestañas y una vista previa:

- **Contenido**: el **Texto de la etiqueta** se compone combinando **Campo** y **Texto** fijo (hasta
  diez partes). Los campos numéricos se pueden formatear como **Número** (**Decimales**, **Separador de
  miles**, **Idioma**) y los de fecha como **Fecha** (**Formato de fecha**). También **Mayúsculas y
  minúsculas**, **Espaciado entre letras** y **Partir el texto a** (anchura máxima antes de partir en
  varias líneas; 0 = nunca).
- **Colocación**:
    - En puntos, **Posición respecto al punto** (nueve posiciones) y desplazamiento horizontal y vertical.
    - En líneas, **Seguir la línea (texto curvo)**, **Ángulo máximo de curvatura**, **Repetir cada** y
    **Distancia a la línea**.
    - En polígonos, **Siempre dentro del polígono** o **Centroide (como las etiquetas clásicas)**.
    - En puntos y polígonos, **Ángulo** fijo o **Ángulo desde un campo**.
    - **Etiquetas solapadas**: **Dibujar aunque se solape con otras etiquetas**, **Espacio mínimo
    alrededor** y **Campo de prioridad** (con etiquetas que chocan, se dibujan antes las de valor más
    alto).
- **Fondo**: **Dibujar un recuadro detrás de la etiqueta**, con color y opacidad de relleno, **Color
  del borde**, **Grosor del borde** y **Margen interior**. Con fondo, los mapas WMS solo parten el texto
  en varias líneas si la etiqueta está centrada sin rotación o a la derecha del punto.

**Volver a etiqueta clásica** descarta las opciones avanzadas, previa confirmación.

## Estilo por defecto

El estilo por defecto es el que usan el visor, la leyenda y la miniatura de la capa.

- Al marcar **Fijar como estilo por defecto** en un estilo, los demás estilos de la capa dejan de
  serlo.
- Si la capa no tiene estilo por defecto, el primer estilo que se guarda pasa a serlo aunque no se
  marque.
- Al guardar el estilo por defecto se regenera la miniatura de la capa y, si la capa tiene caché de
  teselas, se vacía para que el mapa muestre el estilo nuevo.

## Aplicar una rampa de color

En valores únicos, intervalos, tabla de color y mapa de calor, **Aplicar rampa de color** colorea las
reglas existentes con una rampa. Elija **Seleccionar biblioteca de rampas de color**, la categoría y
la rampa; **Invertir rampa de color** la aplica en orden inverso. Antes debe haber reglas: si no, se
avisa de que hay **Reglas necesarias para aplicar a la rampa de color**.

## Bibliotecas de símbolos

Una **biblioteca de símbolos** agrupa símbolos reutilizables para importarlos en cualquier estilo con
**Importar desde librería**.

![Biblioteca de símbolos](img/simbologia-biblioteca.png)

- **Añadir biblioteca**: pide el **Nombre** (solo minúsculas, números y guiones bajos) y una
  **Descripción** opcional.
- **Actualizar biblioteca** abre la biblioteca: se puede cambiar la descripción (el nombre no), buscar
  símbolos y filtrarlos por tipo. **Añadir símbolo** crea un **Punto**, una **Línea**, un **Polígono**
  o un **Gráfico externo**. Cada símbolo tiene **Nombre** (mismas reglas que la biblioteca; no se puede
  cambiar después) y **Título**, y se edita con el mismo editor de simbolizadores que los estilos.
- Un **Gráfico externo** es una imagen PNG o SVG con su **Tamaño** en píxeles. Los SVG se escalan sin
  perder calidad; al guardarlos se eliminan los scripts y las referencias externas.
- Pulse un símbolo para modificarlo o eliminarlo. **Eliminar** pide confirmación y borra el
  símbolo.
- **Eliminar biblioteca** pide confirmación y borra la biblioteca con todos sus símbolos.

### Exportar e importar bibliotecas

**Exportar biblioteca** descarga un fichero `.zip`. Si la biblioteca contiene símbolos avanzados, se
avisa y se ofrece **Exportar para versiones anteriores**: los símbolos avanzados se convierten en
clásicos (forma, colores y guiones), porque las versiones anteriores de gvSIG Online no saben
importarlos.

**Importar biblioteca** crea una biblioteca nueva a partir de un `.zip` exportado desde gvSIG Online;
no modifica las existentes. Hay que darle un **Nombre** que no exista ya.

## Rampas de color

Las **rampas de color** son degradados que se aplican a las leyendas (ver
[Aplicar una rampa de color](#aplicar-una-rampa-de-color)). Se organizan en **bibliotecas** y, dentro
de ellas, en **categorías**.

![Editor de rampa de color](img/simbologia-rampa-color.png)

- **Añadir biblioteca**, **Importar biblioteca** (desde un `.zip` exportado de gvSIG Online),
  **Exportar biblioteca** y **Eliminar biblioteca**, como en las bibliotecas de símbolos. Los nombres
  solo admiten minúsculas, números y guiones bajos.
- En una biblioteca, **Añadir categoría** crea una categoría; cada categoría se puede actualizar o
  borrar.
- En una categoría, **Añadir nueva rampa de color** abre el editor de la rampa. Cada **paso** tiene un
  **Porcentaje** (posición a lo largo de la rampa: 0 = inicio, 100 = final), un **Color** y una
  **Transparencia** (de 0, transparente, a 1, opaco). Entre pasos el color se interpola. Se necesitan
  al menos dos pasos; arrastre las filas por su asa para reordenarlos. **Vista previa de la rampa**
  muestra el resultado.
