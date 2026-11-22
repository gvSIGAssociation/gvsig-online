# Servidores y almacenes de datos

Antes de publicar una capa, gvSIG Online necesita saber **dónde se publica** (un servidor de mapas
GeoServer y un espacio de trabajo dentro de él) y **de dónde se leen los datos** (un almacén de
datos). Este capítulo explica cómo se configuran esas piezas y qué pasa en GeoServer y en la base
de datos al crearlas, cambiarlas o eliminarlas.

Se gestionan desde el panel de administración, en el menú **Servicios**: **Servidores**,
**Espacios de trabajo**, **Conexiones** y **Almacenes de datos**.

## Cómo encajan las piezas

```
Servidor (GeoServer, con sus nodos)
 └─ Espacio de trabajo  (ws_ventas)
     └─ Almacén de datos (ventas, tipo PostGIS) ──usa──► Conexión (PostgreSQL)
         └─ Capas         (comercios, rutas…)
```

- Un **servidor** es una instalación de GeoServer. Puede tener varios **nodos** (copias de
  GeoServer que sirven los mismos datos).
- Un **espacio de trabajo** agrupa almacenes y capas bajo un nombre, con sus propias direcciones
  de servicio (WMS, WFS…). Pertenece a un servidor.
- Un **almacén de datos** indica a GeoServer de dónde leer los datos: un esquema de una base de
  datos PostGIS, un fichero ráster o un servicio WMS remoto. Pertenece a un espacio de trabajo.
- Una **conexión** guarda los datos de acceso a una base de datos o a un servicio externo (servidor,
  usuario, contraseña…). Los almacenes PostGIS la usan en lugar de repetir las credenciales, y otras
  herramientas, como la ETL, también pueden usarla.
- Las **capas** se publican siempre desde un almacén de datos (ver [Capas](capas.md)).

Cuando un usuario pasa a ser personal (*staff*), la plataforma le crea automáticamente, en el
servidor por defecto, un espacio de trabajo `ws_<usuario>` y un almacén PostGIS `ds_<usuario>` con
su propio esquema en la base de datos de la plataforma.

## Quién puede hacer qué

| Acción | Quién |
|---|---|
| Ver, crear, modificar y eliminar servidores | Solo superusuarios |
| Ver, crear, modificar y eliminar espacios de trabajo | Solo superusuarios. El personal no ve estas entradas en el menú |
| Ver la lista de conexiones | Personal y superusuarios. Los superusuarios ven todas; el resto, las que creó, las que tienen **Permitir todos - Gestión** y aquellas en las que alguno de sus roles tiene **Gestión** |
| Crear una conexión | Personal y superusuarios |
| Modificar una conexión | Quien la gestiona: superusuarios, quien la creó y los roles con permiso de gestión |
| Cambiar los permisos de una conexión | Solo superusuarios |
| Probar, configurar (**Opciones**) o eliminar una conexión | Solo superusuarios |
| Ver la lista de almacenes de datos | Personal y superusuarios. Los superusuarios ven todos; el resto, los que creó, los que tienen **Permitir todos - Uso** y aquellos en los que alguno de sus roles tiene **Puede usar** |
| Crear un almacén de datos | Personal y superusuarios. El personal solo ve sus propios espacios de trabajo y las conexiones que tiene permiso para usar en almacenes |
| Modificar o eliminar un almacén de datos | Superusuarios, quien lo creó y quien tenga **Permitir todos - Gestión** o un rol con **Gestión** |
| Cambiar los permisos de un almacén de datos | Solo superusuarios y quien lo creó |

## Servidores

![Pestaña Nodos de un servidor](img/servidores-nodos.png)

La lista muestra el nombre, el título, el tipo y la **URL del frontal** de cada servidor. Pulse
**Añadir servidor** para registrar uno nuevo.

### Pestaña Servidor

- **Nombre**: se genera solo (`server_` y seis letras) y no se puede cambiar.
- **Título** y **Descripción**: lo que se muestra en las listas.
- **Tipo**: solo se admite GeoServer.
- **URL del frontal**: la dirección pública de GeoServer (por ejemplo,
  `https://midominio.es/geoserver`). A partir de ella se calculan la URI y las direcciones WMS, WFS,
  WCS, WMTS y de caché de los espacios de trabajo.
- **Usuario** y **Contraseña**: una cuenta de administración de GeoServer. gvSIG Online la usa
  para crear y borrar espacios de trabajo, almacenes, capas y estilos.
- **Por defecto**: el servidor que se propone al crear espacios de trabajo y en el que se crean los
  espacios de trabajo personales del personal. El primer servidor que se registra queda como
  servidor por defecto aunque no se marque. Al marcarlo en otro servidor, el anterior deja de serlo.
  Siempre tiene que haber uno: en el servidor por defecto la casilla aparece bloqueada; para
  cambiarlo, márquela en otro servidor.

### Pestaña Nodos

Cada nodo es una instancia de GeoServer con su **URL**, su **Estado** (activo, inactivo o error) y la marca
**¿Es maestro?**.

- Debe haber al menos un nodo y exactamente un nodo maestro; el formulario no deja guardar si no.
- gvSIG Online envía los cambios de configuración solo al nodo **maestro**. Después pide a los demás
  nodos que recarguen su configuración, para que todos sirvan lo mismo.
- El **Estado** es informativo: la recarga se pide a todos los nodos no maestros, sea cual sea su
  estado.
- Al modificar un servidor, el icono de recarga de cada nodo fuerza la recarga de ese nodo. Úselo
  si un nodo sirve datos desactualizados.

### Modificar un servidor

Al pulsar **Actualizar servidor** puede cambiar el título, la descripción, la URL del frontal, el
usuario, la contraseña, la marca **Por defecto** y los nodos.

- Si cambia la **URL del frontal**, se recalculan la URI y las direcciones de servicio de todos los
  espacios de trabajo del servidor.
- Los nodos se guardan de nuevo cada vez que se actualiza el servidor.

- Por seguridad, la **Contraseña** guardada no se muestra. Déjela en blanco para conservarla o
  escriba una nueva para cambiarla.

### Eliminar un servidor

**Eliminar servidor** pide confirmación y borra el servidor con todo lo que depende de él:

- En GeoServer, cada espacio de trabajo del servidor con todo su contenido y los estilos de sus
  capas.
- En gvSIG Online, los espacios de trabajo, sus almacenes de datos, sus capas y los nodos.

Los grupos de capas no se borran. Las tablas de la base de datos y los ficheros ráster tampoco. Si
GeoServer no puede borrar alguno de los espacios de trabajo, la operación se detiene con un error y
el servidor puede quedar eliminado solo en parte.

## Espacios de trabajo

![Formulario de espacio de trabajo](img/servidores-espacio-trabajo.png)

La lista muestra el nombre, la descripción, la URI, el servidor y si es público, con buscador y
paginación.

### Crear un espacio de trabajo

Pulse **Añadir espacio de trabajo**.

1. Elija el **Servidor**.
2. Escriba el **Nombre**. Debe empezar por una letra o un guion bajo y contener solo letras sin
   acentos, números y guiones bajos. No puede repetirse.
3. La **Uri** y las direcciones **WMS URL**, **WFS URL**, **WCS URL**, **WMTS URL** y **Caché URL**
   se rellenan solas a partir del servidor y del nombre. No se pueden escribir.
4. Opcionalmente, una **Descripción** y la marca **¿Público?**.

Al guardar se crea el espacio de trabajo en GeoServer. Si ya existe allí o GeoServer no responde,
aparece «Error: el workspace no puede ser creado».

### Modificar un espacio de trabajo

**Actualizar espacio de trabajo** permite cambiar la **Uri**, la **Descripción** y **¿Público?**. El
nombre y el servidor no se pueden cambiar. Estos cambios solo se guardan en gvSIG Online: no se
trasladan a GeoServer.

!!! note "¿Público?"
    Esta marca se guarda y se muestra en la lista, pero no cambia los permisos de las capas. Quién
    puede ver cada capa se decide en la propia capa (ver [Capas](capas.md)).

### Eliminar un espacio de trabajo

**Eliminar espacio de trabajo** pide confirmación y borra:

- En GeoServer, el espacio de trabajo con todos sus almacenes, capas y los estilos de sus capas.
- En gvSIG Online, sus almacenes de datos y sus capas.

Los esquemas y las tablas de la base de datos **no se borran**.

## Conexiones

![Formulario de conexión PostGIS](img/servidores-conexion-postgis.png)

La lista muestra el nombre, la descripción, el tipo, los permisos generales y, en las conexiones
PostGIS, cuántos almacenes de datos la usan (en el resto aparece **No compatible**).

En cada fila:

- **Opciones** (solo conexiones PostGIS y superusuarios): abre la configuración de la conexión,
  donde se definen los **Disparadores**: código SQL que se puede asignar a las capas para que se
  ejecute al insertar, modificar o borrar elementos.
- **Editar conexión** y **Eliminar conexión** (este último, solo superusuarios).

### Crear una conexión

Pulse **Añadir conexión**. La pestaña **Conexión** pide:

- **Nombre**: único; **no se puede cambiar después**.
- **Descripción** (opcional).
- **Categoría** y **Tipo**:
    - **Base de datos**: PostgreSQL/PostGIS, Oracle o SQL Server.
    - **API externa**: InDenova, SEGEX, SharePoint, Padrón ATM, SgaRexWS o Gestiona.
- Los **Parámetros de conexión** propios del tipo elegido. Para PostgreSQL/PostGIS: **Servidor**,
  **Puerto**, **Base de datos**, **Usuario**, **Contraseña** y, opcionalmente, **Parámetros
  adicionales (JSON)** que se pasan a GeoServer; por ejemplo, `jndiReferenceName` para que GeoServer
  use una conexión JNDI en lugar del usuario y la contraseña.

**Probar conexión** (solo superusuarios) comprueba que los datos son correctos sin guardar nada.

Solo las conexiones **PostgreSQL/PostGIS** sirven para crear almacenes de datos. Los demás tipos los
usan otras herramientas, como la ETL.

### Permisos de una conexión

En la pestaña **Permisos** (solo editable por superusuarios):

- **Permitir todos - Almacenes de datos**, **Permitir todos - ETL** y **Permitir todos - Gestión**:
  dan ese permiso a todos los usuarios.
- Para cada rol: **Almacenes de datos** (puede crear almacenes con esta conexión), **ETL** (puede
  usarla en la ETL) y **Gestión** (puede modificarla).

Si la crea un usuario del personal, los permisos quedan vacíos: solo él y los superusuarios pueden
usarla y modificarla.

Quien puede crear almacenes con una conexión pero no gestionarla solo puede usar su propio esquema
`ds_<usuario>` o crear uno nuevo; no puede elegir otros esquemas que ya existan.

### Modificar una conexión

El nombre y el tipo no se pueden cambiar. Si deja la contraseña vacía, se conserva la actual.

Al guardar una conexión PostGIS, gvSIG Online actualiza en GeoServer **todos los almacenes de datos
que la usan**. Si alguno no se puede actualizar, aparece un aviso con sus nombres.

### Eliminar una conexión

Si ningún almacén la usa, se pide una confirmación simple. Si la usan almacenes, el diálogo indica
cuántos almacenes y capas dependen de ella, y hay que marcar **Entiendo que esta acción no se puede
deshacer**. Al eliminarla se borran:

- Los almacenes de datos que la usan, en GeoServer y en gvSIG Online.
- Las capas de esos almacenes, con sus disparadores y reglas topológicas.
- Los disparadores definidos en la conexión.

Las tablas y los esquemas de la base de datos se conservan.

!!! warning "La conexión de la plataforma"
    No elimine la conexión que apunta a la base de datos de la propia plataforma: es la que se usa
    para crear los almacenes personales `ds_<usuario>` del personal.

## Almacenes de datos

La lista muestra el nombre, la descripción, el tipo y la conexión (o los parámetros, con las
contraseñas ocultas, en los almacenes antiguos que no usan una conexión), con buscador y paginación.

### Crear un almacén de datos

![Nuevo almacén PostGIS](img/servidores-almacen-postgis.png)

Pulse **Añadir almacén de datos**. En la pestaña **Almacén de datos**:

- **Espacio de trabajo**, **Tipo** y **Nombre**: **no se pueden cambiar después**. El nombre debe
  ir en minúsculas, empezar por una letra o un guion bajo y contener solo letras, números y guiones
  bajos. No puede existir ya otro almacén con ese nombre en el mismo espacio de trabajo.
- **Descripción** (opcional).

El resto de campos depende del **Tipo**:

| Tipo | Qué es | Qué se pide |
|---|---|---|
| **PostGIS vectorial** | Un esquema de una base de datos PostgreSQL/PostGIS | **Conexión** y **Esquema**. Elija un esquema existente o escriba un nombre nuevo, que aparece con «(nuevo)»; el esquema se crea en la base de datos al guardar |
| **GeoTiff** | Un fichero ráster | **Seleccionar archivo** abre el [gestor de archivos](gestor-archivos.md). El fichero debe estar georreferenciado; si no, aparece «Error: El GeoTIFF especificado no está georreferenciado» |
| **Mosaico de Imágenes** | Una carpeta de imágenes ráster que GeoServer sirve como una sola capa | **Seleccionar archivo** para elegir la carpeta. Opcionalmente, **Dimensión temporal**: una expresión regular que extrae la fecha del nombre de cada fichero (por defecto `(?<=_)[0-9]{8}`) y su formato (por defecto `yyyyMMdd`) |
| **WMS en cascada** | Un servicio WMS remoto que GeoServer vuelve a publicar | **Parámetros de conexión** en JSON: `url` (dirección de *GetCapabilities*) y, si el servicio lo pide, `username` y `password`. **Probar conexión** comprueba el acceso |

Al guardar se crea el almacén en GeoServer y, después, en gvSIG Online.

### Permisos de un almacén de datos

En la pestaña **Permisos**:

- **Permitir todos - Uso**: todo el personal puede publicar capas en este almacén.
- **Permitir todos - Gestión**: todo el personal puede modificarlo y eliminarlo.
- Para cada rol: **Puede usar** y **Gestión**, con el mismo significado.

Solo los superusuarios y quien creó el almacén pueden cambiar estos permisos. Si los cambia otra
persona con permiso de gestión, se guardan el resto de cambios pero no los permisos.

### Modificar un almacén de datos

El espacio de trabajo, el tipo y el nombre aparecen bloqueados. Los cambios afectan a todas las
capas publicadas desde el almacén.

- **Almacenes PostGIS con conexión**: solo se puede cambiar la descripción y los permisos. La
  conexión y el esquema se muestran como información; para cambiar los datos de acceso, edite la
  conexión con el enlace que aparece.
- **Almacenes sin conexión** (WMS en cascada, mosaicos y almacenes PostGIS antiguos): se pueden
  editar los **Parámetros de conexión**. Las contraseñas aparecen como `****`; déjelas así para
  conservarlas.
- Los almacenes **GeoTiff** no se pueden modificar: elimínelo y créelo de nuevo.

### Eliminar un almacén de datos

![Eliminar un almacén de datos](img/servidores-eliminar-almacen.png)

**Eliminar almacén de datos** pide confirmación y borra:

- El almacén en GeoServer, con sus capas, y los estilos de esas capas.
- En gvSIG Online, el almacén y sus capas, con los disparadores y reglas topológicas de las capas.
- En los mosaicos, el índice del mosaico y los ficheros que GeoServer generó en la carpeta. Las
  imágenes se conservan.

En los almacenes PostGIS, la casilla **Marque esta opción para eliminar el esquema asociado al
almacén de datos** borra además **el esquema y todas sus tablas** de la base de datos. Si no la
marca, los datos se conservan. No se puede borrar:

- el esquema `public`, que está protegido;
- un esquema que usa también otro almacén de la misma base de datos. El aviso indica cuáles lo
  usan; desmarque la casilla para eliminar solo este almacén. Al eliminar un espacio de trabajo
  con sus datos, ese esquema se conserva hasta que se borra el último almacén que lo usa.
