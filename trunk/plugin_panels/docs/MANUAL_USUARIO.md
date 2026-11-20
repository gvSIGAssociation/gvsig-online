# Manual de uso del plugin Paneles

## 1. ¿Qué permite hacer?

El plugin **Paneles** permite crear cuadros de mando formados por mapas, tablas,
listas, gráficos e indicadores. Cada elemento puede utilizar:

- una capa operativa de gvSIG Online; o
- datos importados desde un fichero CSV o Excel.

Los elementos pueden relacionarse entre sí. Por ejemplo, al seleccionar un
municipio en una lista, el mapa puede resaltarlo y los gráficos recalcular sus
valores para ese municipio.

Este manual distingue tres perfiles:

- **Lector:** abre y consulta los paneles para los que tiene permiso.
- **Diseñador:** además, modifica su contenido y distribución.
- **Administrador:** crea paneles, define su acceso, los vincula a proyectos y
  asigna permisos.

Las opciones disponibles dependen de los permisos de cada cuenta.

---

## 2. Acceso a los paneles

Un panel puede abrirse desde:

- la sección **Paneles** de la portada del SPA;
- el botón **Paneles** de la barra superior de un proyecto;
- su enlace directo; o
- la lista de administración del plugin.

El botón de la barra del proyecto sólo aparece cuando hay al menos un panel
vinculado al proyecto que el usuario puede consultar.

### Panel global y panel vinculado a un proyecto

- Un **panel global** no está asociado a ningún proyecto.
- Un **panel vinculado** aparece en el botón Paneles del proyecto elegido.

La vinculación sirve como punto de acceso y aporta al panel la configuración
cartográfica del proyecto. No limita el catálogo del diseñador a las capas del
proyecto: al editar un panel se pueden elegir todas las capas operativas,
consultables y legibles por el usuario.

La dirección del panel no contiene el nombre del proyecto:

`/spa/panel/nombre-del-panel/`

### Panel público y panel restringido

- **Público:** cualquier persona con el enlace puede abrirlo.
- **Restringido:** sólo pueden abrirlo su creador, los administradores
  autorizados y los roles que tengan permiso de acceso o gestión.

Un panel público no puede exponer silenciosamente capas privadas. Al guardarlo,
el sistema solicita confirmación para publicar las capas privadas utilizadas.
La operación sólo se permite si el usuario puede gestionar todas esas capas.

---

## 3. Consultar un panel

En modo lectura se puede:

- consultar todos sus elementos;
- interactuar con mapas y gráficos;
- seleccionar valores para filtrar o resaltar otros elementos;
- retirar una selección;
- ampliar cualquier elemento a pantalla completa; y
- utilizar las leyendas de los gráficos para mostrar u ocultar series.

Si el usuario puede gestionar el panel, verá además el botón **Editar**.

### Pantalla completa

El botón **Ampliar** de la cabecera de cada elemento lo abre en una ventana
grande. Se cierra con el aspa de la ventana o pulsando fuera de ella.

### Uso en móvil

En pantallas estrechas los elementos se ordenan automáticamente en una sola
columna. Esta distribución móvil es automática y no modifica la composición de
escritorio guardada por el diseñador.

---

## 4. Crear y administrar paneles

Esta sección requiere una cuenta con perfil **staff** y permiso de gestión
sobre el panel. Un usuario con permiso de gestión que no sea staff puede
editar el diseño desde el SPA, pero no acceder a esta administración.

1. Abra **Plugins > Paneles**.
2. Pulse **Nuevo**.
3. Complete los datos del panel.
4. Defina su acceso y sus permisos.
5. Pulse **Guardar**.
6. En la lista, utilice **Diseñar** para añadir y maquetar los elementos.

### Datos generales

- **Nombre:** nombre interno utilizado para construir la URL.
- **Título:** encabezado visible del panel.
- **Descripción:** texto que aparece debajo del título.
- **Imagen:** imagen opcional que identifica el panel en el escritorio, las
  portadas de las aplicaciones y la portada SPA. Si no se carga ninguna, se
  utiliza la imagen predeterminada de los paneles.
- **Proyecto:** asociación opcional con un proyecto.
- **Acceso público:** permite abrir el panel a cualquiera que tenga el enlace.

> **Importante:** al cambiar el nombre interno se genera una nueva dirección.
> Los enlaces antiguos al panel pueden dejar de funcionar.

### Permisos por rol

Cada rol puede recibir:

- **Puede acceder:** permite abrir y consultar el panel.
- **Puede gestionar:** permite también modificarlo.

Activar **Puede gestionar** activa automáticamente **Puede acceder**.

También pueden gestionar un panel:

- su creador;
- un superusuario; y
- quien pueda gestionar el proyecto al que esté vinculado.

### Lista de paneles

La lista permite:

- buscar por texto;
- ordenar y paginar los resultados;
- distinguir paneles públicos y restringidos;
- abrir el panel en modo lectura;
- abrir su diseño;
- cambiar sus datos generales y permisos; y
- eliminarlo.

Al eliminar un panel se eliminan también sus elementos. La operación solicita
confirmación.

---

## 5. Diseñar un panel

Abra el panel en modo edición desde **Diseñar** o mediante el botón **Editar**
del propio panel.

En este modo puede:

- añadir elementos;
- moverlos y cambiar su tamaño;
- configurar o quitar cada elemento;
- definir dimensiones comunes;
- editar los colores de los gráficos; y
- guardar el diseño.

Al pulsar **Guardar**, el panel vuelve automáticamente al modo lectura.

### Añadir un elemento

1. Despliegue **Añadir elemento** en la parte superior.
2. Elija el tipo.
3. Abra su botón de configuración.
4. Seleccione el origen y los campos.
5. Pulse **Aplicar**.
6. Cuando termine el diseño, pulse **Guardar** en la cabecera del panel.

**Aplicar** actualiza el elemento en el editor, pero el cambio no queda
persistido hasta guardar el panel completo.

### Mover y redimensionar

- Arrastre un elemento desde el control de movimiento de su cabecera.
- Arrastre su esquina inferior derecha para cambiar el tamaño.

Estas operaciones están disponibles en la distribución de escritorio. En móvil
se utiliza la disposición automática de una columna.

### Quitar un elemento

El botón de papelera de su cabecera lo retira del diseño. La eliminación se
hace definitiva al guardar el panel.

---

## 6. Configuración común de los elementos

### Identificación

- **Tipo de elemento:** permite cambiar el tipo inicialmente elegido.
- **Nombre:** identificación interna opcional.
- **Título:** texto principal de la cabecera.
- **Descripción:** texto complementario.

### Origen de los datos

Salvo el mapa, cada elemento puede leer de una **capa** o de **datos
importados**, nunca de ambos al mismo tiempo.

Al elegir una capa, sólo aparecen las capas operativas y consultables que el
usuario puede leer. Los campos ofrecidos respetan, cuando existen, la
visibilidad y los títulos configurados para la capa.

El mapa siempre utiliza una capa porque necesita geometrías.

### Agregaciones

Los gráficos y los indicadores ofrecen:

- **Recuento:** número de registros.
- **Suma:** suma del campo de valor.
- **Media:** promedio de sus valores.
- **Mínimo:** valor más bajo.
- **Máximo:** valor más alto.

Los valores vacíos o no numéricos se tratan como cero en los cálculos
numéricos. Conviene revisar y limpiar las columnas antes de importarlas.

### Selección cruzada

- **Vinculado:** recibe las selecciones realizadas en otros elementos.
- **Independiente:** ignora las selecciones de los demás.

La independencia afecta a las selecciones recibidas; el elemento puede seguir
originando una selección al pulsarlo.

### Apariencia

La opción **Mostrar leyenda** controla la leyenda o el texto descriptivo cuando
el tipo de elemento lo admite.

---

## 7. Tipos de elementos

### 7.1. Mapa

Representa las geometrías de una capa de gvSIG Online.

Opciones principales:

- **Capa operativa:** capa que se mostrará.
- **Estilo:** estilo publicado de la capa; vacío utiliza el estilo por defecto.
- **Campo al pinchar:** atributo cuyo valor se propagará al resto del panel.
- **Mapa base:** fondo cartográfico disponible en el grupo de capas base.
- **Encuadrar sobre los datos:** centra la vista en las entidades al cargar.
- **Mostrar leyenda:** muestra la leyenda de la capa.

Al pulsar una entidad, ésta se resalta y su valor seleccionado se envía a los
elementos vinculados. El mapa resalta las coincidencias sin ocultar las demás
entidades. Pulsar en un espacio vacío retira la selección originada por el
mapa.

Si no se selecciona un mapa base, se utiliza el predeterminado del proyecto,
OpenStreetMap si está disponible o el primero de la lista.

### 7.2. Tabla

Muestra registros en filas y atributos en columnas.

- En **Columnas** se eligen y ordenan los atributos visibles.
- Si no se elige ninguna, se muestran todos los atributos visibles de la capa
  o del conjunto importado.

Al pulsar una fila se crea una selección utilizando el primer atributo
mostrado. Coloque primero la columna que deba relacionarse con el resto del
panel.

### 7.3. Lista

Muestra los valores distintos de un atributo.

- **Campo de la lista:** atributo cuyos valores formarán la lista.

Al pulsar un valor se selecciona o se deselecciona. Se pueden seleccionar
varios valores de la misma variable.

### 7.4. Barras verticales y horizontales

Representan una medida agrupada por categorías.

- **Eje X:** campo de categoría.
- **Eje Y:** campo de valor.
- **Agregación:** cálculo aplicado a cada categoría.
- **Campos de valor:** permite usar varias columnas como puntos del eje.
- **Una serie por cada valor de:** divide el resultado en varias series.
- **Títulos de ejes:** sustituyen los nombres automáticos.

Las barras pueden originar selecciones al pulsarlas.

### 7.5. Líneas

Utiliza las mismas opciones de datos que las barras. Es especialmente útil para
evoluciones temporales:

- En formato largo, utilice el año como categoría y una columna como valor.
- En formato ancho, seleccione varias columnas de valor, por ejemplo
  `poblacion_1996`, `poblacion_2000` y `poblacion_2022`.

Con un campo de serie se dibuja una línea por cada uno de sus valores. Pulsar
una línea selecciona su serie; pulsar un punto selecciona su categoría.

### 7.6. Circular

Distribuye el valor agregado entre categorías. Al pulsar un sector se crea una
selección.

Es más legible con pocas categorías. Para listas largas suele ser preferible
utilizar barras horizontales.

### 7.7. Indicador

Muestra un único valor agregado mediante:

- **Número:** valor destacado; o
- **Acelerador:** valor dentro de una escala con franjas de color.

Para el acelerador se configuran:

- mínimo y máximo de la escala;
- una o varias franjas de color; y
- el límite de cada franja en unidades o en porcentaje del rango.

La última franja llega siempre hasta el máximo. Los límites deben estar
ordenados y quedar dentro de la escala.

El indicador calcula un único resultado con el campo de valor y la agregación.
El campo **Eje X** que aparece actualmente en su formulario no interviene en
ese cálculo.

---

## 8. Colores y leyendas de los gráficos

En modo edición, pulse el recuadro de color de una entrada de la leyenda para
elegir su color. El color queda asociado al nombre de la categoría o serie, por
lo que no cambia si se reordenan los datos.

Pulsar el texto o la entrada de una leyenda, fuera del recuadro de color,
muestra u oculta temporalmente esa serie o categoría.

Los cambios de color deben confirmarse guardando el panel.

---

## 9. Importar CSV y Excel

Los formatos admitidos son:

- CSV;
- XLSX; y
- XLS.

Para importarlos:

1. Configure un elemento distinto de mapa.
2. Elija **Datos importados**.
3. Pulse **Importar CSV / XLSX**.
4. Seleccione el fichero.
5. El conjunto recién importado queda seleccionado automáticamente.

Se importan como máximo **10.000 filas** y sólo la **primera hoja** del libro.
Si se supera el límite, el sistema muestra un aviso y conserva las primeras
10.000. Para volúmenes mayores es recomendable publicar los datos como capa.

La primera fila debe contener nombres de columna únicos y comprensibles.
Conviene evitar celdas combinadas, subtotales y cabeceras intermedias.

### Cómo se almacenan

El navegador lee la hoja y envía sus filas a gvSIG Online. Las filas se guardan
en la base de datos como un conjunto de datos del panel o del proyecto. El
fichero original no se utiliza para pintar los elementos.

Los conjuntos asociados a un proyecto pueden aparecer disponibles para otros
paneles de ese proyecto. Los de un panel global pertenecen a ese panel.

### Formato largo y formato ancho

Para filtrar por año y combinar varias variables, normalmente se recomienda el
**formato largo**:

```text
municipio,año,poblacion
Gurupi,2020,87545
Gurupi,2021,88982
Arraias,2020,10645
```

El formato ancho también puede representarse:

```text
municipio,poblacion_2020,poblacion_2021
Gurupi,87545,88982
Arraias,10645,10821
```

En el segundo caso los años son columnas, no valores de una dimensión, por lo
que no se pueden seleccionar como años independientes del mismo modo. En una
gráfica con varios campos de valor, pulsar puede seleccionar una serie si se ha
configurado un campo de serie, pero no convierte la columna pulsada en una
selección.

---

## 10. Dimensiones del panel

Una dimensión representa un concepto compartido, como **Municipio**, **Región**
o **Año**. Sirve para relacionar orígenes que llaman de forma diferente al
mismo concepto:

- una capa puede utilizar `nome`;
- un CSV puede utilizar `name`;
- ambos pueden asignarse a la dimensión **Municipio**.

### Definir dimensiones

1. Abra el panel en modo edición.
2. Pulse **Dimensiones del panel**.
3. Añada y nombre las dimensiones necesarias.
4. Cierre la ventana.
5. Configure cada elemento vinculado.
6. En **Selección cruzada**, asigne a cada dimensión el atributo de ese
   elemento que la representa.
7. Guarde el panel.

Si existe un atributo cuyo nombre coincide con el de la dimensión ignorando
mayúsculas y acentos, la interfaz puede proponerlo. Si no existe, queda sin
asignar.

### Cuándo son necesarias

Si dos elementos utilizan un atributo con el mismo nombre, la selección puede
relacionarlos directamente. Las dimensiones son especialmente importantes
cuando:

- los atributos se llaman de forma distinta;
- se combinan capas y hojas importadas;
- un nombre ambiguo significa cosas distintas según el origen; o
- se relacionan valores numéricos, como años o códigos.

Los textos se comparan ignorando mayúsculas, acentos y espacios exteriores; por
ejemplo, `GURUPI`, `Gurupi` y ` Gurupi ` se consideran equivalentes.

Para los valores numéricos no se adivinan equivalencias entre atributos de
nombre diferente: deben llamarse igual o estar vinculados mediante una
dimensión. Esto evita confundir un año con un identificador o un código.

---

## 11. Filtros y multiselección

### Seleccionar valores

Una selección puede iniciarse desde:

- una entidad del mapa;
- una fila de tabla;
- un valor de lista;
- una barra o sector;
- un punto o una serie de una gráfica.

Los elementos vinculados pueden:

- recalcular sus valores si la dimensión seleccionada no se dibuja en ellos; o
- mantener el contexto y resaltar la categoría o serie seleccionada.

### Combinar selecciones

- Varios valores del **mismo atributo o dimensión configurada** se combinan con **O**:
  `Gurupi O Arraias`.
- Variables **distintas** se combinan con **Y**:
  `(Gurupi O Arraias) Y año 2020`.

Volver a pulsar un valor ya seleccionado lo retira.

La barra **Selección activa** muestra una etiqueta por variable con todos sus
valores. El aspa de una etiqueta elimina esa variable; **Quitar selección**
elimina todas.

Las selecciones son temporales: no se guardan con el panel y se reinician al
recargar o volver a abrir la página.

### Elementos independientes

Un elemento configurado como **Independiente** no recibe selecciones de los
demás. Es útil para conservar una referencia general mientras el resto del
panel se filtra.

---

## 12. Guardado, publicación y enlaces

El botón **Guardar** persiste:

- la posición y el tamaño de los elementos;
- sus opciones y orígenes de datos;
- las dimensiones y sus correspondencias;
- los colores personalizados; y
- los elementos añadidos o eliminados.

Después de guardar se abre automáticamente el modo lectura.

Para compartir un panel, copie su dirección desde el navegador. El enlace es el
mismo esté o no vinculado a un proyecto.

Si un panel público utiliza una capa privada, el guardado solicita hacerla
pública. Si no dispone de permisos sobre la capa, el panel no puede publicarse
en ese estado.

---

## 13. Recomendaciones

- Empiece con pocos elementos y compruebe las selecciones antes de completar el
  diseño.
- Utilice títulos orientados al lector, no los nombres técnicos de los campos.
- Para series temporales y filtrado cruzado, prefiera datos en formato largo.
- Declare dimensiones cuando combine fuentes o nombres de atributos distintos.
- Use el modo independiente sólo para elementos que deban conservar el total.
- Evite gráficos circulares con muchas categorías.
- Compruebe el panel en escritorio y móvil antes de compartirlo.
- Si una hoja se acerca a 10.000 filas, publique una capa para mejorar escala,
  permisos y mantenimiento.
- No haga público un panel sin revisar antes las capas que utiliza.

---

## 14. Resolución de problemas

### El botón Paneles no aparece en el proyecto

Compruebe que:

- existe un panel vinculado a ese proyecto; y
- su usuario tiene permiso para consultarlo.

### No aparece una capa en el selector

La capa debe:

- ser operativa, no una capa externa;
- ser consultable; y
- ser legible por el usuario que diseña el panel.

No es necesario que esté visible por defecto en el árbol del proyecto.

### Un elemento no recibe una selección

Revise:

1. que esté configurado como **Vinculado**;
2. que su origen contenga el concepto seleccionado;
3. que los atributos tengan el mismo nombre o estén asignados a la misma
   dimensión; y
4. que sus valores sean equivalentes.

Para años, identificadores y otros números, configure una dimensión cuando los
nombres de atributo sean distintos.

### Una selección afecta al atributo equivocado

Defina una dimensión explícita y asigne en cada elemento el atributo correcto.
Evite utilizar el mismo nombre de dimensión para conceptos diferentes.

### El mapa no propaga selecciones

Configure **Campo al pinchar**. Debe ser el atributo que identifica la entidad
o el concepto que se desea enviar al resto del panel.

### La hoja importada no muestra todas las filas

Sólo se importan las primeras 10.000 filas de la primera hoja. Para más datos,
publique una capa.

### El panel público no se puede guardar

Alguna capa utilizada es privada. El usuario debe poder gestionarla y confirmar
su publicación, o bien mantener el panel restringido.

### Los datos aparecen limitados

Los elementos basados en capas cargan como máximo 5.000 entidades. Cuando se
alcanza este límite, el panel muestra un aviso. Reduzca el volumen, filtre los
datos en origen o ajuste la publicación de la capa.

---

## 15. Resumen rápido

### Para consultar

1. Abra el panel.
2. Pulse mapas, listas o gráficos para seleccionar.
3. Combine varios valores si lo necesita.
4. Use la barra superior para retirar selecciones.
5. Amplíe un elemento cuando necesite más detalle.

### Para diseñar

1. Abra **Editar**.
2. Añada y configure los elementos.
3. Ordénelos y cambie su tamaño.
4. Defina dimensiones si combina orígenes.
5. Compruebe la selección cruzada.
6. Pulse **Guardar**.

### Para administrar

1. Abra **Plugins > Paneles**.
2. Cree o configure el panel.
3. Defina proyecto, visibilidad y roles.
4. Diseñe su contenido.
5. Revise capas privadas antes de publicarlo.
