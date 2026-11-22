# Gestor de archivos

El **gestor de archivos** es el espacio de ficheros del servidor: en él se suben los datos
(shapefiles, GeoPackage, GeoTIFF, hojas de cálculo, ZIP…) que después se cargan en la base de datos
o se publican como capas. Se organiza en carpetas, una por rol de usuario.

Se abre desde el panel de administración, en **Administrador de archivos**.

## Quién puede hacer qué

| Acción | Quién |
|---|---|
| Abrir el gestor | Personal (*staff*) y superusuarios |
| Ver carpetas y ficheros | Los superusuarios ven todo. El resto solo ve, en la carpeta principal, las carpetas con el nombre de alguno de sus roles, y todo lo que contienen |
| Subir, crear carpetas, renombrar, mover, copiar, descomprimir, descargar y enviar a la papelera | Dentro de las carpetas de sus roles: el personal con ese rol. En cualquier sitio: los superusuarios |
| Crear, renombrar, mover o borrar las carpetas de rol (las de la carpeta principal) y escribir en la carpeta principal | Solo superusuarios |
| Ver, restaurar y borrar definitivamente lo que hay en la papelera | Los superusuarios, todo. El resto, lo que proceda de carpetas que puede gestionar |
| Consultar el **Histórico de exportaciones** | Cada usuario ve sus exportaciones; los superusuarios, las de todos |

!!! note "Carpetas de rol"
    Cuando un usuario pasa a ser personal, se crea su rol principal y, con él, una carpeta con el
    nombre de ese rol en el gestor. Para compartir ficheros entre varias personas, use la carpeta de
    un rol que tengan todas ellas (ver [Usuarios, grupos y roles](usuarios.md)).

!!! warning "Borrar un rol borra su carpeta"
    Al eliminar un rol se elimina también su carpeta del gestor **con todo su contenido**, sin pasar
    por la papelera.

## Dos interfaces

El gestor tiene dos interfaces: la **actual**, tipo explorador, y la **clásica**, una lista con
acciones por fila. La que se usa la decide la configuración de la instalación; los usuarios no
pueden cambiarla. Lo que sigue describe la interfaz actual; la clásica se resume al final, en
[Interfaz clásica](#interfaz-clasica).

## La ventana del explorador

![Gestor de archivos con el árbol de carpetas, la lista y el panel de detalles](img/gestor-archivos-explorador.png)

- **Carpetas** (a la izquierda): el árbol de carpetas, con la **Papelera** al final. El botón
    **Mostrar u ocultar el árbol de carpetas** lo pliega.
- **Lista** (en el centro): las carpetas y ficheros de la carpeta abierta, con **Nombre**,
    **Tamaño** y **Modificado**. Pulse una cabecera para ordenar por ella. Encima, la ruta (empieza en
    *data*) permite volver a cualquier carpeta superior.
- **Detalles** (a la derecha): el tipo, el tamaño, la ruta y las acciones del elemento
    seleccionado. Con varios seleccionados muestra cuántos ficheros y carpetas son y su **Tamaño
    total**. El botón **Mostrar u ocultar el panel de detalles** lo pliega.
- **Filtrar esta carpeta**: busca por nombre dentro de la carpeta abierta.

Para trabajar con varios elementos, márquelos con su casilla (o con **Seleccionar todos**). Las
acciones aparecen en la barra de selección, en el panel de detalles, en **Más acciones** (⋯) de
cada fila y con el botón derecho del ratón.

Algunas marcas de la lista:

- **+N asociados**: un shapefile se muestra como una sola fila. Sus ficheros asociados (.dbf, .shx,
    .prj…) se mueven, copian, renombran y borran con él.
- **En uso**: el fichero o carpeta lo usa un almacén de datos ráster (GeoTIFF o mosaico). Mientras
    lo use una capa no se puede mover, renombrar ni enviar a la papelera.
- **Puedes ver esta carpeta pero no modificarla**: aparece, por ejemplo, en la carpeta principal
    para quien no es superusuario.

Atajos de teclado: **Supr** envía a la papelera, **F2** renombra, **Intro** abre una carpeta o
descarga un fichero, **Ctrl+A** selecciona todo y **Esc** quita la selección.

## Subir ficheros

Pulse **Subir** y elija **Subir ficheros** o **Subir carpeta** (sube la carpeta entera, con sus
subcarpetas). También puede arrastrar ficheros o carpetas desde el ordenador y soltarlos sobre la
lista o sobre una carpeta del árbol.

![Panel de subidas con el progreso de cada fichero](img/gestor-archivos-subidas.png)

- El panel **Subidas**, abajo a la derecha, muestra el avance de cada fichero.
- En los nombres, los espacios se cambian por guiones bajos y se quitan los caracteres especiales.
- Si se corta la conexión, la subida se reanuda desde donde se quedó (**Se cortó al N %. Se
    reanudará desde ahí.**). Si falla del todo, pulse **Reintentar**.
- Si ya existe un fichero con el mismo nombre, el gestor pregunta qué hacer:
    - **Conservar los dos**: el nuevo se guarda con un nombre numerado (_1, _2…).
    - **Reemplazar**: el fichero actual se sustituye por el nuevo. No se puede reemplazar un fichero
    **En uso**.
    - **Omitir**: ese fichero no se sube.

    Marque **Hacer lo mismo con los demás ficheros repetidos** para no responder fichero a fichero,
    o pulse **Cancelar las subidas que faltan**.

### Límites

| Límite | Valor por defecto |
|---|---|
| Tamaño máximo de cada fichero subido | 50 GB (configurable en la instalación). Además, debe haber espacio libre suficiente en el disco |
| Tamaño descomprimido de un ZIP | 20 GB |
| Número de entradas de un ZIP | 200.000 |
| Tamaño de una descarga como ZIP | 10 GB |
| Días que se guarda lo enviado a la papelera | 30 |

No hay restricción por tipo de fichero.

### Subidas en segundo plano

Las subidas se hacen desde la página del gestor: si sale de ella, se detienen. Para seguir usando
gvSIG Online mientras se suben ficheros grandes, páselas a la ventana **Subidas y procesos**:

- Pulse **Continuar en segundo plano** en el panel de subidas, o
- al salir del gestor con subidas en curso, elija **Seguir en segundo plano e ir** (también puede
    **Quedarme aquí** o **Salir y detenerlas**).

La ventana se abre aparte, pequeña, en la esquina de la pantalla. Si el navegador la bloquea,
permita las ventanas emergentes para el sitio y vuelva a intentarlo. También se abre con el botón
**Subidas y procesos** (icono de nube) de la barra del gestor.

![Ventana Subidas y procesos](img/gestor-archivos-ventana-procesos.png)

La ventana tiene tres apartados:

- **En curso y recientes**: lo que se está subiendo desde esta ventana.
- **En pausa**: subidas que se interrumpieron (por ejemplo, al cerrar la ventana). Pulse **Elegir
    el fichero** y seleccione el mismo fichero para continuar donde se quedó, o **Descartar** para
    borrar lo recibido. Las subidas que pasan 24 horas sin recibir datos se descartan solas.
- **Tareas en el servidor**: las descompresiones en segundo plano, aunque se lanzaran desde otra
    página.

Mientras haya subidas en curso, no cierre esta ventana: si se cierra, se pausan. Cuando todo
termina bien, se cierra sola a los 10 segundos, salvo que pulse **Mantener abierta**.

## Organizar ficheros y carpetas

- **Nueva carpeta**: crea una carpeta dentro de la abierta.
- **Renombrar**: cambia el nombre. Al renombrar un shapefile también se renombran sus ficheros
    asociados.
- **Mover a…** y **Copiar a…**: piden la carpeta de destino. También puede mover arrastrando las
    filas sobre una carpeta. Si en el destino ya hay elementos con el mismo nombre, al mover se ofrece
    **Conservar los dos (nombre numerado)**; al copiar, la copia recibe directamente un nombre
    numerado. No se puede mover ni copiar una carpeta dentro de sí misma.
- **Descomprimir aquí** (ficheros ZIP): extrae el contenido en una carpeta nueva con el nombre del
    ZIP (o con un nombre numerado si ya existe). Los ZIP de más de 100 MB se descomprimen en el
    servidor en segundo plano, y su avance se ve en **Subidas y procesos**.
- **Descarga**: un fichero se descarga tal cual. Varios elementos o una carpeta se descargan
    como un ZIP (**Descargar como zip**).

Tras mover o enviar a la papelera, el aviso que aparece abajo ofrece **Deshacer**.

## Papelera

**Enviar a la papelera** no borra nada todavía: el elemento se guarda en la **Papelera** durante
30 días, y después se borra definitivamente. Un shapefile entra con todos sus ficheros asociados.

![Papelera del gestor de archivos](img/gestor-archivos-papelera.png)

Abra la papelera desde el árbol de carpetas o desde **Más acciones**. Para cada elemento se ve la
**Ubicación original**, quién lo borró, cuándo, y cuántos días quedan. Puede:

- **Restaurar**: lo devuelve a su carpeta original. Necesita poder escribir en esa carpeta.
- **Borrar definitivamente**: lo elimina sin esperar. **No se puede deshacer.**
- **Vaciar papelera**: borra definitivamente todo lo que usted ve en la papelera.

## Cargar ficheros en la base de datos y publicarlos

Desde el gestor, los ficheros vectoriales se cargan en una tabla de PostGIS y, si se quiere, se
publican como capa en el mismo paso.

- **Exportar a base de datos**: para shapefiles (.shp o .dbf) y GeoPackage (.gpkg).
- **Aplicar transformación**: para ficheros CSV y XLSX. Solo aparece si está instalado el plugin
    de ETL.

![Formulario Exportar a base de datos](img/gestor-archivos-exportar.png)

El formulario **Exportar a base de datos** pide:

- **GeoPackage layer** (solo GeoPackage; el texto aparece sin traducir): la capa del fichero que se carga. Cada exportación
    carga una sola capa.
- **Modo de creación de tabla**: **Crear**, **Añadir** (a una tabla existente) o **Sobrescribir**.
- **Almacén de datos**: el esquema de PostGIS de destino. Los superusuarios ven todos los almacenes
    PostGIS; el resto, los que creó, su almacén por defecto, los que algún rol suyo puede usar y los
    abiertos a todos (ver [Servidores y almacenes de datos](servidores.md)).
- **Nombre**: el nombre de la tabla.
- **Codificación de caracteres** y **Sistema de referencia de coordenadas** del fichero.
- **Conservar estructura de tabla** (al sobrescribir): **Conservar la estructura de tabla (modo
    'truncate')** o **Eliminar y recrear la tabla**.
- **Columna de clave primaria** y **Valores de clave primaria** (conservar o no los del fichero).
- **Publicar la capa tras exportar**: publica la tabla como capa, con el **Título** y el **Grupo
    de capas** que indique. La capa se crea apagada en el visor y consultable. Si ya existe una capa
    con ese nombre en el almacén, no se vuelve a publicar.

!!! warning "Nombres de columnas"
    Los nombres de las columnas solo pueden tener letras sin acentos, números y guiones bajos, y no
    pueden empezar por un número. Si el fichero tiene otros nombres, el formulario lo avisa y no se
    puede exportar hasta corregirlos.

Pulse **Exportar**. La carga se hace en segundo plano y se abre el **Histórico de exportaciones**,
con el **Estado**, el **Archivo**, el **Tiempo**, el **Mensaje** y el **Usuario** de cada
exportación, y una barra de progreso mientras se ejecuta. Si una falla, **Probar de nuevo** vuelve
al formulario. Se guardan las 20 últimas exportaciones de cada usuario.

Para publicar capas por otras vías, y para el resto de opciones de la capa, vea
[Capas](capas.md).

### El gestor como selector de ficheros

Otras pantallas abren el gestor en una ventana para elegir un fichero o una carpeta: la
publicación de capas ráster y de mosaicos, los almacenes de datos de tipo GeoTIFF o mosaico, y las
atribuciones. En esa ventana, haga doble clic en el fichero (o márquelo y pulse **Seleccionar**).
Si la pantalla pide una carpeta, márquela o ábrala y pulse **Seleccionar**. Cuando la pantalla solo
admite ciertos tipos, se indica con **Solo se muestran:** y la lista de extensiones.

## Interfaz clásica

Si la instalación usa la interfaz clásica, el gestor es una lista de la carpeta abierta con los
botones **Crear directorio**, **Subir** e **Histórico de exportaciones**. Cada fila tiene un menú
de acciones con **Exportar a base de datos**, **Aplicar transformación**, **Descomprimir fichero**,
**Eliminar archivo** o **Eliminar directorio**. Pulse el nombre de un fichero para descargarlo.

!!! warning "En la interfaz clásica no hay papelera"
    **Eliminar archivo** y **Eliminar directorio** borran definitivamente, con todo el contenido de
    la carpeta. Lo que usa un almacén de datos no se puede borrar.
