4. Funcionalidades del visor de mapas
=====================================

El visor de mapas es la interfaz de visualización de la plataforma que permite la visualización de los proyectos configurados desde el panel de control.  

.. image:: ../../_static/images/viewer1.png
   :align: center

Está formado por una serie de componentes los cuales están ubicados en una zona específica de la página web (Mapa, menú superior, panel de contenidos, controles).

Menú superior
*************

En el menú superior encontramos en primer lugar el botón que nos permite mostrar u ocultar el panel lateral de contenidos.

A continuación si el plugin de geocdificación está activo encontramos el cuadro de búsqueda. Desde aquí podremos encontrar localizaciones en el mapa en función de la configuración.

En la parte derecha del menú superior tenemos en primer lugar el botón de impresión, y por último nos encontramos con el menú de sesión, desde el cual podremos cerrar la sesión o volver al panel de control.


Panel de contenidos
*******************
El panel de contenidos se encuentra en la parte izquierda del visor y está formado por 3 pestañas: el árbol de capas, la leyenda y el panel de resultados.

El árbol de capas contiene la jerarquía de capas que ha sido definida desde la interfaz de administración para la aplicación que se está ejecutando.

El árbol de capas está formado por grupos de capas y capas. Los grupos de capas tienen como finalidad agrupar las capas que poseen rasgos comunes.

Se puede dividir las estructura del árbol en 2 regiones:

*   **Capas base:** Este grupo está formado por una serie de capas base que son definidas en tiempo de desarrollo, es decir, no se pueden gestionar desde el interfaz de administración. (OpenStreetMap, Bing, Google Maps, Ortofotos locales, capas de catastro, etc)

*   **Capas propias de la aplicación:** Está formado por el resto de grupos de capas que han sido definidas propiamente para la aplicación que se está ejecutando (Capas temáticas).

.. image:: ../../_static/images/viewer3.png
   :align: center
   
Todas las capas (excepto las capas base predefinidas), disponen de un menú con una serie de acciones disponibles en función de la configuración.

.. image:: ../../_static/images/viewer4.png
   :align: center

Para ver la leyenda del mapa actual seleccionaremos la pestaña *"Leyenda"* en la barra de navegación. El panel de leyenda muestra la leyenda de las capas que hay activas y visibles en el momento de la consulta.

.. image:: ../../_static/images/legend.png
   :align: center


4.1 Imprimir mapa
--------------------
TODO


4.2 Mostrar tabla de atributos
------------------------------

Si la capa dispone de un origen de datos vectorial aparecerá disponible la acción *"Tabla de atributos"*. Al seleccionar la acción se abrirá una ventana que contendrá la tabla de atributos de la capa.

La tabla de atributos ofrece una serie de funcionalidades:

*   **Seleccionar elementos sobre el mapa:** Para seleccionar una elemento sobre el mapa seleccionaremos la fila de la tabla que deseemos, y a continuación presionaremos el botón *"Zoom a la selección"*, que se encuentra en la parte superior izquierda de la tabla. Para limpiar la selección de un elemento presionaremos el botón *"Limpiar selección"*.

*   **Filtro de búsqueda rápida:** La tabla de atributos nos ofrece también la funcionalidad de búsqueda rápida. Para ello introduciremos en el cuadro de búsqueda que se encuentra en la parte superior derecha el patrón que deseamos buscar. Automáticamente la tabla se irá actualizando con los campos que cumplan con el patrón de búsqueda introducido.

.. image:: ../../_static/images/attribute.png
   :align: center

La tabla de atributos muestra los resultados paginados de 10 en 10. Para navegar entre los resultados en la parte inferior de la tabla se muestra un navegador de páginas.


4.3 Editar capa
------------------------------

** Esta acción requiere que el usuario pertenezca a un grupo con permisos de escritura.

Para poner una capa en modo de edición seleccionamos en el menú de acciones la entrada *"Editar capa"*.

Al comenzar la edición se añade al mapa una nueva barra de herramientas de edición, en función del tipo de geometría de la capa ya sea punto, linea o polígono.

|10000201000003690000017E0831F857_png|

La barra de herramientas de edición dispone de 4 herramientas:

|100002010000002900000078CBF75D2B_png|

**Añadir un nuevo elemento a la capa**

Para añadir un nuevo elemento seleccionamos la herramienta de dibujo y a continuación procedemos a dibujar el elemento sobre el mapa (punto, linea o polígono). 

Una vez dibujado elemento aparecerá en la barra de navegación un formulario para que introduzcamos los valores de los atributos del elemento.

Una vez hallamos rellenado el formulario seleccionaremos el botón
* “Guardar”*
**. **
En ese momento la nueva geometría y sus atributos asociados serán persistidos en la base de datos.

Si presionamos el botón
*“Cancelar”*
la geometría será eliminada del mapa y se cerrará el formulario.

|10000201000001900000024A97752C4D_png|

**Modificar un elemento existente**

Seleccionaremos la herramienta de modificar elementos en la barra de edición. A continuación seleccionaremos el elemento sobre el mapa. Una vez hayamos seleccionado el elemento podremos editar su geometría seleccionando y moviendo
los vértices en caso de ser linea o polígono, o desplazando el elemento en caso de ser un punto.

También se desplegará en la barra de navegación un formulario con el valor de los atributos del elemento.

Una vez hayamos terminado de modificar la geometría y/o datos alfanuméricos del elemento procederemos como en el apartado anterior seleccionando el botón
*“Guardar” o “Cancelar”*
.

**Eliminar un elemento existente**

Seleccionaremos la herramienta de eliminar elementos en la barra de edición. A continuación seleccionaremos el elemento que deseamos eliminar sobre el mapa. Una vez hayamos seleccionado el elemento se desplegará en la barra de navegación un formulario con el valor de los atributos del elemento.

En esta ocasión dispondremos del botón
*“Eliminar”*
,
el cual eliminará el elemento del mapa y de la base de datos.


4.4 Modificar opacidad
---------------------

Para modificar la opacidad de la capa seleccionaremos el valor de opacidad deseado en el slider del menú de acciones de la capa.

|100002010000015F000000331DC3D460_png|


4.5 Controles de zoom
---------------------

Los controles de zoom que se encuentran en la barra de herramientas, permiten alejar o acercar la visualización del mapa.

|10000201000000220000004205B1E582_png|



Además de con los controles de zoom también podremos acercar o alejar la visualización con la rueda del ratón.

4.6 Información en el punto
---------------------------
La herramienta de información en el punto, nos permite obtener la información en una coordenada determinada de las capas que hay visibles.

|1000020100000029000000AE45648EF1_png|

Para obtener la información en el punto seleccionamos la herramienta y hacemos click en el mapa en la ubicación deseada.

Se mostrará un popup en las coordenadas seleccionadas donde aparecerá un listado de elementos que intersectan.

Si deseamos ampliar la información seleccionaremos el elemento y nos mostrará información extendida en el panel de resultados.

|100002010000037F0000029CF6E7624E_png|


4.7 Medir distancia
-------------------
Esta herramienta permite medir la longitud entre dos o más puntos.

|1000020100000029000000AE45648EF1_png|

Para comenzar a medir hacemos click en el punto de origen y a continuación nos desplazamos al punto destino (o punto intermedio). Para terminar hacemos doble click sobre el punto destino.

|100002010000041A000001D1201E6DEA_png|


4.8 Medir área
--------------
Esta herramienta permite medir el área contenida en un polígono.

|1000020100000029000000AE45648EF1_png|

Para comenzar a medir hacemos click en el punto de origen y a continuación dibujaremos el resto de puntos que definen el área a medir. Para terminar realizaremos doble click sobre el punto que cierra el polígono.

|10000201000003D0000002048F3A9C90_png|


4.9 Buscar por coordenadas
--------------------------
La modalidad de búsqueda inversa nos permite buscar una localización a partir de unas coordenadas dadas.

|1000020100000029000000AE45648EF1_png|

Para proceder a la búsqueda inversa, en primer lugar debemos seleccionar el sistema de referencia en el que introduciremos las coordenadas. Los sistemas de coordenadas vendrán predefinidos para cada aplicación.

Una vez hayamos seleccionado el sistema de coordenadas, introduciremos los valores para la longitud y latitud en caso de ser un sistema con coordenadas geográficas o X/Y
en caso de ser un sistema con coordenadas proyectadas.

|1000020100000387000001286832345E_png|


4.10 Posición actual
~~~~~~~~~~~~~~~~~~~~~
Permite ubicar nuestra posición actual y centrar el mapa sobre ella. Requiere que aceptemos los permisos que nos solicitará el navegador.

|1000020100000029000000AE45648EF1_png|


4.11 Escala numérica
~~~~~~~~~~~~~~~~~~~~~
Se encuentra situada en la parte inferior izquierda del mapa.

|10000201000000870000002B34D59522_png|


4.12 Posición del ratón
-----------------------
Muestra la posición del ratón en el sistema de coordenadas seleccionado.

Podremos cambiar entre cualquiera de los sistemas de coordenadas configurados para la aplicación, seleccionando desde el desplegable.

|10000201000000E30000007E48C8E0BB_png|

|10000201000000CD00000028216587DE_png|



4.13 Mapa de referencia
-----------------------
El mapa de referencia se encuentra situado en la parte inferior derecha del mapa, y nos permite mantener una referencia de nuestra posición cuando nos encontramos a niveles de zoom bajos.

|10000201000001B900000120CCEE3BF0_png|