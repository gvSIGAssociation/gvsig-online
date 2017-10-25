ETL - Plugin de transformación de datos
=======================================

1. Introducción
---------------

*ETL* (acrónimo de los términos en inglés *Extract, Transform and Load*) es una herramienta que permite exportar la información contenida en un fichero plano de  datos (Excel o CSV) a una tabla en la base de datos para luego poder operar con ella.

La ventaja de esta herramienta es que permite georrefenciar los registros de cada tabla, siempre y cuando exista un campo con el valor de las coordenadas o bien la dirección para poder posicionarlo mediante el geocodificador inverso, es decir, por medio del buscador de direcciones, que en este caso se usará la fuente de datos del servidor de OpenStreetMap (OSM).


2. Requisitos para realizar las transformaciones
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
2.1. Tener disponible los datos en un fichero plano, en formatos de hoja de cálculo (**.xlsx**) o texto (**.csv**)
2.2. Crear una **capa vacía** en el sistema con los campos a donde se volcará la información de los ficheros planos.
2.3. Crear la plantilla de transformación
2.4. Aplicar la transformación sobre el fichero plano.


3. Requisitos básicos en la estructura de los ficheros planos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Algunos requisitos mínimos se deben cumplir para que el proceso de transformación se realice de forma correcta. Los formatos deben ser los citados anteriormente y por otro lado asegurarse que las coordendas contenidas en los ficheros sean estándar y uniforme. De esta manera se garantiza que la transformación sea exitosa al momento de posicionar cada elemento.

3.1. **Transformación con dirección**: El campo que contenga la dirección del elemento, preferiblemente que sea lo mas similiar posible a la dirección que ofrece la cartografía base del OSM.
3.2. **Transformación con coordenadas para formato (.xlxs)**: las coordenadas comunmente están en celdas separadas, deberán estar expresadas en grados decimales, donde la parte entera se separa de los minutos y segundos por (,), por ejemplo: (-31,4459068688) (-64,233981896). 

.. note::
   El sistema no soporta comillas simples, ni dobles al final de la coordenadas, ejemplo: (-31,4354382939') (-64,2393822877'), tampoco será válido coordenadas no bien definidas como ésto: (-313.937.747)  (-6.417.356.619.999.990).
   
3.3. **Transformación con coordenadas para formato (.csv)**: las cordenadas normalmente estarán en una misma celda, por lo tanto, igual estarán expresadas en grados decimales, pero esta vez la parte entera se separa de los minutos y segundos por (.) ya que la (,) es usada para separar entre latitud y longitud o viceversa. También se acepta que estén o no dentro de paréntesis. Ejemplo: (-31.4315574, -64.18822169999998) 


4.Pasos para transformar
~~~~~~~~~~~~~~~~~~~~~~~~
4.1. **Crear capa vacía**: Se crea la capa vacía en el sistema y se añaden tantos campos como tenga el fichero plano o los que se quiera volcar información.

.. note::
   - Cuando se crea una capa vacía en el sistema se añaden por defecto los campos: 'gid' y 'wkb_geometry', el primero es interno para hacer un identificador único en la tabla de Base de Datos (BD) no será usado en la transformación, el segundo es el campo donde se registrará la geometría de cada elemento y será el que se use para volcar las coordenadas.
   
   - También se añaden los campos 'last_modification' y 'by_modified', tampoco se usarán en la transformación. Son campos usados como control en la edición de la capa online desde el geoportal.

Una vez se haya publicado la cpa vacía sin registros, se procede a crear la plantilla de transformación para fijar la configuración entre la capa vacía y el fichero plano.

4.2. **Crear plantilla de transformación (formato .xlsx)** Para acceder a esta funcionalidad se debe ingresar en el panel de control:


.. image:: ../images/etl1.png
   :align: center


.. list-table:: Crear transformación
   :widths: 2 30 100
   :header-rows: 1

   * - Pasos
     - Selección
     - Acción
   * - 1
     - En Panel de control, entrada: Geocoding 
     - Muestra todos los plugins disponibles
   * - 2
     - seleccionar el plugin 'transformación'
     - Mostrará la ventana de listado de traasformaciones
   * - 3
     - Clic sobre 'añadir transformación'
     - Saldrá una nueva vista para configurar la plantilla de transformación



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


    
   