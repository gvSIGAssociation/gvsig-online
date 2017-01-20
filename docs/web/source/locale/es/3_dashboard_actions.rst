3. Acciones del panel de control
================================

3.1 Gestionar usuarios y grupos de usuario
---------------------------------

3.1.1 Crear, modificar y eliminar usuarios
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
La gestión de usuarios y grupos se lleva a cabo desde la entrada *"Usuarios y grupos"* que se encuentra disponible en el menú del panel de control:

.. image:: ../../_static/images/user_group1.png
   :align: center

Desde la vista de usuarios podemos ver el listado de usuarios disponibles, así como crear(1), actualizar(2) o eliminar usuarios(3).

Los campos que aparecen en el formulario de usuarios son los siguientes:

*   **Nombre** y **apellidos** reales del usuario

*   **Nombre de usuario: (Obligatorio)** Alias con el que se accederá al sistema

*   **Contraseña**

*   **Es superusuario**: Indicamos si el usuario implementará el rol de superusuario, con lo que tendrá permisos totales sobre la plataforma

*   **Puede gestionar proyectos**: Indicamos si el usuario implementa el rol de gestión

.. image:: ../../_static/images/user_group2.png
   :align: center

En la parte inferior del formulario de usuarios, aparece un listado con los grupos disponibles. Si asignamos el usuario a algún grupo, este podrá acceder a las entidades definidas en el grupo (proyectos, capas, ...).

3.1.1 Crear y modificar grupos de usuario
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
De la misma manera, desde la vista de grupos podemos ver el listado de grupos disponibles, así como crear(1) o eliminar grupos(2).

.. image:: ../../_static/images/user_group3.png
   :align: center

Los campos que aparecen en el formulario de grupos son los siguientes:

*   **Nombre** del grupo

*   **Descripción** del grupo

.. note::
   Actualmente no está soportada la edición de grupos de usuarios. Si se desea cambiar un grupo de usuarios es necesario eliminarlo y crearlo de nuevo.


3.2 Gestionar servicios
-----------------------

3.2.1 Crear y eliminar espacios de trabajo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Puede crear(1) y eliminar(2) espacios de trabajo desde el listado de espacios de trabajo. Si elimina un espacio de trabajo, se eliminarán de gvSIG Online todos los almacenes de datos y capas asociadas.

.. image:: ../../_static/images/ws1.png
   :align: center

Para crear un espacio de trabajo, proporcione un nombre y una descripción. El nombre del espacio de trabajo no puede contener espacios, signos de puntuación ni caracteres especiales como la *"ñ"*. 
Habitualmente no es necesario modificar la URL de los servicios (generada automáticamente).


3.2.2 Crear, modificar y eliminar almacenes de datos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Puede añadir(1), actualizar(2) y eliminar(3) almacenes de datos desde el listado de almacenes de datos.

.. image:: ../../_static/images/ds1.png
   :align: center

Es importante entender que para poder añadir un almacén de datos, debemos partir de una fuente de datos que exista previamente. 
Por ejemplo, para poder añadir un almacén de datos de tipo PostGIS vectorial, la base de datos espacial debe existir previamente. 
De esta forma, los que estamos haciendo es registrar en gvSIG Online (y en Geoserver) los parámetros de conexión a dicha base de datos. 
De la misma forma, para añadir un almacén de datos de tipo ráster, el fichero ráster debe existir previamente en el servidor
(en este caso estamos registrando en gvSIG Online la ruta a dicho fichero ráster).


En el formulario de creación de almacén de datos deberemos seleccionar el espacio de trabajo al que pertenecerá, el tipo de almacén, 
el nombre (sin caracteres especiales) y los parámetros de conexión.

El formulario incluye diversos ejemplos de parámetros de conexión para cada tipo de almacén.

.. image:: ../../_static/images/ds2.png
   :align: center

En caso de que el almacén de datos sea de tipo raster el formulario cambiará y nos permitirá seleccionar el fichero que compondrá el almacen.

.. image:: ../../_static/images/ds3.png
   :align: center

Al abrir el dialogo de seleccionar archivo, este nos mostrará un ventana con el gestor de ficheros, desde donde podremos seleccionar el archivo raster que habremos subido previamente.

.. image:: ../../_static/images/ds4.png
   :align: center

.. note::
   	La eliminación de un almacén de datos elimina todas las capas asociadas al almacén. 
   	
	Por contra, no se eliminará la fuente de datos asociada (la base de datos espacial o el fichero ráster correspondiente).

3.2.3 Publicar, crear, modificar y eliminar capas
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Desde el listado de capas podemos acceder a la gestión de las mismas. Podemos publicar capas existentes en almacenes de datos(1), o crear capas vacías(2) definiendo de forma manual los campos.

.. image:: ../../_static/images/layer1.png
   :align: center

Sobre cada una de las capas podemos realizar las siguientes operaciones:

*   **Actualizar capa (3):** Desde donde se puede modificar el título grupo al que pertenece la capa, propiedades (visible, consultable, etc …), así como los permisos de lectura y escritura de la capa.

*   **Configurar capa (4):** Podemos definir alias a los nombres de los campos, así como definir que campos serán visibles para las herramientas del visor (herramienta de información, tabla de atributos, etc …).

.. image:: ../../_static/images/layer2.png
   :align: center

*   **Limpiar caché (5):** Limpia la caché de la capa en el servidor de mapas. Muy útil cuando realizamos cambios en la simbología de la capa.

*   **Eliminar capa (6):** Elimina la capa y estilos asociados.

Publicar capa
*************
Para publicar una capa existente en un almacén de datos. Seleccionaremos el botón *"Publicar capa"*, una vez accedamos a la vista de publicación nos aparecerá un formulario.

.. image:: ../../_static/images/publish1.png
   :align: center
   
Los pasos para publicar una capa son los siguientes:

*	Seleccionamos el almacén de datos donde se encuentra la capa que desamos publicar.

*	A continuación seleccionamos en el desplegable el recurso (Solo aparecen los recursos que aún no han sido publicados).

*	Introducimos un titulo para la capa.

*	Seleccionamos el grupo de capas al cual queremos asignar la capa (debe existir previamente).

*	Seleccionamos las propiedades de la capa en el visor (visible, cacheada, imagen simple, consultable).

*	Si lo deseamos podemos introducir una descripción de la capa.

*	A continuación seleccionamos el botón *"Sgiuiente"*, lo que nos llevará a la vista de permisos.

Por último aplicaremos los permisos de lectura y escritura a la capa.

.. image:: ../../_static/images/permissions.png
   :align: center
   
.. note::
   	Por defecto todas las capas pueden ser leídas por cualquier usuario, pero solo pueden ser escritas por los usuarios con rol de **superusuario**.
   	
Crear capa vacía
****************
TODO

.. image:: ../../_static/images/create_layer1.png
   :align: center


3.2.4 Gestión de bloqueos
~~~~~~~~~~~~~~~~~~~~~~~~~
Podemos consultar los bloqueos activos desde el listado de bloqueos, así como desbloquear capas bloqueadas.

.. image:: ../../_static/images/block1.png
   :align: center

3.2.5 Crear, modificar y eliminar enumeraciones
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
TODO


3.3 Gestionar archivos
----------------------

3.3.1 Crear directorios
~~~~~~~~~~~~~~~~~~~~~~~

Podremos crear todos los subdirectorios que deseemos para organizar nuestros archivos dentro de un directorio raíz. 
Para ellos seleccionaremos el botón *“crear directorio”*, e introduciremos el nombre del nuevo directorio.

|100002010000068B0000010873918762_png|

Con esto se habrá creado un nuevo subdirectorio dentro del directorio raíz.


3.3.2 Operaciones sobre archivos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
En la parte derecha de cada archivo o directorio tendremos un menú desplegable con las operaciones que podemos realizar sobre el mismo. En caso de subdirectorios, nos aparecerá la opción “
*eliminar directorio”*.

Si la seleccionamos eliminaremos el subdirectorio y todo su contenido.

Actualmente los formatos soportados por el administrador de archivos son *"Shapefile y GeoTIFF"*.

Los archivos se pueden subir seleccionando uno a uno o comprimidos en formato zip.

El formato shapefile, es un formato multiarchivo y tienen un conjunto de archivos requerido para su correcto funcionamiento. Los archivos requeridos tienen las siguientes extensiones:

*   **shp:** Almacena las entidades geométricas de los objetos.

*   **shx:** Almacena el índice de las entidades geométricas.

*   **dbf:** base de datos en formato dBASE, donde se almacena la información de los atributos.

Además de estos tres archivos requeridos, opcionalmente se pueden utilizar otros para mejorar el funcionamiento en las operaciones de consulta a la base de datos, información sobre la proyección cartográfica o almacenamiento
de metadatos. Entre ellos destaca:

*   **prj:** Es el archivo que guarda la información referida al sistema de coordenadas en formato WKT

Por tanto ya sea seleccionando uno a uno o comprimidos tendremos especial atención en que todos ellos estén presentes.

|1000020100000684000001F61189782B_png|

Una vez subido los archivos nos aparecerá en el directorio donde lo hayamos subido, aunque únicamente veremos el archivo con extensión *"SHP"*.

|1000020100000695000001376BA0C7E1_png|

Para eliminar el archivo shapefile seleccionaremos en el menú de operaciones la opción *“eliminar archivo”*, esto borrará en el servidor tanto el archivo shp como el resto de archivos asociados (.shx, .dbf, .prj, …).

Entre las operaciones que podemos realizar sobre los archivos de tipo shapefile, se encuentra la de *“Exportar a base de datos”*, para ello seleccionamos la operación en el menú de operaciones del archivo.

|100002010000069400000137DD1411FC_png|

A continuación se mostrará el formulario con los parámetros necesarios para realizar la exportación.

|100002010000068E000001770D7737A4_png|

En el formulario deberemos elegir el almacén de datos de destino (de tipo base de datos PostGIS), así como especificar el sistema de referencia de coordenadas (CRS) y la codificación de caracteres de la capa a subir.

También podremos especificar si deseamos crear una nueva tabla en el almacén de datos, añadir registros o sobreescribir una tabla existente.

Las dos últimos opciones deben utilizarse con cuidado, ya que borrarán o modificarán datos existentes.

GeoTIFF es un estandar de metadatos de domino público que permite que información georreferenciada sea encajada en un archivo de imagen de formato TIFF.

La información adicional incluye el tipo de proyección, sistemas de coordenadas, elipsoide y datum y todo lo necesario para que la imagen pueda ser automáticamente posicionada en un sistema de referencia espacial.

Los archivos GeoTIFF disponen de una extensión .tif o .tiff.

Para subirlos procederemos de la misma forma que con los archivos shapefile, solo que en este caso será un único archivo.


3.4 Gestionar proyectos
-----------------------

3.4.1 Crear, modificar y eliminar proyectos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Para crear un nuevo proyecto seleccionaremos en el menú de la izquierda la opción *"Proyectos"*, lo que nos llevará a la vista listado deproyectos.

|1000020100000780000001BC2554AE2C_png|

A continuación seleccionamos la opción *"Añadir proyecto"*, que se encuentra en la parte superior derecha, para abrir la vista que nos permitirá crear un nuevo proyecto.

|10000201000007700000038A08741B24_png|

El formulario para crear un nuevo proyecto está formado por los siguientes campos:

*   **Nombre** del proyecto

*   **Descripción** del proyecto

*   **¿Es público?:** Indicamos si el proyecto será acccesible publicamente, sin necesidad de estar autenticado en la plataforma

*   **Vista**: Centraremos el mapa y le añadiremos el zoom deseado

*   **Imagen**: Logo del proyecto que se mostrará en el listado de proyectos. Si no se define ninguna se asignará una por defecto.

Además de estos campos en la parte inferior aparecerán dos listados:

|100002010000066C000001EB8B677957_png|

*   **Grupos de usuario**: Grupos de usuario(roles) para los que el proyecto estará disponible. Los usuarios administradores tendrán acceso a todos los proyectos.

*   **Grupos de capas**: Grupos de capas que estarán disponibles en el visor para este proyecto.

Para modificar un proyecto existente seleccionaremos el botón *"Actualizar proyecto"*, que se encuentra en la parte derecha en cada fila del listado de proyectos.

Para eliminar un proyecto existente seleccionaremos el botón *"Eliminar proyecto"*, que se encuentra en la parte derecha en cada fila del listado de proyectos.

Para cada uno de los proyectos es posible definir un orden particular de las capas y grupos de capas. Para ello en el listado de proyectos seleccionaremos el botón *"Ordenar TOC"*.

A continuación en la vista aparecerán los grupos de capas y dentro de ellos si los desplegamos las capas. Las capas pueden ser ordenadas mediante las flechas que se encuentran en la parte derecha de las mismas, mientras que los grupos de capas pueden ser ordenados usando la técnica de arrastrar y soltar.

|1000020100000694000001C21AD35E12_png|


3.5 Gestionar simbología
------------------------

3.5.1 Leyenda de símbolo único
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
La leyenda de símbolo único es la más simple de todas y nos permite definir un estilo que será aplicado a todos los elementos de una capa de la misma forma, sin hacer ningún tipo de distinción.

|100002010000067E0000024F0C8625B0_png|


La vista para crear una leyenda de símbolo único está divida en tres áreas:

El área de metadatos(recuadro rojo) contiene los siguientes campos:

*   **Nombre**: El nombre del estilo se genera por defecto por tanto no es necesario definirlo.

*   **Título**: Título que aparecerá en la leyenda que se muestra en el visor.

*   **Escala mínima**: Escala mínima a partir de la cual será mostrada la leyenda (Si el valor es -1 no se tendrá en cuenta).

*   **Escala máxima**: Escala máxima hasta la cual será mostrada la leyenda (Si el valor es -1 no se tendrá en cuenta).

*   **Por defecto**: Si seleccionamos este campo el estilo será el que se muestre por defecto en el visor.

El área de pre-visualización (recuadro morado) contiene el mapa donde podremos observar el estilo de la leyenda. 
Para actualizar la pre-visualización lo haremos a través del botón *"Actualizar previsualización"* situado en la parte superior derecha.

El área de simbolizadores (recuadro verde) Desde aquí iremos añadiendo los distintos simbolizadores que conformarán finalmente el símbolo.

Tenemos 3 opciones:

*   **Importar un símbolo desde una biblioteca:** Se nos mostrará un dialogo con desplegable donde seleccionaremos la biblioteca de símbolos. A continuación seleccionaremos el símbolo.

|10000201000001200000002A6A1F01B9_png|

|10000201000002730000011396096EA6_png|

*   **Añadir uno o varios simbolizadores:** Como hemos comentado anteriormente un símbolo puede estar formado por uno o más simbolizadores.

|10000201000001200000002A6A1F01B9_png|

Podremos editar o eliminar un simbolizador desde los botones que se encuentran en la parte derecha.

|100002010000062E0000004ED4160A40_png|

Al seleccionar el botón de edición se abrirá un dialogo donde podremos configurar los valores de las propiedades del simbolizador en función de us tipo.

|10000201000002650000014A9E6B1115_png|

En caso de tener varios simbolizadores podemos definir el orden de visualización de los mismos mediante la técnica de arrastrar y soltar. Para ello seleccionaremos el simbolizador y lo arrastraremos a la posición deseada.

|1000020100000641000000B45326936D_png|

*   **Añadir una etiqueta:**Las etiquetas son tipo especial de simbolizadores de tipo texto. Para añadir una nueva etiqueta seleccionaremos el botón *"Añadir etiqueta"*.
    Solo podremos añadir una etiqueta por símbolo por tanto una vez añadida una etiqueta el botón desaparecerá, y solo volverá a aparecer si esta es eliminada.

|10000201000001200000002A6A1F01B9_png|

Como cualquier otro simobolizador una vez añadida podremos editar sus propiedades.

|100002010000025F000002736533B86D_png|

3.5.2 Leyenda de valores únicos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
La leyenda de valores únicos genera una clasificación de símbolos en función de un campo de la capa.

|100002010000066F0000037F31B49968_png|

Seleccionaremos el campo por el que deseamos realizar la clasificación (1), y a continuación se crearán de forma automática las clases correspondientes.

Cada una de las clases creadas puede ser modificada de la misma forma que si se tratara de un símbolo único.

3.5.3 Leyenda de intervalos
~~~~~~~~~~~~~~~~~~~~~~~~~~~
El tipo de leyenda más habitual para representar datos numéricos quizá sea la de intervalos, que permite clasificar los valores disponibles en los distintos elementos en una serie de rangos.
Para generar la leyenda de intervalos en primer lugar seleccionaremos el campo por el que deseamos realizar la clasificación (1) (solo aparecerán los campos numéricos),
y a continuación seleccionaremos el número de intervalos ().

|10000201000006730000037EE47B6A4B_png|

Cada una de las clases creadas puede ser modificada de la misma forma que si se tratara de un símbolo único.

3.5.4 Leyenda de expresiones
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Mediante esta leyenda podremos asignar un tipo de símbolo a los elementos que cumplan con una determinada condición o expresión. Y, por supuesto, podemos tener en una misma leyenda tantas condiciones como deseemos.

Para crear un un símbolo seleccionaremos el botón *"Añadir nueva regla"* (1), lo que nos creará un nuevo símbolo con los valores por defecto.

Cada una de las clases creadas puede ser modificada de la misma forma que si se tratara de un símbolo único.

Para definir la condición de filtrado seleccionaremos en el menú de herramientas la opción *"Editar filtro"* (2).

|100002010000067300000116AD76FB10_png|

A continuación se nos mostrará un diálogo, desde donde podremos definir el filtro con la condición deseada.

|1000020100000261000001C7407B359A_png|

3.5.5 Mapa de color (ráster)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Mediante esta leyenda podremos asignar una tabla de colores a una capa de tipo ráster. Las rampas de color se utilizan, por ejemplo, para aplicaciones específicas, como mostrar la elevación o precipitación.

Para añadir una nueva entrada a la tabla de colores seleccionaremos el botón *"Añadir entrada de color"* (1).

|100002010000067A0000029A809A286E_png|

|100002010000001500000017FA9CFD1C_png|

Podremos añadir tantas entradas de color como deseemos. Para editar los valores de cada una de las entradas seleccionaremos el botón editar.

A continuación se nos mostrará un dialogo para que configuremos los valores.

|100002010000025F000001C514240607_png|

*   **Color:** Seleccionaremos el color deseado para la entrada.

*   **Cantidad:** Aquí seleccionaremos el valor del ráster por el que filtraremos.

*   **Etiqueta:** Etiqueta que se mostrará al representar la leyenda para este valor.

*   **Opacidad:** Nivel de opacidad para esta entrada de color.



3.5.6 Bibliotecas de símbolos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Las bibliotecas de símbolos nos permiten crear y agrupar símbolos genéricos que posteriormente podremos importar desde las leyendas de capa.

Para crear una nueva biblioteca de símbolos seleccionaremos la entrada *"Bibliotecas de símbolos"* en el menú de simbología.

|1000020100000774000001CFFA76A596_png|

Para crea una nueva biblioteca seleccionaremos el botón *"Añadir biblioteca"* que se encuentra en la parte superior derecha, y rellenaremos los campos nombre y descripción en el formulario.

Podremos también importar bibliotecas que hayan sido creadas previamente en la plataforma. Las bibliotecas de símbolos son archivos están formadas por un archivo ZIP que contiene un fichero con extensión .sld por cada uno de los símbolos y un directorio resources con loas imágenes en caso de que haya símbolos puntuales de tipo imagen.

Para añadir símbolos a una biblioteca seleccionaremos la opción actualizar biblioteca en el listado (botón verde).

Podremos añadir 4 tipos de símbolos: Gráficos externos (imágenes), puntos, líneas y polígonos.

El interfaz para añadir puntos líneas y polígonos es similar al descrito en el punto 6.2.1.
En caso de que el símbolo que deseemos añadir sea de tipo imagen el interfaz nos permitirá seleccionar la imagen desde nuestro sistema de ficheros local.

|100002010000067A000001BC75651FB5_png|

.. note::
   Actualmente únicamente se soportan imágenes en formato PNG.

Conforme vayamos añadiendo símbolos estos irán apareciendo en la vista de la biblioteca, desde donde podremos seleccionarlos para modificarlos o eliminarlos.

|100002010000067F00000166CFF00956_png|

Podremos exportar cualquier biblioteca de símbolos, para tener un resguardo de la misma y poder restaurarla posteriormente o compartirla con otros usuarios de la aplicación. Para ello seleccionaremos el botón naranja.

Al seleccionar exportar se genera un archivo ZIP que contiene la definición de cada uno de los símbolos en formato SLD, y un directorio “resources” que contendrá las imágenes de los símbolos que sean de tipo gráfico externo.

Por último para eliminar una biblioteca seleccinaremos el botón rojo.

Al eliminar la biblioteca borraremos esta y todos los símbolos que hayan asociados a ella.
