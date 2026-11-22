# Capas externas

Una **capa externa** es una capa que sirve otra organización (un WMS, un WMTS, teselas XYZ,
OpenStreetMap, Bing o teselas vectoriales) y que se muestra en el visor sin copiar sus datos. Los
datos siguen en el servicio de origen: si ese servicio no responde, la capa no se ve.

Las capas externas se gestionan desde el panel de administración, en **Servicios** > **Capas
externas**. Como cualquier otra capa, pertenecen a un grupo de capas, y llegan al visor cuando ese
grupo forma parte de un proyecto.

## Quién puede hacer qué

| Acción | Quién |
|---|---|
| Ver la lista de capas externas | Personal (*staff*) y superusuarios. Los superusuarios ven todas; el resto, las que crearon y aquellas en las que alguno de sus roles tiene permiso de gestión |
| Añadir una capa externa | Personal y superusuarios. Solo pueden elegir los grupos de capas que crearon o en los que tienen permiso de gestión (los superusuarios, todos) |
| Modificar o eliminar una capa externa | Los superusuarios, quien la creó y el personal con un rol que tenga permiso de gestión sobre la capa |

Las capas externas se crean siempre como **públicas**: las ve cualquier usuario que pueda abrir un
proyecto que las contenga.

## Lista de capas externas

![Lista de capas externas](img/capas-externas-lista.png)

La **Lista de capas externas** muestra el identificador, el **Título**, el **Tipo**, el **Grupo de
capas** y si está **Cacheada**. El buscador filtra la tabla.

En cada fila:

- **Actualizar capa externa**: abre el formulario de la capa.
- **Eliminar capa externa**: pide confirmación y la borra. Si la capa estaba cacheada, también se
  borra su caché.

Las capas externas también aparecen en la lista de capas de su grupo (ver
[Grupos de capas](grupos-capas.md)), desde donde se pueden modificar y eliminar igual que aquí.

!!! note "Capas 3D"
    Los tipos de capa que aportan los plugins, como las capas del visor 3D, no aparecen en esta
    lista: se crean y modifican desde el propio plugin (ver la
    [guía del visor 3D](doc:gvsigol_plugin_viewer3d/index.md)).

## Tipos de capa externa

El campo **Tipo** decide qué otros campos muestra el formulario:

| Tipo | Para qué sirve | Campos propios |
|---|---|---|
| **WMS** | Mapas de un servicio WMS, como imagen | **URL**, **Versión**, **Capas**, **Formato**, **Formato de featureinfo** |
| **WMTS** | Teselas ya generadas de un servicio WMTS | Los del WMS, más **MatrixSet** |
| **XYZ** | Teselas servidas con una plantilla de dirección `{z}/{x}/{y}` | **URL**, **API-key** |
| **Bing** | Mapas de Bing | **Capas** (`Road`, `Aerial` o `AerialWithLabels`), **API-key** |
| **OSM** | Teselas de OpenStreetMap o de un servidor compatible | **URL**, **API-key** |
| **Vector tiles (MVT)** | Teselas vectoriales con un estilo de Mapbox | **URL**, **API-key**, estilo y sistema de referencia |

## Añadir una capa externa

Pulse **Añadir capa externa**. El formulario tiene cuatro pestañas: **General**, **Propiedades de
visualización**, **Metadatos** e **Información detallada**.

### Pestaña General

![Formulario de una capa externa WMS](img/capas-externas-formulario-wms.png)

- **Tipo**: el tipo de servicio (ver la tabla anterior). Elíjalo primero.
- **URL**: la dirección del servicio o de las teselas.
- **Título**: el nombre que ven los usuarios en el visor. Se puede cambiar en cualquier momento.
- **Grupo de capas**: el grupo al que pertenece la capa. La capa se añade al final del grupo.

Para **WMS** y **WMTS**:

1. Escriba la **URL** del servicio y pulse **Conectar**. Se lee la descripción del servicio
   (GetCapabilities) y se rellenan las listas de **Versión**, **Capas**, **Formato** y **Formato de
   featureinfo**. Si el **Título** está vacío, se propone el del servicio.
2. Elija en **Capas** la capa del servicio que quiere mostrar. Al cambiar de capa o de versión, se
   vuelve a consultar el servicio.
3. Revise el **Formato** de imagen y el **Formato de featureinfo** (el de las respuestas de consulta
   de información).
4. En WMTS, elija el **MatrixSet**. Si su nombre no contiene 3857 ni 4326, aparece el aviso
   «Alerta: el matrixset seleccionado debe ser compatible con el CRS del mapa».

En WMS, los estilos que ofrece el servicio para esa capa se leen automáticamente al conectar o al
guardar.

Si la URL no está en el mismo dominio que la plataforma, aparece un aviso: algunos navegadores
podrían no cargar la capa por su política de dominios cruzados.

Para **Bing**, elija la capa en **Capas** y escriba su **API-key**. Para **XYZ** y **OSM**, escriba
la **URL** y, si el proveedor la exige, la **API-key**.

### Teselas vectoriales (MVT)

![Campos de una capa de teselas vectoriales](img/capas-externas-mvt.png)

- **URL del archivo de estilo Mapbox**: dirección de un estilo de Mapbox (`.json`).
- **O sube tu archivo de estilo Mapbox (.json)**: en lugar de una dirección, un fichero de estilo.
  Solo se puede usar una de las dos opciones: al rellenar una, la otra se desactiva.
- **Sistema de referencia de coordenadas por defecto**: el de las teselas. Si no está en la lista,
  elija **Otro** y escríbalo en **Indica tu sistema de referencia de coordenadas** (por ejemplo,
  `EPSG:25830`).

Si el fichero de estilo no se puede guardar, la capa se guarda igualmente y el formulario avisa de
que debe volver a subirlo. Subir ficheros de estilo requiere que la instalación tenga el plugin
`gvsigol_plugin_featureapi`.

### Pestaña Propiedades de visualización

![Pestaña Propiedades de visualización](img/capas-externas-propiedades-visualizacion.png)

- **Timeout (milisegundos)**: tiempo de espera de la capa. Por defecto, 30000.
- **Visible**: la capa aparece encendida al abrir el proyecto.
- **Cacheada** (solo WMS): la plataforma guarda una copia de las teselas en la caché de teselas
  (GeoWebCache) del servidor del grupo de capas, y el visor pide las teselas a esa caché en lugar
  de al servicio de origen. La caché se gestiona después en
  [Gestión de la caché](servicios-avanzados.md#gestion-de-la-cache).
- **Imagen simple (sin tiles)** (solo WMS): el visor pide una sola imagen para toda la vista en
  lugar de teselas.

**Cacheada** e **Imagen simple (sin tiles)** no se pueden combinar: al marcar una, la otra se
desmarca y aparece un aviso.

!!! warning "Si la caché falla"
    Si al guardar no se puede registrar la capa en la caché, el formulario muestra un error. La
    capa queda creada, pero sin caché: búsquela en la lista y revise sus datos.

### Pestaña Metadatos

**Metadatos: Abstract**: un resumen de la capa. Si se deja vacío, se genera uno a partir del
título.

Al modificar una capa externa, si la instalación tiene el plugin de catálogo, esta pestaña muestra
en su lugar el **UUID** del metadato y los botones **Crear metadato** o **Editar en catálogo**.

### Pestaña Información detallada

Marque **Habilitar información detallada** para añadir a la capa un botón en la tabla de contenidos
que muestra un contenido HTML propio:

- **Título del botón en el TOC**: el texto del botón. Por defecto, «Información detallada».
- **HTML**: el contenido que se muestra al pulsarlo. Se propone una plantilla con el título y la
  descripción de la capa.

Pulse **Guardar** para crear la capa, o **Cancelar** para salir sin guardar.

## Modificar una capa externa

Pulse **Actualizar capa externa** en la lista. El formulario es el mismo que el de creación.

- Puede cambiar el **Tipo**, la **URL**, la capa del servicio y el **Grupo de capas**. Para WMS y
  WMTS, pulse **Conectar** de nuevo si cambia la URL.
- Si desmarca **Cacheada**, la capa deja de usar la caché aunque el borrado de la caché en el
  servidor falle o tarde.
- Si cambia la URL, la capa, el formato, el estilo por defecto, el sistema de referencia o el grupo
  de una capa cacheada, se vuelve a registrar en la caché.

Si llegó al formulario desde un grupo de capas, al guardar vuelve a ese grupo.

## Eliminar una capa externa

**Eliminar capa externa** pide confirmación («La capa externa será borrada») y la borra del grupo
y de todos los proyectos que la usaban. Se borran también su caché y el fichero de estilo subido,
si los tenía. Los datos del servicio de origen no se ven afectados.

## Usar capas externas en los proyectos

Las capas externas llegan a un proyecto a través de su grupo de capas:

1. Cree la capa externa en un grupo de capas.
2. En el proyecto, pestaña **Grupos de capas**, marque ese grupo (ver
   [Gestión de proyectos](proyectos.md#pestana-grupos-de-capas)).

### Como capa base

Los servicios de mapa de fondo (OpenStreetMap, ortofotos WMS o WMTS, Bing, XYZ) suelen usarse como
**capas base**. Para ello:

1. Cree las capas externas en un grupo dedicado a mapas de fondo.
2. En el proyecto, marque ese grupo como **Grupo base**. Todas sus capas pasan a ser capas base.
3. Elija la **Base por defecto**, con la que se abre el visor, y, si quiere, la **Vista general**
   del mapa de situación.
