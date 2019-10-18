2. Conceitos
============


2.1 Painel de controle
--------------------
O painel de controle é a principal interface de administração de gvSIG Online. 

O painel de controle é dividido em vários componentes:

*   **Barra superior:** Na barra superior encontramos o menu de sessão de usuário e o seletor de idioma.

*   **Menu principal:** Onde podemos ter acesso à gestão das entidades da plataforma (usuários e grupos, serviços, estilos, …).

*   **Conteúdo principal:** Na área de conteúdo as vistas serão carregadas com os formulários dependendo da seleção que fizermos no menu principal. 
    
.. image:: ../images/dashboard_main.png
   :align: center
    
Dependendo da função que o nosso usuário implementar, o painel de controle irá mostrar alguns componentes ou outros.  

Ao acessar o painel de controle padrão, a exibição *“Início”* é mostrada, onde um resumo é mostrado com as informações do usuário e uma lista com os projetos que o usuário tem disponíveis.

.. Anotação::
   Se o nosso usuário não implementar o papel de superusuário, e tiver apenas um projeto atribuído a ele, ele irá acessar o projeto diretamente sem passar pelo painel de controle.
   
   
2.2 Visor de mapas
------------------
O visualizador de mapas é a interface de visualização da plataforma que permite a visualização dos projetos configurados a partir do painel de controle. 

.. image:: ../images/viewer1_2.png
   :align: center

A plataforma oferece dois tipos de visualizadores de mapas:

*   **Visor público:**  Acessível a qualquer usuário sem ter que se registrar na plataforma. Oferece uma série de funcionalidades básicas: Zoom, ferramentas de busca, medição e informação, etc. 

*   **Visor restrito:** Acessível apenas para usuários registrados da plataforma. Também dependendo do nível de acesso do usuário, este tipo de visualizador oferecerá funcionalidades específicas, além das básicas.
	
	
2.3 Utilizadores e grupos de utilizadores
---------------------------------
O GvSIG Online utiliza duas entidades principais tanto para gerenciar a autenticação quanto para gerenciar permissões para processamento de dados e acesso a serviços da plataforma.
Estas duas entidades são os *"usuários"* e os *"grupos de usuários"*.

Todas as informações de autenticação são centralizadas a partir do serviço LDAP.

.. image:: ../images/ldap.png
   :align: center

2.3.1 Roles de usuario
~~~~~~~~~~~~~~~~~~~~~~
Cada usuario implementa un rol, el cual le confiere una serie de permisos que definen el acceso a la plataforma y como el usuario interactua con las entidades.

Los roles que puede implementar un usuario son los siguientes:

*   **Superusuario**: Tiene acceso a toda la plataforma, pudiendo administrar cualquier objeto haya sido creado por el o por otros usuarios. También puede administrar usuarios y grupos.

*   **Gestión**: Los usuarios que implementan el rol de gestión pueden gestionar proyectos, y capas, pero están restringidos a un espacio de trabajo. Este rol no permite la gestión de otros usuarios y grupos.

*   **Básico**: Los usuarios que implementan el rol básico únicamente pueden consultar los proyectos que les han sido asignados por usuarios de rol superior, no pudiendo gestionar capas ni proyectos.

2.3.2 Espacio de trabajo de usuario
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Cuando creamos un nuevo usuario automáticamente se genera la siguiente estructura en la plataforma:

*   Usuario

*   Grupo para el usuario. El grupo se llamará como el usuario precedido del prefijo *ug_*

*   Espacio de trabajo en el servidor de mapas para el usuario

*   Esquema en BBDD y almacén de datos vectorial en el servidor de mapas asociado al esquema, donde el usuario podrá publicar sus capas.

*   Directorio en el sistema de ficheros desde donde el usuario podrá gestionar sus archivos. El directorio se llamará como el usuario precedido del prefijo *ug_*


2.4 Servicios
-------------
gvSIG Online utiliza un servidor de mapas para publicar y acceder a las capas de información geográfica. 
Los servicios de mapas están basados en los estándares del `Open Geospatial Consortium <http://www.opengeospatial.org/>`_ (OGC), 
que permiten que las capas sean interoperables tanto con el visor integrado en gvSIG Online como con otros visores y aplicaciones SIG de escritorio como gvSIG Desktop.

El módulo de servicios permite publicar y gestionar las capas de gvSIG Online.

2.4.1 Espacios de trabajo
~~~~~~~~~~~~~~~~~~~~~~~~~
Los espacios de trabajo son contenedores que se utilizan para organizar elementos diversos como capas y almacenes de datos. 

Los espacios de trabajo se identifican por su nombre, que debe ser único, y permiten agrupar capas y almacenes de datos similares.

2.4.2 Almacenes de datos
~~~~~~~~~~~~~~~~~~~~~~~~
Los almacenes de datos definen conexiones a fuentes de datos ráster o vectoriales, como bases de datos PostGIS, 
carpetas de ficheros SHP o ficheros ráster individuales.

Los almacenes de datos vectoriales permiten definir los parámetros de conexión una única vez para todas las capas presentes en el almacén.

Por contra, los almacenes de datos ráster definen los parámetros de un fichero ráster individual, que contiene una única capa.

Existen diferentes tipos de almacenes de datos en gvSIG Online:

*   **PostGIS vectorial**: Almacena capas vectoriales en una base de datos PostGIS

*   **GeoTiff**: Capa ráster en formato GeoTiff, que almacena la geo-referenciación de la capa dentro de los metadatos Tiff

*   **WMS en cascada**: Almacena la dirección de un servicio WMS para posteriormente ser publicada las capas que tenga disponibles.

Es importante entender que para poder añadir un almacén de datos, debemos partir de una fuente de datos que exista previamente. 
Por ejemplo, para poder añadir un almacén de datos de tipo PostGIS vectorial, la base de datos espacial debe existir previamente. 
De esta forma, los que estamos haciendo es registrar en gvSIG Online (y en Geoserver) los parámetros de conexión a dicha base de datos. 
De la misma forma, para añadir un almacén de datos de tipo ráster, el fichero ráster debe existir previamente en el servidor
(en este caso estamos registrando en gvSIG Online la ruta a dicho fichero ráster).

2.4.3 Capas
~~~~~~~~~~~
Una capa es un conjunto estructurado de información geográfica y alfanumérica que describe un aspecto de la realidad (parcelas, áreas protegidas, usos del suelo, precipitación, etc).

Existen dos tipos diferenciados de capas: vectoriales y ráster. Las capas vectoriales contienen registros de base de datos, cada uno de los cuales posee una o más geometrías asociadas. Las capas ráster
definen una matriz de valores y se utilizan frecuentemente para representar fenómenos continuos en el espacio tales como temperatura, elevación, precipitación o color (ortofotos). Es habitual utilizar formatos de imagen para almacenar capas ráster.

Dentro de cada uno de estos tipos principales podemos encontrar diferentes tipos más especializados.

2.4.4 Grupos de capas
~~~~~~~~~~~~~~~~~~~~~
Los grupos de capas como su nombre indica se utilizan para agrupar capas por una temática específica. Los grupos de capas nos permiten agilizar la asginación de capas a un proyectos.
Además desde el visor de mapas podremos visualizar el grupo de capas como una única capa, mejorando los tiempos de respuesta en la visualización.

2.4.5 Bloqueos
~~~~~~~~~~~~~~
Cuando una capa está en modo edición automáticamente se bloquea para evitar errores en la escritura de los datos.

Existen dos tipos de bloqueos:

*   **Bloqueos del geoportal**: cuando 

*   **Bloqueos de la aplicación móvil**:


2.4.6 Capas Bases
~~~~~~~~~~~~~~~~~
Son aquellas capas que se usan como cartografía de referencia para anclar o usar (como bien su nombre indica) de base en los proyectos. Se puede hacer uso de distintos tipos de proveedores como OSM, BING (con su API-key), teselas XYZ, servicios WMS y WMTS.

Éstas capas se pueden gestionar previamente por un usuario administrador, una vez definidas se podrán asignar y fijar por defecto a cada uno de los proyectos de forma independiente.
 

2.5 Tipos de datos
------------------
Desde gvsig online, se ofrece la opción de generar datos de tipo dominio (listado de enumeraciones y multiple enumeración) y también permite tener campos de control interno en la edición de capas.


2.5.1 Enumeraciones
~~~~~~~~~~~~~~~~~~~
Las enumeraciones son un tipo especial de entidades que definen dominios de valores. Es posible utilizarlas en la creación de nuevas capas cuando deseemos crear un tipo de campo que contenga un listado de elementos y poder seleccionar un único item de dicho listado.

La nomenclatura usada en la BD para ser reconocida como campo de dominio es: **enm_#_acti**

Donde: 

* *enm* = tipo de dato enumeración.

* *#* = número que asigna el sistema por defecto cuando se crean nuevas listas de enumeraciones.

* *acti* = Las primeras cuatro letras del título de la lista de enumeraciones. Para este ejemplo, el título es: 'Actividad'


2.5.2  Múltiple enumeración
~~~~~~~~~~~~~~~~~~~~~~~~~~~
A diferencia del tipo enumeración, este campo permite seleccionar varios elementos de un conjunto de dominios disponibles en un 'listado de enumeración', esta opción se hace disponible cuando se crea una capa vacía en el sistema, seleccionando éste tipo de dato y posteriormente escogiendo algunos de los listados disponibles en las enumeraciones.

Nomenclatura: **enmm_#_acti**

Donde: 

* *enmm* = tipo de dato múltiple enumeración.

* *#* = número que asigna el sistema por defecto cuando se crean nuevas listas de enumeraciones.

* *acti* = Las primeras cuatro letras del título de la lista de enumeraciones. Para este ejemplo, el título es: 'Actividad'


2.5.3 Campos de control interno
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Estos campos son generados automáticamente cuando se crea una capa vacía desde el sistema, los campos son:

 *  **modified_by**: Es un campo que no permite su edición dentro de la tabla. Cuando se edita y guarda un elemento de la capa (atributos o geometría), este campo '*Modified by*' se rellena automáticamente con el nombre del usuario que estaba autenticado en el sistema. 

 *  **last_modification:** Es otro campo que no permite su edición en la tabla. Cuando se edita y guarda un elemento de la capa (atributos o geometría), este campo '*last_modification*' se rellena automáticamente con la fecha que registra el ordenador o móvil.

.. NOTE::
   Estos tipos de datos también pueden ser añadidos manualmente a la tabla de atributos de cualquier capa por medio de la BD antes de que la capa sea publicada en el sistema.

2.6 Administrador de archivos
-----------------------------
El administrador de archivos nos permite subir ficheros a la plataforma de gvSIG Online, para posteriormente realizar operaciones sobre ellos.

El administrador de archivos gestiona directorios en función de los grupos de usuarios. Por cada grupo de usuarios creado existirá un directorio en el servidor. 
Por tanto a la hora de explorar los directorios, únicamente podremos visualizar aquellos directorios que tengamos asignados por pertenencia al grupo.


2.7 Proyectos
-------------
Podemos definir un proyecto como una unidad de agregación de objetos que mediante una configuración dada, permiten una visualización gráfica.

Un proyecto está formado por los siguientes elementos:

*   Información general: nombre, descripción y logo del proyecto

*   Una vista de mapa (centro y extensión)

*   Capas bases

*   Grupos de usuarios

*   Grupos de capas

Existen 2 tipos de proyectos:

*   **Proyectos de acceso público**: Los datos que son visualizados no poseen ningún tipo de restricción. Pueden ser accedidos de forma anónima por usuarios que no estén registrados en la plataforma.

*   **Proyectos de acceso restringido**: Los datos poseen restricciones de acceso y uso para determinados grupos de usuarios. Solo pueden ser accedidos por usuarios que estén dados de alta en la plataforma.


2.8 Simbología
--------------

2.8.1 Leyendas
~~~~~~~~~~~~~~
Otra de las funcionalidades que ofrece gvSIG Online es la posibilidad de modificar la simbología de las capas y aplicarles distintos tipos de leyenda.

La leyenda nos indicará la forma y los criterios que se emplearán para mostrar los datos en el mapa, para una mejor visualización y comprensión de los datos que se representan en el geoportal a través de las distintas capas.

Las leyendas están formadas por uno o más símbolos. Cada símbolo puede estar formado a su vez por uno o más simbolizadores, lo que nos permitirá crear símbolos de mayor complejidad.

En función del tipo de geometría de la capa (punto, linea o polígono) los simbolizadores pueden ser de los siguientes tipos:

*   Geometría tipo punto(PointSymbolizer): Marcadores vectoriales(Mark) o imágenes(ExternalGraphic).

*   Geometría de tipo línea(LineSymbolizer): Simbolizador vectorial.

*   Geometría de tipo polígono(PolygonSymbolizer): Simbolizador vectorial.

Además de los símbolos vectoriales también se podrán definir símbolos para capas raster (RasterSymbolizer) y simbolizadores que definen texto o etiquetas (TextSymbolizer).

Existen diversos tipos de leyenda en función de si el tipo de capa es vectorial o ráster.

Los tipos de leyenda para las capas vectoriales son:

*	*Leyenda de símbolo único*

*	*Leyenda de valores únicos*

*	*Leyenda de intervalos*

*	*Leyenda de expresiones*

Para las capas de tipo ráster existe un tipo de leyenda que es el *Tabla de color*.


2.8.2 Bibliotecas de símbolos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Las bibliotecas de símbolos nos permiten crear y agrupar símbolos genéricos que posteriormente podremos *"importar"* desde las leyendas de capa.
Además podremos *"exportar"* las librerías de símbolos para poder compartir o hacer copias de las mismas. 


2.9 Plugins
-----------
Los plugins se consideran componentes o aplicaciones desarrolladas de forma independientes al sistemas básico. Por lo tanto, son complementos extras que pueden añadirse al sistema. Cada plugin es desarrolado para abarcar funcionalidades específicas según las necesidades de cada cliente.

Esta entrada será visible en el panel de control si se disponen de aplicaciones, por ejemplo: el Geocoding (aplicación para la búsqueda por direcciones), Worldwind (configurador de MDT para 3D), transformaciones, entre otros.


