# Introducción

Esta guía explica cómo administrar gvSIG Online desde su **panel de administración**: los
proyectos (visores de mapas), las capas y su simbología, los servidores de mapas, los usuarios y
sus permisos, el gestor de archivos y las estadísticas de uso.

Está pensada para las personas que gestionan la plataforma, no para programadores. Cada página
describe un apartado del menú lateral del panel.

## Cómo se entra en el panel

1. Abra la dirección de su instalación de gvSIG Online en el navegador e inicie sesión.
    - Si la instalación usa **Keycloak**, el inicio de sesión se hace en la página de Keycloak, y
     al terminar vuelve a gvSIG Online.
    - Si no, gvSIG Online muestra su propio formulario: escriba el **Nombre de usuario** y la
     **Contraseña** y pulse **Iniciar sesión**.
2. Tras iniciar sesión se abre la página **Inicio**, con los proyectos, cuadros de mando y
   aplicaciones a los que tiene acceso. Desde cualquier página del panel se vuelve a ella con
   **Inicio**, la primera opción del menú lateral.

![Página Inicio del panel con el menú lateral](img/introduccion-inicio.png)

En la barra superior del panel están:

- El icono **?**, que abre la documentación (esta guía y los manuales de los plugins) en una
  pestaña nueva.
- El selector de idioma.
- Su nombre de usuario. Al pulsarlo se muestra su correo y el botón **Cerrar sesión**.

En la página **Inicio**, junto a su nombre, una etiqueta indica su perfil: **Administrador**
(superusuario), **Gestor** (personal) o **Usuario**. Desde **Detalles** puede, si la instalación lo
permite, **Cambiar contraseña**.

## Quién ve el panel

Cualquier usuario con sesión iniciada llega a la página **Inicio**, pero los apartados de
administración del menú lateral solo aparecen para dos perfiles:

| Perfil | Etiqueta en Inicio | Qué puede hacer |
|---|---|---|
| **Superusuario** | **Administrador** | Todo: además de lo que hace el personal, gestiona usuarios y roles, servidores, espacios de trabajo, atribuciones, URLs de los servicios y estadísticas. Ve todos los proyectos |
| **Personal** (*staff*) | **Gestor** | Crea y gestiona proyectos, grupos de capas, capas, estilos, almacenes de datos y archivos. En general, solo ve y modifica lo que ha creado o aquello sobre lo que alguno de sus roles tiene permiso |
| **Usuario** | **Usuario** | No ve los apartados de administración. Abre los proyectos a los que le dan acceso sus roles y los proyectos públicos |

Todo superusuario es también personal.

Si alguien sin el perfil necesario abre directamente la dirección de una página del panel, se
muestra la página **Operación no permitida**.

### Cómo se obtiene cada perfil

Depende de cómo esté configurada la autenticación de la instalación:

- **Usuarios gestionados en gvSIG Online** (sin Keycloak): un superusuario marca, en el formulario
  del usuario, **Es superusuario** o **Puede gestionar proyectos** (personal). Ver
  [Usuarios, grupos y roles](usuarios.md).
- **Keycloak**: el perfil lo deciden dos roles del *realm* de Keycloak. Por defecto se llaman
  `GVSIGOL_DJANGO_SUPERUSER` (superusuario) y `GVSIGOL_DJANGO_STAFF` (personal); la instalación
  puede usar otros nombres. gvSIG Online lee esos roles cada vez que el usuario inicia sesión y
  actualiza su perfil, así que un cambio hecho en Keycloak se aplica en el siguiente inicio de
  sesión. Las casillas del formulario de usuario de gvSIG Online también asignan o quitan esos
  roles en Keycloak.

Al dar a un usuario el perfil de personal o de superusuario, gvSIG Online le prepara además su
espacio de trabajo propio (ver [Rol principal y espacio de trabajo
propio](usuarios.md#rol-principal-y-espacio-de-trabajo-propio)).

## El menú lateral

El menú lateral agrupa los apartados de administración. Algunas opciones solo se muestran a los
superusuarios, y otras dependen de la configuración de la instalación.

| Menú | Opción | Quién la ve | Página de la guía |
|---|---|---|---|
| **Gestión de usuarios** | **Usuarios**, **Roles** | Superusuarios | [Usuarios, grupos y roles](usuarios.md) |
| **Servicios** | **Servidores**, **Espacios de trabajo** | Superusuarios | [Servidores](servidores.md) |
| | **Conexiones**, **Almacenes de datos** | Personal | [Servidores](servidores.md) |
| | **Grupos de capas** | Personal | [Grupos de capas](grupos-capas.md) |
| | **Capas** | Personal | [Capas](capas.md) |
| | **Capas externas** | Personal | [Capas externas](capas-externas.md) |
| | **Gestión de la caché**, **Vistas SQL** | Personal | [Otras herramientas de servicios](servicios-avanzados.md) |
| | **Atribuciones**, **URLs de los servicios** | Superusuarios | [Otras herramientas de servicios](servicios-avanzados.md) |
| **Tipos de datos** | **Enumeraciones** | Personal, si la instalación las tiene activadas | [Otras herramientas de servicios](servicios-avanzados.md) |
| **Administrador de archivos** | | Personal | [Gestor de archivos](gestor-archivos.md) |
| **Simbología** | **Estilos de capa** | Personal | [Simbología](simbologia.md) |
| | **Bibliotecas de símbolos**, **Rampas de color** | Personal | [Simbología](simbologia.md) |
| **Proyectos** | **Proyectos** | Personal | [Proyectos](proyectos.md) |
| | **Vistas compartidas** | Personal | [Vistas compartidas y aplicaciones](vistas-compartidas.md) |
| **Aplicaciones** | | Personal | [Vistas compartidas y aplicaciones](vistas-compartidas.md#aplicaciones) |
| **Plugins** | Una opción por plugin | Según el plugin | Manual de cada plugin |
| **Estadísticas** | | Superusuarios | [Estadísticas](estadisticas.md) |

- **Gestión de usuarios** puede no aparecer si la instalación gestiona los usuarios fuera de gvSIG
  Online.
- **Plugins** reúne las opciones que añaden los plugins instalados; cada plugin decide a quién se
  la muestra. **Estadísticas** va siempre al final del menú.
- El menú se puede plegar con el botón de la barra superior; el panel recuerda la preferencia en
  ese navegador.

## Conceptos básicos

Estos términos se repiten en toda la guía.

### Proyecto

Un visor de mapas: reúne unos grupos de capas, las herramientas del visor, las capas base y los
permisos de quién puede abrirlo y gestionarlo. Ver [Proyectos](proyectos.md).

### Grupo de capas

Un conjunto de capas que se muestran juntas en la tabla de contenidos del visor. Los proyectos no
incluyen capas sueltas, sino grupos de capas; un mismo grupo puede formar parte de varios
proyectos. Ver [Grupos de capas](grupos-capas.md).

### Capa

Un conjunto de datos geográficos publicado en el servidor de mapas (GeoServer), con su estilo y
sus permisos de lectura, escritura y gestión. Cada capa pertenece a un único grupo de capas y sus
datos están en un almacén de datos. Las capas externas, en cambio, muestran servicios de otros
servidores (WMS, WMTS…). Ver [Capas](capas.md) y [Capas externas](capas-externas.md).

### Espacio de trabajo

Una división del servidor de mapas que agrupa almacenes de datos y capas, y les da sus direcciones
de servicio (WMS, WFS, WCS, WMTS). Crear un espacio de trabajo en gvSIG Online lo crea también en
GeoServer. Ver [Servidores](servidores.md).

### Almacén de datos

El origen de los datos de las capas dentro de un espacio de trabajo: por ejemplo, un esquema de una
base de datos PostGIS o un fichero GeoTIFF. Ver [Servidores](servidores.md).

### Rol

Un nombre al que se asignan usuarios y permisos. Los permisos de proyectos, grupos de capas, capas
y almacenes de datos no se dan a usuarios concretos, sino a roles: un usuario tiene los permisos de
todos sus roles. Ver [Roles](usuarios.md#roles).
