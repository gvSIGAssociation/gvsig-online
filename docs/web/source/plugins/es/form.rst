Plugin de encuestas
===================

1. Introducción
---------------

Este plugin tiene como objetivo vincular Features (alguna geometría) de nuestras capas vectoriales con encuestas realizadas a través de la plataforma LimeSurvey. 
De esta forma, se puede ligar la encuesta a una feature del mapa para posteriores estudios que puedan ser necesarios.

La plataforma LimeSurvey es independiente del gvsigonline y la conexión entre ambas plataformas es realizado por el administrador del sistema.

Según wikipedia:"LimeSurvey (anteriormente PHPSurveyor) es una aplicación open source para la aplicación de encuestas en línea, escrita en PHP y que utiliza bases de datos MySQL, PostgreSQL o MSSQL. Esta utilidad brinda la posibilidad a usuarios sin conocimientos de programación el desarrollo, publicación y recolección de respuestas de sus encuestas.

Las encuestas incluyen ramificación a partir de condiciones, plantillas y diseño personalizado usando un sistema de plantillas web, y provee utilidades básicas de análisis estadístico para el tratamiento de los resultados obtenidos. Las encuestas pueden tener tanto un acceso público como un acceso controlado estrictamente por las claves que pueden ser utilizadas una sola vez (tokens) asignadas a cada persona que participa en la encuesta. Además los resultados pueden ser anónimos, separando los datos de los participantes de los datos que proporcionan, inclusive en encuestas controladas"


2. Requisitos para vincular encuestas a las features de una capa
----------------------------------------------------------------
* 2.1 Crear mínimo una encuesta en la plataforma Limesurvey

* 2.2 Registrar encuesta en gvsigonline

* 2.3 vincular la encuesta a una capa de gvsigonline


2.1 Crear una encuesta en la plataforma Limesurvey
__________________________________________________

Para crear una encuesta se necesita:

* 2.1.1 Acceder con usuario y clave a la paltaforma de Limesurvey
* 2.1.2 Dar de alta una encuesta (configuraciones básicas)
* 2.1.3 Activar encuesta

2.1.1 Acceder con usuario y clave a la paltaforma de Limesurvey
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Se ingresa a la plataforma limesurvey a través de la url del gvsigonline con la extensión a ésta plataforma. Las url dependen de la configuración de cada cliente.

.. image:: ../_static/images/form1.png
   :align: center

.. list-table:: Autenticarse en Limesurvey 
   :widths: 2 10 
   :header-rows: 1
   :align: left

   * - selección
     - Acción
   * - 1
     - Usuario que tendrá privilegios para crear/editar encuestas
   * - 2
     - Ingresar clave
   * - 3 
     - La plataforma permitir seleccionar distintos idiomas
   * - 4
     - Nos lleva al entorno principal de la plataforma. Se describen los apartados relevantes
   * - 5 
     - Si es primera vez, se configuran las opciones generales que se aplican a todo el entorno y sobre todas las encuestas.
   * - 6
     - Entrada para dar de alta una encuesta nueva. También se puede desde la barra de menú superior
   * - 7 
     - Entrada que muestra enlistada las ecuestas que estan activas o no para poder usarse.       

.. note::
   En este manual no se hará detalles del manejo específico de la plataforma (limesurvey). Se indicará los items más relevantes y necesarios para que interactue con el gvsigonline. 


En esta interfaz se pueden añadir las encuestas(por bloques, preguntas, condiciones entre ellas, etc), exportarlas, guardar, editarlas, manejar la seguridad, entre otros. Se recomienda al usuario revisar el Manual_ propio de la interfaz Limesurvey.

 .. _Manual: http://manual.limesurvey.org/


2.1.2 Dar de alta una encuesta (configuraciones básicas)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Es Importante tener presente que ciertas configuraciones se personalizan según los requerimientos o necesidades de cada cliente.  La configuración de algunos parámetros principales se describen a continuación.

 
.. image:: ../_static/images/form2.png
   :align: center  

.. list-table:: Configuración básica para dar de alta encuesta 
   :widths: 2 15 
   :header-rows: 1
   :align: left

   * - Vista
     - Opciones activadas
   * - 1
     - Entrada principal donde se describe la información relacionada a la encuesta:
     
       * Seleccionar el idioma
       * El Título (nombre de la encuesta)
       * La descripción 
       * Algún mensaje de bievenida (opcional)
       * Algún mensaje de despedida (opcional) 
   * - 2
     - Entradas secundarias desplegables donde se ajustan las configuraciones por sección.
   * - 2.1
     - Sección: 'Opciones Generales', ACTIVAR:
     
       * pregunta por pregunta
       * Las demás opciones están por defecto según la configuración del administrador.
   * - 2.2
     - Sección: 'Presentación y navegación', ACTIVAR:
     
       * Mostrar pantalla de bienvenida
       * Mostrar pantalla de bienvenida
       * Mostrar barra de progreso (opcional)
       * Cargar URL automáticamente cuando finalice la encuesta (opcional)
       * Cargar URL automáticamente cuando finalice la encuesta (opcional)
       * Mostrar el nombre de la sección y/o la descripción: 'Mostrar solo el nombre de la sección (opcional)'
       * Mostrar el número y/o el código de la pregunta: 'Ocultar ambos'
       * Demás opciones desactivados o se activan según se requiera.
   * - 2.3
     - Sección: 'Control de publicación y acceso', ACTIVAR: 
     
       * Mostrar al público la encuesta
       * Fecha y hora de inici y expiración (cuando la fecha expire la encuesta estará desativada para usar)
       * Demás opciones desactivadas (se pueden activar según lo requiera el administrador)
   * - 2.4
     - Sección: 'Administración de la notificación y de los datos', ACTIVAR:
     
       * Sello de tiempo
       * Guardar la dirección IP
       * Guardar la URL de origen (referrer URL)
       * Guardar mediciones de tiempo
       * Habilitar modo evaluación
       * Los participantes pueden guardar y continuar más tarde
       * Demás opciones desactivadas (se pueden activar según lo requiera el administrador)    
   * - 2.5
     - Sección: 'Encuestados/as', ACTIVAR:
     
       * Activar persistencia de la respuesta para la misma contraseña
       * Permitir múltiples respuestas o actualizar la existente para la misma contraseña
       * Utilizar formato HTML para los correos a los usuarios restringidos
       * Enviar correos electrónicos de confirmación
       * Respuestas anonimizadas (DESACTIVADO)
       * Permitir registro público (DESACTIVADO)

Finalizado las configuraciones generales se van añadiendo las secciones de grupos de preguntas y dentro de ellos cada una de las preguntas.

.. image:: ../_static/images/survey_grupo_secciones.png
   :align: center


Para cada grupo se puede definir el orden de las preguntas y éstas últimas se pueden presentar de distintos formatos, añadir condiciones entre las distintas preguntas, configuraciones generales y avanzadas de forma independiente.

.. image:: ../_static/images/survey_conf_gr_preguntas.png
   :align: center


2.1.3 Activar encuesta
~~~~~~~~~~~~~~~~~~~~~~

Una vez configuradas las preguntas de la encuesta, se debe activar la encuesta para poder ser usada. 

Dependiendo de las necesidades del cliente, se podrá activar la encuesta de forma anónima o no. En este caso se describe la opción de generar una lista de participantes, es decir, que no sea anónima. 

Es importante prestar atención a las especificaciones de cómo funcionará las distintas opciones a escoger, Limesurvey lo irá mostrando de forma sencilla y bastatnte clara. Por ejemplo, cuando se procede activar la encuesta muestra los siguientes mensajes:

"
.. note::
   Debe activar una encuesta sólo cuando esté absolutamente seguro(a) de que la configuración de la misma es correcta y que no habrá más cambios. 
 
   Una vez activada la encuesta no se le permitirá:

    * Agregar o eliminar secciones de la encuesta
    
    * Agregar o eliminar pregunta
    
    * Agregar o eliminar subpregunta, o cambiar sus códigos


   ... Por favor, tenga en cuenta que, una vez que las respuestas de esta encuesta se han recogido, si quiere añadir o eliminar grupos/preguntas o cambiar uno de los ajustes anteriores, necesitará desactivar esta encuesta; esto provocará que todos los datos que fueron ya introducidos sean movidos a una tabla de diferente para su archivo.
   
"   

.. image:: ../_static/images/encuesta_activar_1_.png
   :align: center

.. image:: ../_static/images/encuesta_activar_2_.png
   :align: center

.. list-table:: Activar encuesta 
   :widths: 2 10 
   :header-rows: 1
   :align: left

   * - Opción
     - Acción
   * - 1
     - Entrada 'Encuestas': muestra todo el listado de las encuestas que existen.
   * - 2
     - Estado de las encuestas, indican cuales son los activas o no. Se hace clic 
       
       sobre la que no está activa y nos lleva a otra ventana
   * - 3
     - Al hacer clic sobre 'activar encuesta' nos lleva a otras opciones a seleccionar    
   * - 4
     - Son las distitas opciones de la encuesta en general:
     
       * Previsualizar la encuesta, ver como la visualizan los usuarios
       * Propiedades de la encuesta (configuaraciones)
       * Herramienstas
       * Mostrar/exportar 
       * Participantes de la encuesta
   * - 5
     - Seleccionar, **Respuestas Anónimas : NO** las demás opciones pueden ser 'SI' u opcionales.     
   * - 6
     - Salvar y activar encuestas. Como no Son anónimas las respuestas se continúa configurando
   * - 7
     - Cambiar a encuesta de acceso restringido (leer las condiciones que se activan)
   * - 8
     - Inicializar tabla de participantes
   * - 9
     - Al dar a 'continuar', la encuesta estará activa para poder realizarla             
      




2.2 Registrar encuesta en gvSIG Online
______________________________________

Una vez se tiene completa la definición de la encuesta en el sistema LimeSurvey, se procederá a registrarla en gvSIGOnline. 

En la entreda de menú correspondiente, dentro de *Tipo de datos*, encontramos el listado de formularios dados de alta en la plataforma. Como siempre, podemos añadir, editar y borrar.
Para insertar uno nuevo se necesitan los siguientes parámetros:

* *Nombre:* generado automáticamente para luego hacer referencia a ella

* *Descripción:* Comentarios sobre la encuesta

* *Url:* Dirección web al API-rest del servicio LimeSurvey (suele ser la dirección al servicio al que se añade '/admin/remotecontrol'). P.ej: https://<url_limesurvey>/limesurvey/index.php/admin/remotecontrol 

* *Nombre de usuario:* usuario para acceder al LimeSurvey

* *Contraseña:* password asociada a la cuenta de usuario

Una vez rellenos estos datos, a través del botón 'Recargar' se pueden obtener las encuestas disponibles

* *Identificador de la encuesta:* elegir la encuesta entre las disponibles
 

2.3 vincular la encuesta a una capa de gvsigonline
__________________________________________________

Al crear una capa vacía, aparecerá un nuevo tipo de campo (junto con el de enteros, texto, booleanos, enumeraciones, ...) que será el de formularios (Form)

Al seleccionarlo, habrá que indicar el formulario registrado en el paso anterior al que hacemos referencia y.... ¡listo!
Cuando la capa se publique, se podrán insertar features, modificar y borrar tal y como se ha hecho hasta ahora, con la diferencia que uno de los campos será un botón que nos abrirá una pestaña en el navegador con una nueva instancia de la encuesta y la asociará a esa feature de la capa.



3. Pausar o dar de baja una encuesta desde LimeSurvey
-----------------------------------------------------

* Si se para la encuesta, SIEMPRE hay que elegir la opción 'desactivar' si se va a querer gastar posteriormente (si no, aunque se active, no tendrá vigencia y no se podrá recuperar las respeustas).

* Cuando se activa una encuesta:

  * En el primer panel, poner respuestas anónimas a 'NO', el resto opcional.
  * Pinchar sobre el botón 'Cambiar encuesta a modo restringido'
  * Pinchar sobre el botón 'Iniciar tabla de participantes'

