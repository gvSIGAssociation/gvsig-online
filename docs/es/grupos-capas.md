# Grupos de capas

Un **grupo de capas** reúne varias capas bajo un mismo título. En el visor se muestra como una
carpeta de la tabla de contenidos. Los proyectos no se componen de capas sueltas, sino de grupos de
capas: para que una capa aparezca en un proyecto, su grupo tiene que estar asignado a ese proyecto
(ver [Gestión de proyectos](proyectos.md)).

Cada grupo pertenece a un servidor de mapas y se publica también en GeoServer como grupo de capas.

Los grupos se gestionan desde el panel de administración, en **Servicios** > **Grupos de capas**.

## Quién puede hacer qué

| Acción | Quién |
|---|---|
| Ver la lista de grupos | Personal (*staff*) y superusuarios. Los superusuarios ven todos; el resto, los grupos que han creado y aquellos en los que alguno de sus roles tiene **Permiso de gestión** |
| Crear un grupo | Personal y superusuarios |
| Modificar, limpiar la caché o eliminar un grupo | Quien lo gestiona: los superusuarios, quien lo creó y quien tenga un rol con **Permiso de gestión** en el grupo |
| Incluir el grupo en un proyecto o publicar capas en él | Los superusuarios, quien lo creó y quien tenga un rol con **Permiso para incluir en proyectos** |
| Ver y cambiar la pestaña **Permisos** | Superusuarios siempre; el resto del personal, salvo que la instalación tenga desactivada la gestión de permisos en la interfaz |

## Lista de grupos de capas

![Lista de grupos de capas con su servidor y los proyectos a los que están asignados](img/grupos-capas-lista.png)

La lista muestra, para cada grupo, su identificador, el **Nombre**, el **Título**, el **Servidor** y
la columna **Asignado a**, con los proyectos que lo incluyen. El buscador filtra por nombre y por
título, y la tabla se pagina.

### Grupos de un proyecto

Desde la lista de proyectos, el botón **Grupos de capas del proyecto** abre esta misma lista
filtrada por ese proyecto. En ese caso:

- Aparece el botón **Volver al listado de proyectos**.
- Un grupo creado con **Añadir grupo de capas** se asigna automáticamente a ese proyecto y se añade
  a su tabla de contenidos.

### Acciones de cada fila

- **Actualizar grupo de capas**: abre el formulario del grupo.
- **Limpiar caché**: vacía la caché de teselas de todas las capas del grupo (y la del propio grupo)
  y vuelve a generar el grupo en GeoServer. Úselo cuando el visor muestre imágenes antiguas.
- **Eliminar grupo de capas**: pide confirmación y lo borra (ver
  [Eliminar un grupo](#eliminar-un-grupo)).

### El grupo «Por defecto»

Existe un grupo interno, **Por defecto**, que no aparece en la lista. Se ofrece como opción al
publicar una capa y recoge las capas de los grupos que se eliminan. No se puede asignar a
ningún proyecto, así que sus capas no se ven en ningún visor hasta que se cambian de grupo.

## Crear un grupo

Pulse **Añadir grupo de capas**. El formulario tiene dos pestañas: **General** y **Permisos**.

![Pestaña General del formulario de grupo de capas](img/grupos-capas-formulario-general.png)

### Pestaña General

- **Seleccionar servidor**: el servidor de mapas donde se publicará el grupo. Solo podrá contener
  capas de almacenes de datos de ese servidor. **No se puede cambiar después.**
- **Nombre**: el identificador interno del grupo. **No se puede cambiar después.**
    - Debe empezar por una letra o un guion bajo, y solo admite letras sin acentos, números y guiones
    bajos.
    - Al guardar, se le añade al final un guion bajo y su nombre de usuario. Por ejemplo, si el
    usuario *jperez* escribe `carreteras`, el grupo se llamará `carreteras_jperez`.
    - No puede repetirse: si ya existe, el formulario lo indica.
- **Título**: el nombre que ven los usuarios en la tabla de contenidos del visor. Se puede cambiar
  en cualquier momento.
- **Crear caché para este grupo de capas**: el grupo se sirve como un único mapa teselado y cacheado
  en GeoServer. Solo tiene efecto en el visor cuando el proyecto tiene activada la opción **Grupos
  de capas seleccionables** (ver
  [Tabla de contenidos y acceso](proyectos.md#tabla-de-contenidos-y-acceso)).
- **Es visible**: en los proyectos con **Grupos de capas seleccionables**, el grupo aparece
  encendido al abrir el visor. No se aplica cuando el grupo hace de grupo base del proyecto.

### Pestaña Permisos

![Pestaña Permisos del grupo de capas](img/grupos-capas-permisos.png)

Para cada rol, marque:

- **Permiso para incluir en proyectos**: los usuarios con ese rol pueden añadir el grupo a sus
  proyectos y publicar capas en él.
- **Permiso de gestión**: además, pueden modificarlo, limpiar su caché y eliminarlo.

El buscador filtra los roles por nombre y descripción. Al crear un grupo, su rol principal aparece
marcado en las dos columnas. El rol de administración tiene siempre los dos permisos, aunque no
aparezca en la lista.

!!! note "Permisos del grupo y permisos de las capas"
    Los permisos del grupo deciden quién puede usarlo y gestionarlo en la administración. No dan
    acceso a los datos: quién ve o edita cada capa se decide en los permisos de la propia capa (ver
    [Permisos de la capa](capas.md#pestana-permisos)).

Pulse **Guardar** para crear el grupo, o **Cancelar** para salir sin guardar. Para añadirle capas,
edítelo después de guardarlo.

## Modificar un grupo

Pulse **Actualizar grupo de capas** en la fila del grupo. El formulario tiene tres pestañas:
**General**, **Capas del grupo** y **Permisos**. En la pestaña **General** el servidor y el nombre
aparecen bloqueados; el resto de campos son los mismos que al crearlo.

### Pestaña Capas del grupo

![Pestaña Capas del grupo, con las capas ordenables y sus botones](img/grupos-capas-capas-del-grupo.png)

La pestaña muestra cuántas capas tiene el grupo y las lista con su título y su nombre completo
(espacio de trabajo y nombre).

**Orden de las capas.** Arrastre cada capa por su asa (⋮⋮) para cambiar su posición. La capa de
arriba es la primera del grupo en la tabla de contenidos del visor. El nuevo orden se aplica al pulsar **Guardar**.

**Añadir capas.** Desde aquí puede:

- **Crear capa vacía**: crea una tabla nueva y la publica en este grupo.
- **Publicar capa**: publica en este grupo una tabla o un fichero que ya está en un almacén de datos.

Los dos botones guardan antes el grupo (se pide confirmación) y, al terminar, vuelven a este
formulario. Ver [Publicar una capa](capas.md#publicar-una-capa) y
[Crear una capa vacía](capas.md#crear-una-capa-vacia). Algunos plugins añaden aquí botones propios;
por ejemplo, el visor 3D añade uno para añadir capas 3D.

**Botones de cada capa.** Solo están activos en las capas que usted puede gestionar:

- **Actualizar capa**: abre el formulario de la capa (o el de capa externa, si lo es).
- **Configurar capa**: configuración de los campos. Solo en capas vectoriales de PostGIS.
- **Limpiar caché**: solo en capas cacheadas.
- **Eliminar capa**: borra la capa en ese momento, sin esperar a que guarde el grupo.

!!! warning "Guardar el grupo limpia la caché de sus capas"
    Cada vez que pulsa **Guardar** en un grupo, se vuelve a generar el grupo en GeoServer y se
    limpia la caché de todas sus capas, que además vuelven a calcular su extensión y su miniatura.
    En grupos con muchas capas, o con capas pesadas, el guardado puede tardar.

Al cambiar el título, se actualiza también en la tabla de contenidos de los proyectos que incluyen
el grupo.

## Eliminar un grupo

**Eliminar grupo de capas** pide confirmación y, al aceptar:

- El grupo se quita de todos los proyectos que lo tenían asignado.
- **Sus capas no se borran**: pasan al grupo **Por defecto** y dejan de verse en los visores. Para
  recuperarlas, cámbielas de grupo desde el formulario de cada capa.
- El grupo se borra de GeoServer.

Si lo que quiere es borrar también las capas, elimínelas antes desde la pestaña **Capas del grupo**
o desde la [lista de capas](capas.md).

## Relación con los proyectos

- Un mismo grupo puede estar en varios proyectos. Los cambios en el grupo (título, orden de capas,
  capas nuevas) se ven en todos ellos.
- Los grupos se asignan al proyecto en su pestaña **Grupos de capas**. Allí solo se ofrecen los
  grupos para los que usted tiene **Permiso para incluir en proyectos** y los que el proyecto ya
  tenía (ver [Pestaña Grupos de capas](proyectos.md#pestana-grupos-de-capas)).
- Uno de los grupos del proyecto puede ser el **Grupo base**, con las capas de fondo. Esto se
  decide en el proyecto, no en el grupo.
- Desde el formulario del proyecto, **Añadir grupo de capas** crea un grupo nuevo, lo asigna al
  proyecto y vuelve al proyecto al guardar.
