3. Tipos de datos
=================

3.1 Crear, modificar y eliminar listas de enumeraciones
-------------------------------------------------------
Puede añadir(**1**), actualizar(**2**) y eliminar(**3**) ingresando al menú principal, en la entrada de *Tipos de datos* - *'enumeraciones'*.

.. image:: ../images/enum1.png
   :align: center

Desde el formulario de enumeraciones podremos añadir o eliminar los items que forman parte del listado de enumeración.

.. image:: ../images/enum2.png
   :align: center
   
Por ejemplo, un listado de enumeración que represente los distintos riesgos que pueden existir en un incendio:
 
- título: 'Riesgos de incendios' 
- nombre: asignado por defecto en el sistema, ejemplo: *enm_1*
- Items: 

    * muy bajo, 
    * bajo 
    * medio
    * alto 
    * muy alto
    
- Al dar guardar, el nombre final del listado sera: *enm_1_ries*

.. NOTE::
   Este listado puede ser usado tanto para el tipo de dato 'enumeración' como 'multiple enumeración'. 
   En caso de que se elija el tipo de dato 'múltiple enumeración' la base de datos convierte automáticamente la nomenclatura del campo por: *enmm_1_ries*
   
   
3.2 Asignar tipo de dato 'enumeración' a una tabla
--------------------------------------------------
Existen dos opciones: desde una capa vacía creada en el sistema o añadiendo el campo a la tabla de atributos desde la Base de Datos.


3.2.1 Desde 'crear capa vacía' en el sistema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
en la sección de 'añadir campos',  seleccionamos:

* Seleccionar tipo: 'enumeracion'
* Seleccionar enumeración: escoger el listado que se quiera. 

.. image:: ../images/enum3.png
   :align: center

Cuando la capa se haya publicado en un proyecto y se inicie su edición, en este campo se desplegará el listado con los items y se podrá seleccionar uno de ellos para asignarlo como atributo de un elemneto del mapa.

Por ejemplo: 
 
.. image:: ../images/enum4.png
   :align: center
   
   
3.2.2 Añadiendo el tipo de dato en nuevos campos desde la Base de datos.
------------------------------------------------------------------------
   
    FAAAAAAAAAAAAAAALTAAAAAA
    
Para ello se deben crear los nuevos campos con el nombre exactamente igual al nombre de su nomenclatura y fijarle tipo de dato 'chararter_varyin'.