# Vistas compartidas y aplicaciones

Este capítulo trata dos apartados del panel de administración que no son proyectos, pero se
gestionan junto a ellos:

- Una **vista compartida** es un enlace a un proyecto que guarda cómo estaba el mapa al compartirlo:
    posición y zoom, capas encendidas, capa base… La crean los usuarios desde el visor y aquí se
    revisan y eliminan. Está en **Proyectos > Vistas compartidas**.
- Una **aplicación** es un enlace a otra aplicación web que se muestra en el portal junto a los
    proyectos, con su imagen, su título y sus permisos. Está en **Aplicaciones**.

## Quién puede hacer qué

| Acción | Quién |
|---|---|
| Crear una vista compartida | Cualquiera que pueda abrir el proyecto, desde el visor, si el proyecto tiene la herramienta de compartir vista. En proyectos públicos, también sin iniciar sesión |
| Ver la lista de vistas compartidas | Personal (*staff*) y superusuarios. La lista muestra las vistas de todos los usuarios, no solo las propias |
| Eliminar una vista compartida | Quien la creó y los superusuarios. En las vistas de otros, el botón aparece desactivado |
| Ver la lista de aplicaciones | Personal y superusuarios. Los superusuarios ven todas; el resto, las que creó |
| Crear una aplicación | Personal y superusuarios |
| Modificar una aplicación | Los superusuarios, cualquiera; el resto, las que creó |
| Eliminar una aplicación | Los superusuarios, cualquiera; el resto, las que creó |

## Vistas compartidas

### Cómo se crean

Las vistas se crean en el visor del proyecto con la herramienta **Compartir vista**, que debe estar
marcada en la pestaña **Herramientas** del proyecto (ver [Proyectos](proyectos.md)).

![Ventana Compartir vista del visor](img/vistas-compartidas-compartir.png)

En el visor actual:

1. Pulse **Compartir vista**.
2. Escriba una **Descripción** (opcional).
3. Si ha iniciado sesión, puede activar **No expira** (*El enlace compartido no caduca*).
4. Pulse **Generar enlace** y, después, **Copiar enlace**.

En el visor clásico, la opción **Compartir vista** está en el menú de herramientas. La casilla
equivalente es **Marque para que la URL no expire**, y los botones, **Guardar URL** y **Copiar
URL**.

El enlace guarda el estado del mapa en ese momento: el centro y el zoom, las capas y cuáles estaban
encendidas, la capa base y el estado del panel lateral.

### Caducidad

- Si no se marca **No expira**, la vista caduca **al día siguiente** de crearla.
- Si se marca, no caduca nunca.
- Quien comparte sin haber iniciado sesión (en un proyecto público) no puede elegir: su vista
    siempre caduca al día siguiente.

Las vistas caducadas se borran solas cada noche, poco después de las 00:00. El visor actual
tampoco abre una vista caducada aunque aún no se haya borrado. En el visor clásico, un enlace que
ya no existe muestra una página de vista no encontrada.

### Quién puede abrir el enlace

- Si el proyecto es público, cualquiera, también sin iniciar sesión.
- Si no lo es, el enlace pide iniciar sesión y abre la vista solo a quien tiene permiso para abrir
  el proyecto; el resto ve la página **Operación no permitida**.

### Gestionar las vistas compartidas

![Lista de vistas compartidas](img/vistas-compartidas-lista.png)

**Proyectos > Vistas compartidas** abre la **Lista de vistas compartidas**, con el identificador, la
**URL** y la **Fecha de caducidad** de cada vista. Las que no caducan aparecen con fecha del año
9999. El buscador filtra la tabla.

Para eliminar una vista, pulse **Eliminar vista compartida** (botón rojo con un aspa) y confirme con
**Aceptar**. El enlace deja de funcionar para todos los que lo tengan.

!!! note "Qué no se ve en la lista"
    La lista no muestra la descripción, el proyecto ni quién creó cada vista. Para saber a qué
    proyecto pertenece una vista, ábrala con su URL.

## Aplicaciones

Una aplicación aparece en la página de inicio de los usuarios, junto a sus proyectos, y lleva a la
dirección que se indique. Sirve para dar acceso desde el portal a otras herramientas web.

- La ven los usuarios con alguno de los roles asignados a la aplicación. Los superusuarios las ven
    todas.
- Si es pública, la ve todo el mundo, y aparece también en la página de proyectos públicos, sin
    iniciar sesión.

### Lista de aplicaciones

![Lista de aplicaciones](img/vistas-compartidas-aplicaciones-lista.png)

La **Lista de aplicaciones** muestra el **Nombre**, el **Título**, la **URL** y si es pública
(**¿Es pública?**). En cada fila:

- **Actualizar aplicación**: abre el formulario.
- **Eliminar aplicación**: pide confirmación y la borra.

### Crear o modificar una aplicación

Pulse **Añadir aplicación**. El formulario tiene dos pestañas.

![Formulario de aplicación, pestaña General](img/vistas-compartidas-aplicacion-general.png)

**General**:

- **Nombre**: identificador de la aplicación. Solo admite letras sin acentos, números, guiones y
    guiones bajos; los espacios y los demás caracteres se eliminan al guardar. No puede repetirse y
    **no se puede cambiar después**.
- **Título**: el texto que ven los usuarios.
- **Descripción**: texto breve que acompaña a la aplicación.
- **URL**: la dirección a la que lleva. Puede ser completa (`https://…`) o una ruta del propio
    servidor (`/…`). Admite `{id}` y `{name}`, que se sustituyen por el identificador y el nombre de
    la aplicación.
- **Configuración**: texto libre para la aplicación enlazada. gvSIG Online no lo usa; déjelo vacío
    salvo que la aplicación lo necesite.
- **¿Cambiar imagen?**: la imagen que la representa en el portal (.jpg, .jpeg o .png). Sin imagen,
    se usa una por defecto.

**Permisos**:

- **¿Es público?**: cualquiera puede verla. Mientras esté marcada, no se pueden marcar roles.
- **Asignar grupo de usuarios**: marque los roles que verán la aplicación. El buscador filtra la
    lista. Al crear la aplicación, los superusuarios pueden asignar cualquier rol y el resto del
    personal, solo su rol principal; al modificarla, el formulario muestra todos los roles.

El rol de administración se asigna siempre, aunque no se marque.

Pulse **Guardar** (o **Actualizar** al modificar) para guardar los cambios, o **Cancelar** para
salir sin guardar.

!!! warning "Al modificar, revise los roles"
    Al guardar una aplicación se sustituyen todos sus roles por los marcados en el formulario. Un
    rol que se desmarque deja de ver la aplicación.
