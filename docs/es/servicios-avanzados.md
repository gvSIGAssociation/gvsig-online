# Otras herramientas de servicios

Además de los servidores, almacenes, grupos de capas y capas, el menú **Servicios** del panel de
administración reúne varias herramientas de apoyo: **Gestión de la caché**, **Atribuciones**,
**URLs de los servicios** y **Vistas SQL**. En el menú **Tipos de datos** están las
**Enumeraciones**.

**Atribuciones** y **URLs de los servicios** solo aparecen en el menú de los superusuarios, que son
quienes pueden usarlas. El resto de apartados los ven y usan también el personal (*staff*).

## Quién puede hacer qué

| Herramienta | Quién |
|---|---|
| **Gestión de la caché** | Personal y superusuarios. Los superusuarios ven todas las capas y grupos cacheados; el resto, las capas que crearon o en las que tienen permiso de gestión, y los grupos que crearon o en los que tienen permiso de gestión |
| **Atribuciones** | Solo superusuarios |
| **URLs de los servicios** | Solo superusuarios |
| **Vistas SQL** | Personal y superusuarios. Los superusuarios ven y modifican todas; el resto, solo las que crearon |
| **Enumeraciones** | Personal y superusuarios. Los superusuarios ven todas; el resto, las que crearon |

## Gestión de la caché

La caché de teselas guarda las imágenes ya generadas de una capa o de un grupo de capas, para que
el visor no tenga que pedírselas al servidor de mapas cada vez. Esta página sirve para generar
esas teselas por adelantado y para borrarlas cuando los datos cambian.

Solo aparecen las capas y los grupos que tienen la caché activada (en el formulario de la
[capa](capas.md), del [grupo de capas](grupos-capas.md) o, para un WMS externo, de la
[capa externa](capas-externas.md)). La página tiene dos pestañas, **Capas cacheadas** y **Grupos
cacheados**, cada una con su buscador. En cada fila:

- **Limpiar caché**: borra las teselas guardadas. En un grupo, borra la caché de todas sus capas y
  la del propio grupo. Úselo después de cambiar los datos o el estilo, si el visor sigue mostrando
  la versión anterior.
- **Configurar opciones de caché**: abre la página de tareas de la capa o del grupo.

### Crear una tarea de caché

![Crear una tarea de caché](img/servicios-avanzados-cache-tarea.png)

En la pestaña **Crear nueva tarea**:

- **Número de hilos a usar**: de 1 a 16. Más hilos terminan antes, pero cargan más el servidor.
- **Tipo de operación**:
    - **Seed - generar tiles**: genera solo las teselas que faltan.
    - **Reseed - Regenerar tiles**: vuelve a generar todas las teselas.
    - **Truncate - Borrar tiles**: borra las teselas.
- **Rejilla**: el sistema de teselado. Solo se ofrecen las rejillas configuradas para esa capa o
  grupo en el servidor. Al elegirla se proponen su **Zoom inicial** y su **Zoom final**.
- **Zoom inicial** y **Zoom final**: los niveles de zoom que abarca la tarea. Cuantos más niveles,
  más teselas: su número crece muy deprisa con cada nivel de zoom.
- **Extensión**: active el botón del lápiz en el mapa y dibuje un rectángulo con la zona que quiere
  procesar. Los campos **MínX**, **MínY**, **MaxX** y **MaxY** muestran la extensión en grados.

Pulse **Ejecutar**. La tarea la ejecuta el servidor de mapas en segundo plano y la página vuelve a
la lista.

### Seguir las tareas

La pestaña **Tareas actualmente en ejecución** muestra, para cada tarea, las **Tiles procesadas**,
el **Total de tiles a procesar**, el **Total de tiles pendientes**, el **ID de la tarea** y su
**Estado de la tarea**. Pulse **Refrescar tareas** para actualizarla, o **Eliminar todas las
tareas** para detener las tareas de esa capa o grupo.

## Atribuciones

Las **atribuciones** son la información legal y de contacto que acompaña a un proyecto: avisos de
copyright y licencias, ayuda, datos de contacto, aviso legal, enlaces y documentos. En el visor
actual se muestran en una pastilla sobre el mapa con el título y la descripción; al pulsarla se
abre una ventana con el resto. Esto requiere que la instalación tenga el plugin
`gvsigol_plugin_projectapi`.

### Qué configuración se aplica a cada proyecto

Hay dos tipos de configuración:

- **Genérica**: reutilizable. Se aplica a todos los proyectos (**Activa para todos los proyectos**)
  o a los que se marquen en **O selecciona proyectos manualmente**.
- **Específica de proyecto**: para un único proyecto. Solo puede haber una por proyecto.

Para cada proyecto se usa la configuración específica activada, si existe. Si no, la primera
genérica activada que se le aplique, por orden alfabético del título. Si no hay ninguna, el visor
no muestra atribuciones.

### Lista de configuraciones

La lista muestra el **Título**, el **Tipo**, el **Proyecto** (o **Todos los proyectos**, o
**Proyectos seleccionados**), el **Estado** y la **Última modificación**. En cada fila: **Editar**,
**Usar como plantilla para una específica de proyecto** (solo en las genéricas) y **Eliminar**.

Si todavía no hay ninguna configuración genérica, la página recomienda crear una primero
(**Crear configuración genérica**).

### Crear o editar una configuración

![Formulario de atribuciones](img/servicios-avanzados-atribuciones-formulario.png)

Pulse **Nueva configuración**. Para partir de una genérica, elíjala en **Copiar desde
genérica...** o use **Usar como plantilla para una específica de proyecto** en la lista: se copian
sus textos, enlaces y adjuntos, y la nueva configuración es específica de proyecto.

- **Información general**: **Título** (el que se ve en la pastilla del mapa), **Tipo**,
  **Descripción** (texto breve; por ejemplo, notas de licencia) y **Activado**.
- **Proyectos asociados**: el **Proyecto**, si es específica; o **Activa para todos los
  proyectos** o la selección manual, si es genérica.
- **Orden del contenido del modal**: arrastre los bloques para ordenar la ventana del visor. Los
  bloques vacíos no se muestran.
- **Aviso de copyright**, **Otros** (**Título personalizado** y **Texto personalizado**),
  **Ayuda**, **Información de contacto** (**Organización**, **Persona de contacto**, **Dirección**,
  **Teléfono**, **Correo electrónico**) y **Aviso legal**.
- **Enlaces de interés**: **Añadir enlace** para cada dirección, con su descripción.
- **Archivos adjuntos** y **Logotipo**: se eligen con el selector del
  [gestor de archivos](gestor-archivos.md) (**Seleccionar archivo...**); aquí no se suben ficheros.

Ningún campo admite etiquetas HTML: el formulario lo rechaza.

!!! warning "Los adjuntos son públicos"
    Los adjuntos y el logotipo se pueden descargar sin iniciar sesión, aunque el proyecto sea
    privado. No elija ficheros que no deban difundirse.

## URLs de los servicios

Guarda las direcciones de servicios **WMS**, **WMTS**, **WFS** o **CSW** para tenerlas a mano. Para
cada una: **Título**, **Tipo** y **URL**. Use la dirección base del servicio, sin parámetros de
petición.

Pulse **Añadir servicio** para crear una; en la lista, **Actualizar servicio** y **Eliminar
servicio** para modificarla o borrarla.

Las URL guardadas se usan en:

- La página de inicio: si hay al menos una, aparece el acceso **Servicios de mapa**, una página
  pública que las lista agrupadas por tipo.
- Las herramientas que añaden capas desde servicios; por ejemplo, el plugin de importación desde
  servicios ofrece las de tipo WMS y WFS.

## Vistas SQL

Una **vista SQL** es una tabla virtual definida por una consulta sobre una o varias tablas de un
almacén de datos: elige las tablas, cómo se unen, los campos y los filtros, sin escribir SQL. Se
crea como una vista en la base de datos y, si incluye una columna de geometría, se puede publicar
como capa desde [Capas](capas.md), eligiéndola en su almacén de datos como si fuera una tabla.

La lista muestra el **Nombre**, el **Almacén de datos** y las **Tablas** de cada vista, con los
botones **Actualizar Vista SQL** y **Borrar Vista SQL**. Pulse **Añadir Vista SQL** para crear una.

![Pestaña Tablas de una vista SQL](img/servicios-avanzados-vistas-sql-tablas.png)

El formulario tiene cuatro pestañas:

- **General**:
    - **Almacén de datos**: donde se crea la vista. Solo se ofrecen almacenes PostGIS; los usuarios
    que no son superusuarios ven los que crearon o su almacén por defecto.
    - **Nombre**: el nombre de la vista en la base de datos. No puede coincidir con el de otra tabla
    o vista del almacén.
- **Tablas**: **Añadir tabla** para cada tabla. Elija su **Almacén de datos** (solo los de la misma
  base de datos) y la **Tabla**; el **Alias de tabla** se asigna solo. A partir de la segunda,
  indique el **Campo 1 del JOIN** y el **Campo 2 del JOIN**, que deben ser del mismo tipo. Solo se
  incluyen las filas que tienen correspondencia en ambas tablas.
- **Campos**: marque los **Campos incluidos** y, si quiere, cambie su **Alias** (no se pueden
  repetir).
    - **Clave primaria de la vista**: el campo que identifica cada fila, o **Generar clave entera
    única (recomendado en joins)** (`gvol_pk`). Si no elige ninguna, se genera la clave cuando hay
    varias tablas y se usa la de la tabla cuando hay una sola.
    - **Columna de geometría**: solo puede haber una; las demás se omiten.
- **Filtros**: **Añadir condición** (campo, operador y **Valor**) o **Añadir grupo**, y elija cómo
  se combinan en **Combinar grupos con**: **AND (todas)** u **OR (cualquiera)**. Los grupos permiten
  mezclar ambos, por ejemplo (A OR B) AND C. Con **IN**, separe los valores por comas; **contiene**
  y **no contiene** no distinguen mayúsculas.

Pulse **Guardar**. Si la vista no se puede crear, el formulario muestra el motivo (por ejemplo,
«Ya existe un objeto con este nombre» o «La vista necesita una clave primaria») y no cambia nada:
al crearla no se guarda, y al modificarla se conservan la vista y la definición anteriores.

!!! warning "Antes de renombrar o borrar una vista"
    - Si cambia el **Nombre**, se crea la vista con el nombre nuevo, que no puede estar ocupado
      por otra tabla o vista. La vista con el nombre anterior se borra si ninguna capa la usa; si
      alguna la usa, se conserva para no romperla. Las capas no cambian de vista solas.
    - **Borrar Vista SQL** elimina la vista de la base de datos. Las capas que la usan no se
      borran, pero dejan de funcionar: revise antes cuáles son.

## Enumeraciones

Una **enumeración** es una lista cerrada de valores entre los que los usuarios eligen al editar
un campo. Se gestionan en **Tipos de datos** > **Enumeraciones**.

Una vez creada, se asigna a un campo de una capa con el tipo **Enumeration** (un valor) o
**Multiple enumeration** (varios valores), al crear la capa o al añadirle campos (ver
[Capas](capas.md)).

![Formulario de una enumeración](img/servicios-avanzados-enumeracion.png)

Pulse **Añadir enumeración**:

- **Nombre**: el identificador. Se propone uno (`enm_` y un número), no puede repetirse y no se
  puede cambiar después.
- **Título**: el nombre que ven los usuarios. Es obligatorio.
- **Orden de los elementos**: **Manual** (arrastre los elementos para ordenarlos) o **Alfabético**
  (se ordenan al guardar).
- **Mostrar primer elemento por defecto**: en el formulario de edición del visor actual, un campo
  de enumeración simple sin valor aparece con el primer elemento ya elegido.
- **Elementos de la enumeración**: **Añadir elemento** para cada valor. Los elementos no pueden
  contener punto y coma (;); los vacíos se descartan.

En la **Lista de enumeraciones**, **Actualizar enumeración** abre el formulario y **Eliminar
enumeración** la borra tras pedir confirmación.
