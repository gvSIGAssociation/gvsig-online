Geocodificador
==============

Introducción
------------

El geocodificador nos permite buscar lugares y ubicarlos en el mapa.

Una vez introducida la cadena de búsqueda, nos aparece un listado con los posibles candidatos. 

.. image:: ../_static/images/search_1.png
   :align: center
   

Tendremos que seleccionar uno de estos candidatos y a continuación el mapa se centrará sobre su localización.

.. image:: ../_static/images/geocoding_find.png
   :align: center
   
   
También existe la posibilidad de hacer una geocodificación inversa (averiguar la dirección marcando una posición en el mapa). Para ello, bastará hacer click con el botón derecho del ratón sobre el punto del mapa del que se quiera obtener la dirección. 

Dependiendo los proveedores que tengamos disponibles, saldrán más o menos opciones:

.. image:: ../_static/images/geocoding_reverse.png
   :align: center



Conociendo el geocodificador
----------------------------
   
El plugin de geocoding permite definir hasta 4 tipos de servicios diferentes, además de configurarlos y establecer el orden de priorida en el que se mostrarán los resultados entre ellos.

.. image:: ../_static/images/geocoding_move.png
   :align: center


En todos ellos se les puede indicar una categoría (para englobar los resultados de ese proveedor bajo un separador) y se les puede asignar un icono que marcará cada una de las sugerencias propuestas. Luego, según las características de cada uno, se requerirán unos parámetros u otros para que puedan funcionar:

.. image:: ../_static/images/search_2.png
   :align: center



Servicios de Nominatim
----------------------

Nominatim es el motor de búsqueda para datos de OpenStreetMap. 

Aunque se accede al servicio web a través de la url que aparace en 'Parámetros avanzado', se permite configurarla por si cambiara.
 
Otro de los aspectos editables es la posibilidad de acotar los resultados a una zona indicando su country_code en los 'Parámetros avanzados' ('es' para España, por ejemplo)


.. image:: ../_static/images/nominatim.png
   :align: center
 
Servicios de Google Maps
------------------------

También se puede añadir como proveedor de búsquedas el motor de Google Maps.

Entre sus parámetros específicos se definen por defecto las rutas a los servicios (por si cambiaran poder editarlas). 

También requiere indicar una key de Google que dé entrada a los servicios de Google (más información en API/Key de Google: https://developers.google.com/maps/documentation/javascript/get-api-key)


.. image:: ../_static/images/google.png
   :align: center 

Servicios de CartoCiudad
------------------------

CartoCiudad ofrece la posibilidad de descargar la cartografía por regiones y poder añadirla como proveedor de datos. Para ello, se tiene que ir a la página oficial del Centro Nacional de Información Geográfica (CNIG) e ingresar a su Centro de Descargas_.

 .. _Descargas: http://centrodedescargas.cnig.es/CentroDescargas/buscadorCatalogo.do?codFamilia=02122

- Marcar en *seleccione producto* 'CartoCiudad' y en *División administrativa*, 'Provincias'. Marcar la que se requiera y descargar el ZIP.

.. image:: ../_static/images/centro_descargas_1.png
   :align: center

- Una vez descagado y descomprimido, se cargará en gvsigOnline a través del *Administrador de archivos* los recursos con sus extensiones (.shp; .dbf y .shx):
  
  - tramo_vial; 
  - portal_pk
  - municipio_vial.dbf (No tiene .shp)
  - toponimo (**esta capa es opcional de usarla, depende de las carpetas descargadas por provincia puede contener o NO este fichero**)

  
  
- Luego se llevarán a una BD desde el *administrador de archivos* a través de la opción 'Exportar a base de datos' de cada archivo con extensión (.shp), en el que se marcará como nombre el mismo del fichero (sin la extensión) **en minúsculas**. La *Codificación de caracteres* será: 'autodetectar' y el *sistema de coordenadas*: 'ETRS89 LatLon'


.. image:: ../_static/images/centro_descargas_4.png
   :align: center


.. image:: ../_static/images/centro_descargas_5.png
   :align: center

.. note:: 
   El sistema de referencia seleccionado será el que traiga por defecto las capas descargadas del CNIG en su archivo con extensión *.prj*.


Una vez realizada esta tarea, será necesario cargar la cartografía de regiones de España y los límites provinciales, por lo que habrá que repetir el proceso con los siguientes pasos:

- En el Centro de Descargas_., seleccionar en productos *Información geográfica de referencia*: 'Lineas límite municipales' y buscamos en *división dministrativa*  la provincia, municipio o comunidad que se quiera.

.. image:: ../_static/images/centro_descargas_2.png
   :align: center

- Descargar el ZIP de la sección 'Líneas límite municipales'

.. image:: ../_static/images/centro_descargas_3.png
   :align: center

- El fichero comprimido desacargado contiene diversas carpetas, de las cuales solo usaremos las dos siguientes:

  - **recintos_municipales_inspire_peninbal_etr89**
  - **recintos_provinciales_inspire_peninbal_etr89**

- Cargar en el 'Administrador de archivos' la capa que contiene cada carpeta con sus extensiones correspondientes (.shp; .dbf y .shx).
  
- De la carpeta **recintos_municipales_inspire_peninbal_etr89** exportaremos a la BD el fichero (.shp) con el nombre '**municipio**', *Codificación de caracteres*: 'autodetectar' y *sistema de coordenadas*: 'ETRS89 LatLon'
- y de la carpeta **recintos_provinciales_inspire_peninbal_etr89**, exportaremos a la BD el otro fichero (.shp) con el nombre '**provincia**', *Codificación de caracteres*: 'autodetectar' y *sistema de coordenadas*: 'ETRS89 LatLon'
  
.. note::
   Tanto las capas anteriores como éstas de 'líneas límites municipales' deben exportarse en el mismo almacén de la base de datos y *No es necesario hacer públicas éstas capas en el visor de mapas*.  
  
- Por último, para dar de alta el proveedor, se ingresa con la entrada **Geocoding** del menú y se elige el *tipo de proveedor*: 'Cartografía de CartoCiudad', será necesario indicar el almacén de datos en el que se han exportado todas las capas indicadas.

.. note::
   Cuando se ñade este proveedor de Cartociudad *no* se ofrece la posibilidad de seleccionar icono, ya que disponen de los suyos propios para identificar las calles, toponimos, municipios y demás entidades que se indexan a través de este servicio.


- Una vez se ha dado de alta correctamente el proveedor, se redirige a la página que permite cargar los datos en el sistema. Existen dos opciones:

  - **Carga total**: borra los datos anteriores de ese proveedor (si los hubiera), y los sube de nuevo.
  - **Carga parcial**: Sube sólo las entidades actualizadas desde la última vez que se cargaron datos (las entidades borradas no se eliminarán, sólo las actualizadas).
 

  
Otros servicios del usuario
---------------------------

Por otro lado, se pueden incluir en el geocodificador otros resultados procedentes de capas propias.

.. note::
   Se requiere que la capa haya sido publicada en algún proyecto - geoportal.
   
Se precisará:   

  - El espacio de trabajo
  - El almacén de datos
  - La capa a incorporar al geocodificador
  - Un campo que identifique de forma unívoca (es decir, que no hayan dos iguales) a cada elemento a buscar
  - El campo que contiene el texto que se buscará por el geocodificador
  - El nombre del campo que contiene la geometría
    
Igual que ocurría con los servicios de Cartociudad, una vez definido el proveedor, habrá que hacer una carga total de los datos para que el geocodificador empiece a incluirlos en los resultados de las búsquedas.
  
