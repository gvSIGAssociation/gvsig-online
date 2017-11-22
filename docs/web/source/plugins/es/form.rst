Plugin de encuestas
===================

Introducción
------------

Este plugin tiene como objetivo vincular Features de nuestras capas vectoriales con encuestas realizadas a través de la plataforma LimeSurvey. 
De esta forma, se puede ligar la encuesta a un punto en el mapa para posteriores estudios que puedan ser necesarios.

*NOTA:* Antes de continuar, es necesario tener al menos una encuesta definida en el servidor LimeSurvey. Si se desconoce su funcionamiento, se recomienda remitirse a su manual para comenzar a definirla
(https://manual.limesurvey.org/). Posteriormente, a través de su interfaz, se pueden ir definiendo los bloques, preguntas, pasos entre ellas, etc.

   * Configuración antes publicar
     * Opciones generales -> Pregunta a pregunta
     * Presentación y navegación -> Mostrar bienvenida: Sí
     * Presentación y navegación -> Permitir hacia atrás: Sí
     * Administración de la notificación y de los datos -> Permitir modo evaluación: Sí
     * Administración de la notificación y de los datos -> Permitir guardar y continuar: Sí
     * Encuestados/as -> Activar persistencia de la respuesta para la misma contraseña: Sí
     * Encuestados/as -> Permitir múltiples respuestas o actualizar la existente para la misma contraseña: Sí

   * Configuración al publicar
     * Usuarios anónimos: No
     * Resto opciones: Sí




Dar de alta la encuesta en gvSIG Online
---------------------------------------

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
 

Vincular una encuesta a una capa
--------------------------------

Al crear una capa vacía, aparecerá un nuevo tipo de campo (junto con el de enteros, texto, booleanos, enumeraciones, ...) que será el de formularios (Form)

Al seleccionarlo, habrá que indicar el formulario registrado en el paso anterior al que hacemos referencia y.... ¡listo!
Cuando la capa se publique, se podrán insertar features, modificar y borrar tal y como se ha hecho hasta ahora, con la diferencia que uno de los campos será un botón que nos abrirá una pestaña en el navegador con una nueva instancia de la encuesta y la asociará a esa feature de la capa.



Configuración de LimeSurvey
---------------------------

* Si se para la encuesta, SIEMPRE hay que elegir la opción 'desactivar' si se va a querer gastar posteriormente (si no, aunque se active, no tendrá vigencia y no se podrá recuperar las respeustas).

* Cuando se activa una encuesta:

  * En el primer panel, poner respuestas anónimas a 'NO', el resto opcional.
  * Pinchar sobre el botón 'Cambiar encuesta a modo restringido'
  * Pinchar sobre el botón 'Iniciar tabla de participantes'

