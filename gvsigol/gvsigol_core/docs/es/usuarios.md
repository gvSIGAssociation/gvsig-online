# Usuarios, grupos y roles

gvSIG Online da acceso a sus proyectos y capas mediante **roles**: los permisos se conceden a un
rol, y cada usuario tiene los permisos de todos los roles que tiene asignados.

Los usuarios y los roles se gestionan desde el panel de administración, en **Gestión de usuarios**,
con dos opciones: **Usuarios** y **Roles**.

Dónde se guardan realmente los usuarios y los roles depende de la autenticación de la instalación
(ver [Según la autenticación de la instalación](#segun-la-autenticacion-de-la-instalacion)): en la
propia base de datos de gvSIG Online o en Keycloak. Las pantallas son las mismas en ambos casos.

## Quién puede hacer qué

| Acción | Quién |
|---|---|
| Ver el menú **Gestión de usuarios** | Solo superusuarios |
| Ver, crear, modificar y eliminar usuarios | Solo superusuarios |
| Ver, crear y eliminar roles | Solo superusuarios |
| Dar permisos a un rol sobre un proyecto, grupo de capas o capa | Quien gestiona ese proyecto, grupo o capa, desde su propio formulario |
| Cambiar su propia contraseña | Cualquier usuario con sesión iniciada, desde **Inicio** (si la instalación lo permite) |

La instalación puede limitar estas pantallas:

- Si los usuarios se gestionan totalmente fuera de gvSIG Online, el menú **Gestión de usuarios** no
  aparece.
- Si los datos de los usuarios son **de solo lectura**, no se pueden crear ni eliminar usuarios
  (no aparecen **Añadir usuario** ni el botón de eliminar), y en el formulario del usuario solo se
  pueden cambiar el perfil y los roles.

## Usuarios

### Lista de usuarios

![Lista de usuarios](img/usuarios-lista.png)

La lista muestra, para cada usuario, el **Nombre de usuario**, el **Nombre**, los **Apellidos**, el
**Correo electrónico**, si **Es superusuario**, si **Gestiona proyectos** (es personal) y sus
**Roles**. El buscador filtra por cualquiera de esos datos, sin distinguir acentos, y la tabla se
pagina.

En cada fila:

- **Actualizar usuario**: abre el formulario del usuario.
- **Eliminar usuario**: pide confirmación y lo borra (ver
  [Eliminar un usuario](#eliminar-un-usuario)). No aparece en los usuarios que no son editables.

!!! note "Usuarios creados fuera de gvSIG Online"
    La lista se obtiene de una copia que gvSIG Online actualiza al crear o modificar usuarios desde
    el panel y, además, periódicamente (por defecto, cada 10 minutos). Un usuario creado
    directamente en Keycloak puede tardar ese tiempo en aparecer.

### Añadir un usuario

Pulse **Añadir usuario**. El formulario tiene las pestañas **General** y **Roles**, y en las
instalaciones con Keycloak, también **Grupos**.

![Formulario Añadir usuario](img/usuarios-anadir.png)

#### Pestaña General

**Datos personales** (todos obligatorios):

- **Nombre** y **Apellidos**.
- **Nombre de usuario**: el identificador con el que inicia sesión.
    - **No se puede cambiar después.**
    - Se guarda en minúsculas. Evite los espacios.
    - No puede repetirse: si ya existe, el formulario lo indica.
- **Correo electrónico**: se guarda en minúsculas. Con Keycloak, no puede haber dos usuarios con
  el mismo correo; si ya existe, se muestra **Ya existe un usuario con esta dirección de correo
  electrónico.**

**Contraseña** y **Repetir contraseña**. La contraseña debe tener al menos 8 caracteres, no ser
solo números, no parecerse al nombre de usuario, al nombre ni al correo, y no ser una contraseña
habitual (como *12345678* o *qwerty*). El formulario va marcando qué condiciones se cumplen.

Si la instalación valida las contraseñas contra un directorio corporativo (Active Directory), estos
campos no aparecen: **La contraseña la gestiona el directorio corporativo.**

**Permisos**:

- **Es superusuario**: **Acceso completo a la administración.** Un superusuario es también
  personal, aunque no se marque la casilla siguiente.
- **Puede gestionar proyectos**: el usuario es personal (*staff*) y ve el panel de administración.
  **Puede crear y editar proyectos.**

Ver qué puede hacer cada perfil en [Quién ve el panel](introduccion.md#quien-ve-el-panel).

#### Pestaña Roles

![Pestaña Roles del usuario](img/usuarios-pestana-roles.png)

Marque **Asignar rol** en cada rol que deba tener el usuario. El cuadro **Filtrar roles por nombre o
descripción** acota la lista. Los roles de sistema (los que gvSIG Online usa internamente para
los superusuarios y el personal) no aparecen: se asignan solos con las casillas de **Permisos**.

#### Pestaña Grupos

Solo aparece con Keycloak. Marque **Asignar grupo** en los grupos de Keycloak a los que deba
pertenecer el usuario (ver [Grupos](#grupos)).

#### Al guardar

Pulse **Guardar**. Además de crear el usuario:

- Si es personal o superusuario, se le prepara su espacio de trabajo propio (ver
  [Rol principal y espacio de trabajo propio](#rol-principal-y-espacio-de-trabajo-propio)).
- Si la instalación tiene configurado el envío de correo, el usuario recibe un mensaje **Nueva
  cuenta de usuario** con sus datos de acceso, **incluida la contraseña**.

Si algo falla, el formulario se queda abierto con el error y con los roles y grupos que había
marcado, y gvSIG Online deshace lo que hubiera llegado a crear.

### Modificar un usuario

Pulse **Actualizar usuario** en la fila del usuario. El formulario es el de alta, con estas
diferencias:

- El **Nombre de usuario** se muestra, pero **No se puede cambiar.**
- No hay campos de contraseña: cada usuario cambia la suya (ver
  [Contraseñas](#contrasenas)).
- No hay pestaña **Grupos**: los grupos se cambian en Keycloak.
- Si los datos personales son de solo lectura en la instalación, **Nombre**, **Apellidos** y
  **Correo electrónico** no se pueden editar, pero sí los **Permisos** y los **Roles**.

En la pestaña **Roles** aparecen marcados los roles asignados directamente al usuario. Lo que
marque o desmarque sustituye a los roles que tenía.

Pulse **Guardar** para aplicar los cambios. Si el usuario pasa a ser personal o superusuario, se le
prepara su espacio de trabajo propio si aún no lo tenía.

Con Keycloak, si el usuario tiene la sesión abierta, sus nuevos roles pueden no tenerse en cuenta
hasta que vuelva a iniciar sesión.

!!! note "Usuarios no editables"
    Algunas instalaciones sincronizan usuarios desde un sistema externo y los marcan como no
    editables. En esos usuarios el formulario muestra **El usuario no es editable**, todos los
    campos están bloqueados y no se pueden eliminar. Del mismo modo, los roles marcados como no
    editables aparecen bloqueados en la pestaña **Roles** (**El rol no es editable**): al guardar
    el usuario se conservan tal como estaban. Tampoco tienen botón de eliminar en la lista de
    roles.

### Eliminar un usuario

Pulse **Eliminar usuario** en su fila y confirme con **Aceptar**.

- Se borra la cuenta: con Keycloak, también en Keycloak; si la instalación usa un directorio LDAP
  gestionado por gvSIG Online, también en el directorio.
- No se borran su espacio de trabajo, su almacén de datos ni su rol principal, ni los proyectos,
  capas o archivos que haya creado.

## Rol principal y espacio de trabajo propio

Cuando un usuario pasa a ser personal o superusuario (al crearlo, al modificarlo o, con Keycloak,
al iniciar sesión con el rol de personal), gvSIG Online le prepara:

- Un **rol principal**, solo para él, y se lo asigna. Se llama `ug_<usuario>`, o
  `ROLE_UG_<USUARIO>` con Keycloak.
- Una carpeta con el nombre de ese rol en el [Gestor de archivos](gestor-archivos.md).
- Un **espacio de trabajo** (`ws_<usuario>`) en el servidor de mapas por defecto y, dentro de él, un
  **almacén de datos** (`ds_<usuario>`), donde puede publicar sus capas.

En los nombres del espacio de trabajo y del almacén, los caracteres que no son letras ni números se
cambian por guiones bajos, y la arroba por `_at_`.

El rol principal recibe siempre permiso de acceso y de gestión sobre los proyectos que crea el
usuario (ver [Crear un proyecto](proyectos.md#crear-un-proyecto)).

## Roles

Un rol es un nombre al que se asignan usuarios y permisos. Por ejemplo, un rol `tecnicos_urbanismo`
puede tener acceso a un proyecto de planeamiento y permiso de escritura en sus capas; basta con
asignar el rol a cada técnico para que los tenga.

### Lista de roles

![Lista de roles](img/usuarios-roles-lista.png)

Muestra el identificador, el **Nombre** y la **Descripción** de cada rol, con un buscador. Incluye
también los roles de sistema y, con Keycloak, todos los roles del *realm*.

### Añadir un rol

Pulse **Añadir rol**.

![Formulario Añadir rol](img/usuarios-anadir-rol.png)

- **Nombre** (obligatorio): debe empezar por una letra o un guion bajo, y después llevar solo
  letras sin acentos, números o guiones bajos. El nombre `admin` está reservado.
- **Descripción** (opcional): ayuda a reconocer el rol en las listas de permisos.

Pulse **Guardar**. Un rol **no se puede modificar ni renombrar después**; para cambiarlo hay que
eliminarlo y crear otro.

Después de crearlo:

1. Asígnelo a los usuarios desde la pestaña **Roles** de cada usuario.
2. Dele permisos sobre proyectos, grupos de capas y capas desde sus formularios (ver
   [Cómo se usan los roles](#como-se-usan-los-roles)).

### Eliminar un rol

Pulse el botón de eliminar en su fila y confirme con **Aceptar**.

!!! warning "Qué se borra con el rol"
    - El rol desaparece de todos los usuarios que lo tenían.
    - Se quitan todos sus permisos: sobre proyectos, aplicaciones, grupos de capas, capas
      (lectura, escritura y gestión), almacenes de datos, conexiones y disparadores. Si más
      adelante se crea un rol con el mismo nombre, empieza sin permisos.
    - **Se borra la carpeta del rol en el Gestor de archivos, con todo su contenido.**

Los roles de sistema no se pueden eliminar: se muestra **Los roles de sistema no se pueden
eliminar**. Si el servidor de autenticación no permite borrarlo, se muestra **No se ha podido
eliminar el rol** y no se toca nada.

### Cómo se usan los roles

Los permisos nunca se dan a un usuario concreto, sino a sus roles:

| Dónde | Permisos por rol |
|---|---|
| [Proyectos](proyectos.md#pestana-permisos) | **Permiso de acceso** (abrir el proyecto) y **Permiso de gestión** (modificarlo, exportarlo y eliminarlo) |
| [Grupos de capas](grupos-capas.md) | Gestionar el grupo e incluirlo en proyectos |
| [Capas](capas.md) | Lectura (ver la capa), escritura (editar sus datos) y gestión |
| [Servidores](servidores.md) | Usar una conexión o un almacén de datos compartido |

Un proyecto o una capa **públicos** no necesitan permisos de lectura: cualquiera puede verlos. Los
superusuarios no necesitan roles para administrar nada.

Los permisos de lectura y escritura de las capas se trasladan a GeoServer como reglas por rol, de
modo que se respetan también al acceder a los servicios WMS y WFS.

## Grupos

Los grupos solo existen en las instalaciones con Keycloak, y se crean y gestionan en Keycloak. En
gvSIG Online solo se pueden asignar al crear un usuario, en la pestaña **Grupos**.

Los permisos de proyectos y capas de gvSIG Online van siempre por roles, no por grupos. Si en
Keycloak un grupo lleva roles asociados, sus miembros reciben esos roles, aunque en la pestaña
**Roles** del usuario no aparezcan marcados.

## Contraseñas

Cada usuario cambia su propia contraseña desde **Inicio**: pulse **Detalles** junto a su nombre y
después **Cambiar contraseña**. Según la instalación:

- Se muestra un formulario con **Nueva contraseña** y **Repetir nueva contraseña**. Al pulsar
  **Actualizar contraseña** se cierra la sesión y hay que entrar con la nueva.
- O se abre la página de gestión de cuentas de Keycloak u otro sistema externo.
- Con un directorio corporativo (Active Directory), la opción no aparece.

En el formulario de inicio de sesión propio de gvSIG Online, **He olvidado mi contraseña** pide el
nombre de usuario y envía al correo del usuario un enlace para elegir una contraseña nueva. Para
ello, la instalación debe tener configurado el envío de correo.

Un superusuario no puede cambiar desde el panel la contraseña de otro usuario. Con Keycloak, puede
hacerlo en la consola de administración de Keycloak.

## Según la autenticación de la instalación

| | Sin Keycloak (usuarios de gvSIG Online) | Con Keycloak |
|---|---|---|
| Dónde se guardan usuarios y roles | En la base de datos de gvSIG Online (y, si está activado, también en un directorio LDAP) | En el *realm* de Keycloak. gvSIG Online los crea, modifica y borra allí |
| Inicio de sesión | Formulario de gvSIG Online | Página de Keycloak |
| Perfil de superusuario y personal | Casillas del formulario de usuario | Roles `GVSIGOL_DJANGO_SUPERUSER` y `GVSIGOL_DJANGO_STAFF` (nombres por defecto). Las casillas del formulario los asignan; también se pueden asignar en Keycloak, y gvSIG Online los lee al iniciar sesión |
| Rol de los superusuarios | `admin` | `GVSIGOL_DJANGO_SUPERUSER` y `ADMIN` |
| Grupos | No hay | Grupos de Keycloak |
| Usuarios creados fuera del panel | — | Los creados en Keycloak aparecen en la lista tras la siguiente actualización periódica, y pueden iniciar sesión directamente |

Con Keycloak, si el servidor de Keycloak no responde, el formulario del usuario muestra **El
servidor de autenticación no está disponible. Pruebe de nuevo más tarde o contacte a los
administradores del sistema**.

!!! note "Cambios hechos directamente en Keycloak"
    Lo que se cambie en la consola de Keycloak (roles, datos personales, usuarios nuevos) se ve en
    gvSIG Online sin hacer nada más; como mucho, hay que esperar a la siguiente actualización de
    la lista o a que el usuario vuelva a iniciar sesión.
