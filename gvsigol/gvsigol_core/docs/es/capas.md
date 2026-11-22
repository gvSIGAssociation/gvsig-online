# Capas

Una **capa** es un conjunto de datos geográficos publicado en el servidor de mapas (GeoServer) y
preparado para verse en los visores: una tabla de PostGIS, un ráster (GeoTIFF o mosaico) o una
capa de un servicio WMS en cascada. Cada capa pertenece a un [grupo de capas](grupos-capas.md), y
es el grupo el que se asigna a los [proyectos](proyectos.md).

Las capas se gestionan desde el panel de administración, en **Servicios** > **Capas**. Las capas de
servicios externos se gestionan aparte (ver [Capas externas](capas-externas.md)), y las capas que
se suben desde un fichero se publican desde el [gestor de archivos](gestor-archivos.md).

## Quién puede hacer qué

| Acción | Quién |
|---|---|
| Ver la lista de capas | Personal (*staff*) y superusuarios. Los superusuarios ven todas; el resto, las que han creado y aquellas en las que alguno de sus roles tiene **Permiso de gestión** |
| Publicar una capa o crear una capa vacía | Personal y superusuarios, siempre que puedan usar el almacén de datos y tengan **Permiso para incluir en proyectos** en el grupo de destino (o sea el grupo **Por defecto**) |
| Modificar, configurar, refrescar, actualizar la vista previa, limpiar la caché o eliminar una capa | Quien la gestiona: los superusuarios, quien la creó y el personal con un rol con **Permiso de gestión** en la capa |
| Cambiar una capa de grupo | Quien gestiona la capa y, además, gestiona el grupo de origen y el de destino |
| Cambiar las reglas topológicas | Solo superusuarios |
| Ver y cambiar la pestaña **Permisos** | Superusuarios siempre; el resto del personal, salvo que la instalación tenga desactivada la gestión de permisos en la interfaz |

## Lista de capas

![Lista de capas con el filtro por proyecto y los botones de cada fila](img/capas-lista.png)

La lista muestra, para cada capa, su identificador, una **Vista previa** (miniatura), el
**Nombre**, el **Título**, el **Almacén de datos**, el **Grupo de capas** y los **Proyectos** en los
que aparece (los que incluyen su grupo). La tabla se pagina.

- **Filtrar por proyecto**: muestra solo las capas de los grupos de ese proyecto. Se ofrecen los
  proyectos que usted gestiona. **Muestra todas las capas** quita el filtro.
- El buscador filtra por nombre y título de la capa, nombre del almacén de datos y nombre o título
  del grupo.
- **Crear capa vacía** y **Publicar capa** abren los formularios descritos más abajo.

### Acciones de cada fila

- **Actualizar capa**: abre el formulario de la capa (ver [Modificar una capa](#modificar-una-capa)).
- **Actualizar vista previa**: vuelve a generar la miniatura de la capa.
- **Refrescar extensión y definición de capa**: vuelve a leer de la base de datos la extensión y la
  lista de campos de la capa. Úselo si la tabla se ha modificado fuera de gvSIG Online (columnas
  nuevas, datos cargados por otra vía).
- **Configurar capa**: configuración de los campos (ver [Configurar los campos](#configurar-los-campos)).
  Solo en capas vectoriales de PostGIS; en las demás avisa de que **Las capas ráster no son
  configurables**.
- **Eliminar capa**: pide confirmación y la borra (ver [Eliminar una capa](#eliminar-una-capa)).

## Publicar una capa

**Publicar capa** convierte en capa algo que ya existe en un almacén de datos: una tabla o vista de
PostGIS, un GeoTIFF, un mosaico o una capa del WMS en cascada. Pulse **Publicar capa** en la lista
de capas o en la pestaña **Capas del grupo** de un grupo.

![Formulario Añadir capa, pestaña General](img/capas-publicar-general.png)

### Pestaña General

- **Almacén de datos**: de dónde vienen los datos. Se ofrecen los almacenes que usted puede usar
  (ver [Servidores](servidores.md)). Si publica desde un grupo, solo los del servidor del grupo.
- **Nombre del recurso**: la tabla o el recurso que se publica. La lista se rellena al elegir el
  almacén y solo incluye lo que aún no está publicado. Si aparece **El almacén de datos no contiene
  recursos para publicar**, todo está ya publicado. En los almacenes ráster solo se puede publicar
  un recurso.
- **Título**: el nombre que ven los usuarios en el visor. Se puede cambiar en cualquier momento.
- **Grupo de capas**: el grupo donde aparecerá la capa. Se ofrecen los grupos del mismo servidor
  que el almacén. Si publica desde un grupo, viene fijado.
- **Formato**: el formato de imagen con que se sirve la capa. Por defecto se ofrecen **image/png**,
  **image/jpeg** y **vector tiles** (teselas vectoriales); esta última solo en capas vectoriales de
  PostGIS.

El almacén de datos y el nombre del recurso **no se pueden cambiar después**. No se pueden publicar
tablas con nombres de campo que contengan espacios.

Las pestañas **Propiedades de visualización**, **Permisos**, **Metadatos** e **Información
detallada** son las mismas que al modificar la capa y se describen más abajo. Al publicar, la capa
está consultable y apagada por defecto, y su rol principal aparece marcado con permiso de lectura
y de gestión.

### Qué ocurre al guardar

- La capa se publica en GeoServer y se añade al grupo, también en la tabla de contenidos de los
  proyectos que incluyen ese grupo.
- Se crea un **estilo por defecto**. En las capas vectoriales, su color sale de una paleta y va
  rotando entre las capas del mismo grupo, para que capas vecinas tengan colores distintos. Si la tabla tiene más de 200.000
  registros, el estilo solo dibuja la capa a escala 1:50.000 o más detallada. Para cambiarlo, ver
  [Simbología](simbologia.md).
- Se genera la miniatura.
- Si no ha escrito un resumen en **Metadatos**, se genera uno, por ejemplo «Capa vectorial que
  contiene información sobre *título*».

## Crear una capa vacía

**Crear capa vacía** crea una tabla nueva en PostGIS, con los campos que usted defina, y la publica
como capa. Es útil para capas que se van a dibujar en el visor con la herramienta de edición.

![Pestaña Campos del formulario Crear capa](img/capas-crear-capa-vacia-campos.png)

En la pestaña **General**, además de los campos de publicación:

- **Almacén de datos**: solo almacenes PostGIS. A los superusuarios se les ofrecen todos; al resto
  del personal, los que han creado y los que tienen asignados como propios.
- **Nombre del recurso**: el nombre de la tabla. Debe empezar por una letra o un guion bajo, y solo
  admite letras, números y guiones bajos. Se guarda en minúsculas. Si ya existe una tabla con ese
  nombre, se indica que la publique en lugar de crearla.
- **Tipo de geometría**: **Punto**, **Multipunto**, **Línea**, **Multilínea**, **Polígono** o
  **Multipolígono**.
- **Sistema de referencia de coordenadas** de la geometría.

En la pestaña **Campos**, pulse **Añadir campo** para cada columna. Para cada uno elija el tipo
(texto, entero, decimal, booleano, fecha, hora, fecha y hora, JSON, enlace, enumeración o
formulario, según lo que tenga activo la instalación), el **Nombre del campo** y, si procede, un
cálculo automático (**Calculado**).

Al crear la capa vacía, su rol principal aparece marcado también con permiso de escritura, para
que pueda empezar a editarla.

## Modificar una capa

Pulse **Actualizar capa** en la fila de la capa. En la pestaña **General** el espacio de trabajo,
el almacén de datos y el nombre del recurso aparecen bloqueados. Puede cambiar:

- **Título** y **Formato**, como al publicar.
- **Grupo de capas**: mueve la capa a otro grupo. Solo si gestiona los dos grupos; si no gestiona
  el grupo actual, el campo aparece bloqueado.
- **Icono**: una imagen (.jpg, .jpeg, .png o .svg) que acompaña a la capa.

!!! note "Posición de la capa en su grupo"
    Guardar el formulario no cambia la posición de la capa. Si la pasa a otro grupo, se coloca la
    primera del grupo nuevo; para ordenarla, use la pestaña **Capas del grupo** (ver
    [Modificar un grupo](grupos-capas.md#modificar-un-grupo)).

Pulse **Guardar** para aplicar los cambios, o **Cancelar** para volver sin guardar.

### Pestaña Propiedades de visualización

![Pestaña Propiedades de visualización de la capa](img/capas-propiedades-visualizacion.png)

- **Timeout (milisegundos)**: en el visor clásico, tiempo tras el que la capa se marca con error si
  no ha terminado de cargar.
- **Límite de registros en peticiones WFS**: máximo de elementos que GeoServer devuelve en cada
  petición WFS de la capa. Con 0 no hay límite. Solo en capas vectoriales.
- **Visible**: la capa aparece encendida al abrir el visor.
- **Cacheada**: GeoServer guarda las teselas ya dibujadas (GeoWebCache) y el visor las reutiliza.
  Acelera mucho las capas pesadas, pero los cambios en los datos o en el estilo no se ven hasta
  que se limpia la caché (ver [Gestión de la caché](servicios-avanzados.md#gestion-de-la-cache)).
- **Consultable**: al pulsar sobre el mapa, el visor muestra la información de los elementos de la
  capa.
- **Imagen simple (sin tiles)**: la capa se pide como una sola imagen en lugar de en teselas.
  **No se puede combinar con Cacheada**: al marcar una, se desmarca la otra.
- **Parámetro temporal**: activa la dimensión temporal (ver [Capas temporales](#capas-temporales)).
- **Permitir descargas**: ofrece al usuario la descarga de los datos de la capa en el visor.
- **Permitir atributos calculados**: permite a quien puede escribir en la capa usar la calculadora
  de atributos. Solo en capas vectoriales de PostGIS.
- **Ver en tiempo real** e **Intervalo de actualización (milisegundos)**: en el visor clásico, la
  capa se vuelve a pedir cada ese intervalo.

Con **vector tiles** como formato, al guardar se activa ese formato en GeoWebCache; si no se puede,
aparece un aviso y el visor no podrá cargar la capa como teselas vectoriales.

### Capas temporales

Al marcar **Parámetro temporal** aparecen:

- **Campo temporal** y, si los datos son intervalos, **Campo temporal (fin intervalo)**: campos de
  fecha de la tabla.
- **Resolución temporal** y **Presentación temporal** (**Intervalo continuo**).
- **Modo para asignar valores por defecto**: **Menor valor del dominio**, **Mayor valor del
  dominio**, **Valor más cercano al valor referencia** o **Valor de referencia**. En los dos últimos
  hay que indicar el **Valor por defecto** con el formato DD-MM-AAAA hh:mm:ss.

Si falta el campo, el modo o la fecha, el formulario no se guarda e indica qué falta.

### Pestaña Permisos

![Pestaña Permisos de la capa](img/capas-permisos.png)

- **Es pública**: cualquiera puede ver la capa, también sin iniciar sesión. Mientras está marcada,
  las casillas de lectura quedan bloqueadas.
- Para cada rol:
    - **Permiso de lectura**: ve la capa y consulta sus datos.
    - **Permiso de escritura**: además, puede editar sus elementos. No está disponible en las vistas
    SQL y no se aplica a las capas ráster.
    - **Permiso de gestión**: puede modificar, configurar y eliminar la capa en la administración.

El buscador filtra los roles. El rol de administración tiene siempre lectura y escritura, aunque no
aparezca. Los roles con un icono atenuado tienen permisos puestos por una herramienta de permisos
específica y no se pueden cambiar aquí.

!!! warning "Capas usadas en paneles públicos"
    Si está instalado el plugin de paneles y la capa se usa en un panel público, no se puede quitar
    la marca **Es pública**: el formulario lo impide e indica qué paneles la usan.

Un proyecto público no hace públicas sus capas: cada capa conserva sus permisos (ver
[Pestaña Permisos del proyecto](proyectos.md#pestana-permisos)).

### Pestaña Metadatos

- Sin el plugin de catálogo: **Metadatos: Abstract**, un resumen de la capa. Si se deja vacío, se
  genera uno automático al guardar.
- Con el plugin de catálogo: el **UUID** del metadato en el catálogo y los botones **Editar en
  catálogo** o **Crear metadato**. El resumen que ya tuviera la capa se conserva al guardar.

### Pestaña Información detallada

**Activar información detallada** añade a la capa, en la tabla de contenidos del visor, una ficha
con el **HTML** que escriba aquí. **Título del botón en el TOC** es el texto del botón que la abre. El
botón **Generar Metadatos Enriquecidos con Campos** prepara una ficha con la descripción y la lista
de campos de la tabla.

Si está instalado GeoCopilot, la pestaña **GeoCopilot** permite describir la capa y sus campos para
el asistente, y marcar los campos con datos personales.

## Configurar los campos

**Configurar capa** abre la configuración de los campos de una capa vectorial de PostGIS. Pulse
**Guardar** para aplicar los cambios de las casillas, o **Volver** para salir.

![Pestaña Gestión de campos de la configuración de capa](img/capas-configurar-campos.png)

### Gestión de campos

Para cada campo:

| Casilla | Efecto |
|---|---|
| **Nulable** | Si se desmarca, la columna pasa a ser obligatoria **en la base de datos**. Si ya hay registros sin valor, no se permite y se muestra un aviso |
| **Obligatorio** | Exige el campo en los formularios de edición. Si el campo no es nulable, es obligatorio siempre |
| **¿Visible?** | El campo aparece en la tabla de atributos del visor |
| **¿Editable?** | El campo se puede modificar en los formularios de edición. No disponible en vistas SQL |
| **¿Mostrar en getFeatureInfo?** | El campo aparece al consultar un elemento en el mapa |

Pulsando el título de una columna se marcan o desmarcan todas sus casillas. Los campos de control
de la plataforma aparecen como **Campo reservado** y no se pueden cambiar.

El menú **Acciones** de cada campo ofrece **Renombrar**, **Gestionar formato**, **Convertir a
enumerado** (o **Cambiar enumeración**) y **Eliminar campo**. **Añadir campo** crea una columna
nueva.

!!! warning "Renombrar, añadir y eliminar campos actúan al momento"
    Estas acciones cambian la tabla de la base de datos en cuanto se confirman, sin esperar a
    **Guardar**. **Eliminar campo** borra la columna y sus datos, y no se puede deshacer.

### Otras pestañas

- **Títulos de campo**: el alias de cada campo en cada idioma de la instalación. Es el nombre que
  ven los usuarios; si se deja vacío, se usa el nombre del campo.
- **Grupos de campos** y **Títulos del grupo**: agrupan los campos en secciones del formulario de
  edición. Arrastre los campos bajo un grupo y los grupos para ordenarlos.
- **Restricciones de edición**: **Reglas topológicas** que se comprueban al editar (**No debe
  solaparse**, **No debe tener huecos**, **Debe estar cubierto por**, **No debe solaparse con**,
  **Debe ser contiguo**). Solo los superusuarios pueden cambiarlas.
- **Disparadores**: asigna a un campo un cálculo automático de la conexión de base de datos, que se
  ejecuta al insertar, modificar o borrar elementos.

## Eliminar una capa

**Eliminar capa** pide confirmación y, al aceptar:

- Se borra la capa de GeoServer, con sus estilos y sus reglas de acceso.
- Se quita del grupo y de la tabla de contenidos de los proyectos.
- Se borran su miniatura, su metadato del catálogo (si lo hay) y los disparadores asociados.
- En los mosaicos, se borran también sus ficheros de índice.

**La tabla de la base de datos y los ficheros ráster no se borran.** La capa se puede volver a
publicar más tarde desde el mismo almacén.

Si GeoServer no responde, la operación se cancela. Si GeoServer da error al borrar, la capa se
elimina igualmente de gvSIG Online y aparece el aviso **La capa no pudo eliminarse de GeoServer,
pero se eliminó de la lista de todos modos**; en ese caso, revise GeoServer.
