ETL - Plugin de transformación de datos
=======================================

1. Introducción
---------------

*ETL* (acrónimo de los términos en inglés *Extract, Transform and Load*) es una herramienta que permite exportar la información contenida en un fichero plano de  datos (Excel o CSV) a una tabla en la base de datos para luego poder operar con ella.

La ventaja de esta herramienta es que permite georrefenciar los registros de cada tabla, siempre y cuando exista un campo con el valor de las coordenadas o bien la dirección para poder posicionarlo mediante el geocodificador inverso, es decir, por medio del buscador de direcciones, que en este caso se usará la fuente de datos del servidor de OpenStreetMap (OSM).


2. Requisitos para realizar las transformaciones
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
2.1. Tener disponible los datos en un fichero plano, en formatos de hoja de cálculo (**.xlsx**) o texto (**.csv**).

2.2. Crear una **capa vacía** en el sistema con los campos a donde se volcará la información de los ficheros planos.

2.3. Crear la plantilla de transformación.

2.4. Aplicar la transformación sobre el fichero plano.


3. Requisitos básicos en la estructura de los ficheros planos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Algunos requisitos mínimos se deben cumplir para que el proceso de transformación se realice de forma correcta. Los formatos deben ser los citados anteriormente y por otro lado asegurarse que las coordenadas contenidas en los ficheros sean estándar y uniforme, de esta manera se garantiza que la transformación sea exitosa al momento de posicionar cada elemento.

3.1. **Transformación con dirección**: El campo que contenga la dirección del elemento, preferiblemente que sea lo mas similiar posible a la dirección que ofrece la cartografía base del OSM.

3.2. **Transformación con coordenadas para formato (.xlxs)**: las coordenadas comunmente están en celdas separadas, deberán estar expresadas en grados decimales, donde la parte entera se separa de los minutos y segundos por (,), por ejemplo: (-31,4459068688) (-64,233981896). 

.. note::
   - El sistema no soporta comillas simples, ni dobles al final de la coordenadas, ejemplo: (-31,4354382939') (-64,2393822877').
   
   - Tampoco será válido coordenadas no bien definidas como los siguientes ejemplos: (-313.937.747)  (-6.417.356.619.999.990).
   
3.3. **Transformación con coordenadas para formato (.csv)**: las coordenadas normalmente estarán en una misma celda, por lo tanto, igual estarán expresadas en grados decimales, pero esta vez la parte entera se separa de los minutos y segundos por un (.) ya que la (,) es usada para separar entre latitud y longitud o viceversa. También se acepta que estén o no dentro de paréntesis. Ejemplo: (-31.4315574, -64.18822169999998) 


4.Pasos para transformar
~~~~~~~~~~~~~~~~~~~~~~~~
4.1. **Crear capa vacía**: Se crea la capa vacía en el sistema y se añaden tantos campos como tenga el fichero plano o los que se quiera volcar información.

.. note::
   - Cuando se crea una capa vacía en el sistema se añaden por defecto los campos: 'gid' y 'wkb_geometry', el primero es interno para hacer un identificador único en la tabla de Base de Datos (BD), éste no será usado en la transformación, el segundo es el campo donde se registrará la geometría de cada elemento y será el que se use para volcar las coordenadas.
   
   - También se añaden los campos 'last_modification' y 'by_modified', tampoco se usarán en la transformación. Son campos usados como control en la edición de la capa online desde el geoportal.

Una vez se haya publicado la capa vacía sin registros, se procede a crear la plantilla de transformación para fijar la configuración entre la capa vacía y el fichero plano.

4.2. **Crear plantilla de transformación (formato .xlsx)** Para acceder a esta funcionalidad se debe ingresar en el panel de control:


.. image:: ../_static/images/etl1.png
   :align: center


.. list-table:: Crear plantilla de transformación
   :widths: 2 20 50
   :header-rows: 1

   * - Pasos
     - Selección
     - Acción
   * - 1
     - En Panel de control, entrada: Geocoding 
     - Muestra todos los plugins disponibles
   * - 2
     - Seleccionar el plugin 'transformaciones'
     - Mostrará la ventana del listado de transformaciones
   * - 3
     - Clic sobre 'añadir'
     - Saldrá una nueva vista para configurar la plantilla de transformación

4.3 **Configuración de plantilla de transformación (formato xlsx)**: EL primer paso es añadir un nombre a la transformación y seleccionar cuál será la capa en el BD donde se volcarań los datos. 

.. image:: ../_static/images/etl2.png
   :align: center

.. list-table:: Nombre de transformación y seleccionar capa 
   :widths: 2 20 50
   :header-rows: 1

   * - Pasos
     - Selección
     - Acción
   * - 1
     - Añadir un nombre a la plantilla de transformación (sin caracteres especiales, ni espacios en blanco)
     - Será el nombre que identifique a la plantilla 
   * - 2
     - Seleccionar el Espacio de trabajo
     - Es el espacio donde se encuentra el almacén de datos a usar.
   * - 3
     - Seleccionar el almacén de datos
     - En éste almacén de datos se ubica la capa vacía
   * - 4
     - Buscar la capa y seleccionarla
     - Es la capa vacía que se ha creado previemente y donde se volcarán los datos del fichero plano.
   * - 5
     - Clic en continuar
     - Me lleva a una siguiente vista para configurar y corresponder cada una de las hojas, campos y celdas de la transformación a un registro de la tabla en la bd.  


.. image:: ../_static/images/etl3.png
   :align: center

.. list-table:: Configuración para ficheros planos (formato xlxs) 
   :widths: 2 20 50
   :header-rows: 1

   * - Pasos
     - Selección
     - Acción
   * - 1
     - Pasos previos
     - Ya debe estar seleccionada la capa y el nombre de la transformación
   * - 2
     - Escoger la opción 'excel'
     - Se muestra sus propias opciones de hojas 
   * - 3
     - Recuadro de 'seleccionar hoja' 
     - Al pinchar sobre los tres puntos se abrirá una nueva ventana de configuración de hojas
   * - 3.1
     - todas las hojas
     - Volcará en la tabla vacia todos los datos que existan en todas las hojas del fichero excel
   * - 3.2
     - Solo la hoja
     - Escribir el nombre de la hoja que se desea usar, permite solo una hoja.
   * - 3.3
     - Opción desde y hasta
     - Si existen muchas hojas en el fichero plano, se puede indicar un rango de hojas, considera la primera hoja como la número (1) y así sucesivamente. Ejemplo, si hay diez hojas y se quiere usar desde la segunda a la quinta, se indicaría: desde 2 hasta 5.
   * - 3.4
     - opción 'que cumpla'
     - Añade expresiones regulares que cumplan ciertas condiciones. Ejemplo, si existen varias hojas llamadas desde hoja_1 a hoja_8,y otras con nombres diferentes pero se quiere solo las llamadas hojas, la expresión será: hoja_*
   * - 4
     - Seleccionar desde la fila y desde la columna
     - El sistema tomará los datos desde el número de fila y columna indicado del fichero plano. No siempre los datos comienzan en la fila y columna 1, ya que siempre hay encanezados y entre otros.
   * - 5
     - Área para defiir las reglas
     - Desde el botón 'añadir nueva regla', saldrá un nuevo recuadro para ir configurando los campos de la tabla con respecto a las columnas del fichero plano. 
   * - 5.1
     - Campo de la BD a rellenar
     - apareceran todos los campos disponibles de la capa a los cuales se van a volcar los datos del fichero plano.
   * - 5.1.a
     - Campos de la capa en la BD
     - Al hacer clic sobre la casilla se debe mostrar todos los campos incluyendo el 'gid' y el 'wkb_geometry', se selecciona uno de ellos.
   * - 5.2 
     - Rellenar con
     - Ésta opción muestra las distintas formas en que se puede volcar los datos desde el fichero plano al campo de la BD seleccionado.
   * - 5.2.a
     - opciones para rellenar
     - entre las distintas formas que hay, las más usadas son 'valor de columna' y 'campos de geometrías desde campo lat/lon'. Se explicará a detalle en el siguiente item.
   * - 5.3
     - distintas opciones a elegir
     - Dependiendo de la opción seleccionada en el 5.2.a, se muestra diferetes opciones. Por ejemplo, si se elije 'valor fijo', saldrá otra casilla 'Valor fijo' y se añade un valor escrito por el usuario. Ésta opción rellenará el campo seleccionado con este valor para todos sus registros, como su nombre lo indica es un 'Valor que está fijado'
   * - 6
     - aceptar
     - Se guarda la regla y se pueden definir tantas reglas como campos disponibles hayan en la capa de BD. Para continuar añadiendo reglas se repite todo el proceso del paso (5).
   * - 7
     - Guardar
     - Se guarda los cambios cuando se finalice de añadir todas las reglas. 
     



5.Las plantillas de transformaciones
------------------------------------

A través de las transformaciones se definirán cómo rellenar cada uno de los campos de la base de datos destino utilizando la información extraída de cada una de las filas del fichero origen (xlsx o csv)

Las transformaciones aparecen listadas, pudiéndose añadir más, editar las existentes o borrarlas.


**Crear una transformación**: Sólo requiere del nombre de la transformación para su genereación. Luego se pueden definir todos los pasos a seguir para exportar los datos desde la pantalla de edición.

*Borrar transformación*: Elimina la transformación, así como todas sus reglas (pasos a seguir) para rellenar los campos de la base de datos.

*Actualizar transformación*: Permite definir la secuencia de pasos a seguir. En él se definen las reglas (pasos), de la siguiente manera:

- Primero da la opción de indicar un ejemplo de base de datos de destino. Aunque es opcional, si se pone rellenará parte del formulario facilitando la faena posterior (por ejemplo, aparecerá el listado de campos dispoibles, evitando los errores ocasionados al tecleaarlos a mano)

- Luego se define el origen de datos, escogiendo la pestaña correspondiente (Excel o CSV)

- Según la opción especificada, se elegirán los parámetros necesarios para configurarla:

  - Excel:
    
    - Se eligen las hojas del excel sobre las que se hará la transformación. Puede escogerse la opción de 'todas', 'desde...hasta...', 'con el nombre...' o 'que cumplan esta condición...' (expresión regular)
    
    - Luego se define la fila a partir de la cual empezar a tomar los datos (por si hay cabeceras o filas a ignorar)
   
  - CSV:
    
    - Se define el caracter que actúa de separador de campos (aparecen algunos, pero se puede definir uno propio)
    
    - Se especifica la codificación del fichero
    
    - Luego se define la fila a partir de la cual empezar a tomar los datos (por si hay cabeceras o filas a ignorar)
     
- Por último, se establecerán las reglas de transformación. Estas reglas requieren del campo de la tabla de la base de datos donde se va almacenar la información (campo destino), y de cómo se va a rellenar, pudiéndose elegir entre estas opciones:
  
  - Con un *texto fijo* (valores constantes)
  
  - Con el *valor de una columna*. a partir de la fila indicada anteriormente, rellenara con el valor de esa columna. Se ha de indicar el número de columna (empezando por 0 para la primera)
  
  - *Valor calculado*, permite meter código python directamente para definir el valor del campo de forma compleja. Ejemplos existen todos los que se puedan ocurrir, pero por ejemplo marcamos dos:
  
    - self.createGeometry('Multipoint',4326,6,7) -> Función propia que rellena el campo con una geometría (en este caso multipunto), con un SRID (4326), y la longitud/latitud que están en las columnas 6 y 7 respectivamente (en este caso).
    
    - self.getValueOfColumn(0)+'-'+self.getValueOfColumn(1) -> Introduce en el campo destino los valores de la primera y segunda columna separados por un guión. self.getValueOfColumn(X) es una función propia que devuelve el valor para la columna X de la fila actual
    
    - now() -> Función general ed python que devuelve la fecha y hora actual
    
    - Y todas las que se puedan ocurrir....
      


6. Realizar transformaciones
----------------------------

Una vez definida la transformación, se va al directorio de ficheros a buscar el origen de los datos (Ficheros excel o CSV). Y sobre el botón de herramientas se elige la opción *Transformas*

Luego bastará con elegir la transformación a aplicar, la tabla de la BD destino y si se quiere que el resultado se añada al contenido que ya hay en la tabla, o que se borre y se rellene sólo con los datos del fichero.


    
   