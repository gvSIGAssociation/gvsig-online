Libra
=====

1. Introducción
---------------
Libra es la interfas gráfica que se conecta directamente con AGRORED para poder asignar mediante la captura gráfica los croquis o geometrías que corresponden a cada una de las Líneas de declaración gráfica que refieren a una solicitud del pago único. 


1.1 Ojteivo
___________

Este manual tiene como objetivo describir el manejo y funcionamiento de las herramientas para la captura gráfica de solicitudes definidas en AGRORED


1.2. Glosario de términos y acrónimos
_____________________________________

* SIGPAC: Sistema de Información Geográfico de Parcelas Agrícolas

* AGRORED: 

* LIBRA:

* PAC:

* PU: Pago Único

* LDG: Línea de Declaración Gráfica



*  **AGRORED:** Aplicación de captura de solicitudes del pago único (PU) de la PAC.

*  **Recinto SIGPAC**:  superficie contínua de terreno, dentro de una parcela, con un mismo uso agrícola estable (tierra arable, pastos, viñedos, olivar, etc.)

*  **Cultivo:**   superficie continua de terreno, dentro de un recinto, por la que se solicita el pago único. 

*  **Solicitud de AGRORED:** cada una de las solicitudes que realiza una persona física o jurídica a través de AGRORED. En una solicitud se definen varios recintos SIGPAC que a su vez contienen uno o varios cultivos.

*  **Línea de Declaración Gráfica:** Cada una de las superficies continuas de terreno que se declaran con el mismo cultivo principal (y secundario si procede) sobre un recinto SIGPAC.

*  **Geometría:** Representación gráfica de la superficie declarada. Es un atributo de las líneas de declaración gráficas.

*  **Editor gráfico:** Conjunto de herramientas para la definición de las geometrías asociadas a las LDGs.

*  **Tabla de registros (Tabla de atributos o grid alfanumérico):** tabla que muestra la información alfanumérica de cada LDG y que se corresponde con cada uno de los cultivos definidos en una solicitud de AGRORED.


2. Descripción del editor gráfico
---------------------------------

El editor gráfico permite editar, actualizar y añadir nueva geometría asociada a una LDG.


2.1 Vista General del editor gráfico
____________________________________

La vista general es el área de trabajo desde donde se realizará la edición gráfica de las geometrías para cada solicitud única.

.. image:: ../_static/images/libra_online_1.png
   :align: center

.. list-table:: Vista general del editor gráfico 
   :widths: 2 10 
   :header-rows: 1
   :align: left

   * - Opción
     - Descripción
   * - 1
     - Barra de menú principal
   * - 2
     - Panel de contenido
   * - 3
     - Área del mapa
     
     
2.2 Barra de menú principal
___________________________

.. image:: ../_static/images/libra_online_2.png
   :align: center

.. list-table:: Descripción de la barra del menú principal
   :widths: 2 10 
   :header-rows: 1
   :align: left

   * - Opción
     - Descripción
   * - 1
     - Botón para mostrar/ocultar el panel de contenidos
   * - 2
     - Logo del sistema (se puede personalizar según lo solicite el cliente)
   * - 3
     - Menú del usuario (únicamente para administradores del sistema)
      
       **3.1**: Nombre y correo del usuario conectado
       
       **3.2**: Idioma
       
       **3.3**: Opción para ir a la vista principal de administrador
       
   * - 4
     - Cerrar sesión para el usuario conectado.      

  
2.3 Detalles del panel de contenido
___________________________________
 
El panel de contenido se compone de distintas pestañas que contienen el árbol de capas (TOC), la leyenda/simbología de capas, detalles de la información de los elementos seleccionados y las herramientas del editor gráfico.
 
2.3.1  Pestaña: 'árbol de capas'
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: ../_static/images/libra_online_3.png
   :align: center

.. list-table:: Panel de contenido - Árbol de capas
   :widths: 2 10 
   :header-rows: 1
   :align: left

   * - Opción
     - Descripción
   * - 1
     - Pestaña: árbol de capas
   * - 1.1
     - Capas bases que son configuradas desde el panel de administrador.
     
       En este caso se encuentra una única capa activa y por defecto. 
       La capa activa es del Plan Nacional de Ortofotografía Aérea (PNOA) 
       obtenida del Centro Nacional de Información Geográfica (CNIG).
   * - 1.2
     - Grupo de capas que puede contener muchas capas, en este caso el grupo 
       solo tiene una única capa. También se configura desde el Panel de administrador del sistema
   * - **1.2.a**
     - Capa publicada desde el panel de administrador, en este caso para el editor gráfico basta 
       disponer de la capa vectorial que contiene todas las geometrías de los recintos.
   * - **1.2.b**
     - Propiedades propias para cada capa:
     
       - **Metadatos:** Resumen de la información de la capa (se configura cuando se publica la capa desde el panel de administrador)
       
       - **Zoom a la capa:** realiza y muestra el zoom general de todas las geometrías que contiene la  capa sobre el mapa.
       
       - **Cambiar el estilo de la simbología**: esto si se han definido previamente mas de un estilo  desde el panel de administrador.
      
       - **Opacidad**: se puede ir configurando el porcentaje de opacidad como desee y necesite el usuario para el análisis entre varias capas.
     