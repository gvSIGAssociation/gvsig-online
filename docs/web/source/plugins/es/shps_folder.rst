Cargador de carpetas Shape
==========================

Introducción
------------

*ETL* (acrónimo de los términos en inglés *Extract, Transform and Load*) es una herramienta que permite exportar la información contenida en un fichero plano de  datos (Excel o CSV) a una tabla en la base de datos para luego poder operar con ella.

Para acceder a esta funcionalidad, se dispone de una entrada en el menú lateral *Servicios*, subsección *Transformaciones*



Las plantillas de transformaciones
----------------------------------

A través de las transformaciones se definirán cómo rellenar cada uno de los campos de la base de datos destino utilizando la información extraída de cada una de las filas del fichero origen (xlsx o csv)

Las transformaciones aparecen listadas, pudiéndose añadir más, editar las existentes o borrarlas.


*Crear una transformación*: Sólo requiere del nombre de la transformación para su genereación. Luego se pueden definir todos los pasos a seguir para exportar los datos desde la pantalla de edición.

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
      


Realizar transformaciones
-------------------------

Una vez definida la transformación, se va al directorio de ficheros a buscar el origen de los datos (Ficheros excel o CSV). Y sobre el botón de herramientas se elige la opción *Transformas*

Luego bastará con elegir la transformación a aplicar, la tabla de la BD destino y si se quiere que el resultado se añada al contenido que ya hay en la tabla, o que se borre y se rellene sólo con los datos del fichero.


    
   