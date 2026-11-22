# Estadísticas

El panel de **Estadísticas** muestra el uso de la plataforma: cuántas veces se abren los proyectos,
qué capas se encienden, cuántos inicios de sesión hay, quién usa más la plataforma y qué proyectos y
capas llevan tiempo sin usarse. Sirve, por ejemplo, para saber qué conviene mantener y qué se puede
retirar.

Se abre desde el panel de administración, en **Estadísticas** (el último apartado del menú).

## Quién puede hacer qué

| Acción | Quién |
|---|---|
| Ver el panel de estadísticas y descargar sus datos | Solo superusuarios. El resto del personal no ve el apartado en el menú |

## Qué se mide

La plataforma registra tres tipos de actividad:

| Actividad | Cuándo se registra |
|---|---|
| **Aperturas de proyecto** | Al abrir un proyecto en el visor actual, en el clásico o en la aplicación móvil. En el visor actual, si el mismo proyecto se pide varias veces en menos de 10 segundos, cuenta una vez |
| **Activaciones de capa** | Al encender una capa en el visor actual o en el clásico |
| **Inicios de sesión** | Al iniciar sesión. En el visor actual cuenta una vez por sesión, y la renovación automática de la sesión no cuenta como un inicio nuevo |

Si quien abre el proyecto o enciende la capa no ha iniciado sesión (en proyectos públicos), la
actividad se registra como **anónima**.

!!! note "Desde cuándo hay datos"
    Solo hay datos desde que se empezó a registrar la actividad. Bajo el título del panel se indica
    **Datos disponibles desde el** y la fecha del primer registro. Si el periodo elegido empieza
    antes, el panel lo avisa: las fechas anteriores aparecen sin actividad.

Los plugins instalados pueden registrar actividad propia (por ejemplo, descargas). Si hay alguna,
el panel la muestra en la tarjeta **Otras métricas**.

## Filtros

![Filtros y cifras principales del panel de estadísticas](img/estadisticas-filtros-kpi.png)

En la parte superior se elige qué actividad se analiza:

- **Periodo**: **7 días**, **30 días** (por defecto), **90 días**, **12 meses** o **Personalizado**,
    que muestra dos fechas, **Desde** y **Hasta** (ambas incluidas). El periodo como máximo puede
    abarcar unos diez años.
- **Proyecto**: **Todos los proyectos** o uno concreto. Con un proyecto elegido, las activaciones
    de capa se limitan a las capas de ese proyecto. Los inicios de sesión no dependen del proyecto.
- **Usuario**: **Todos los usuarios**, **Anónimo** (solo la actividad sin sesión) o un usuario
    concreto.

Los filtros se aplican a todas las tarjetas, salvo a **Elementos sin uso**. Las fechas y las horas
se calculan en la hora local del servidor. El navegador recuerda el último periodo y el intervalo
elegidos.

## Cifras principales

Debajo de los filtros aparecen las cifras del periodo:

| Cifra | Qué cuenta |
|---|---|
| **Aperturas de proyecto** | Veces que se ha abierto un proyecto |
| **Usuarios únicos** | Usuarios con sesión que han tenido alguna actividad (abrir un proyecto, encender una capa o iniciar sesión) |
| **Inicios de sesión** | Inicios de sesión |
| **Activaciones de capa** | Veces que se ha encendido una capa |
| **Proyectos usados** | Proyectos distintos que se han abierto |
| **Capas usadas** | Capas distintas que se han encendido |
| **Aperturas anónimas** | Porcentaje de aperturas de proyecto sin sesión |

Cada cifra se compara con el periodo anterior de la misma duración (**frente al periodo
anterior**), en porcentaje; las aperturas anónimas, en puntos porcentuales (pp). Si el periodo
anterior no tiene datos, se indica **sin datos en el periodo anterior**.

## Evolución de la actividad

![Gráfico Evolución de la actividad](img/estadisticas-evolucion.png)

Gráfico de líneas de la actividad a lo largo del periodo, con una línea para la actividad de
usuarios **Autenticados** y otra para la de **Anónimos**.

- Elija la actividad: **Proyectos**, **Capas** o **Inicios de sesión**.
- **Intervalo**: **Por día**, **Por semana**, **Por mes** o **Automático**, que agrupa por día
    hasta dos meses, por semana hasta poco más de un año y por mes a partir de ahí.
- **Tabla**: muestra los mismos datos en una tabla (**Periodo**, **Autenticados**, **Anónimos** y
    **Total**).

## Rankings

![Rankings y mapa de actividad por día y hora](img/estadisticas-rankings.png)

Tres tarjetas muestran los diez primeros de cada lista, con el número de veces, el porcentaje
sobre el total y el **Último acceso**:

- **Proyectos más visitados**: también indica cuántos usuarios distintos lo han abierto.
- **Capas más usadas**: igual, para las capas encendidas.
- **Usuarios más activos**: elija la actividad (**Aperturas de proyecto**, **Activaciones de
    capa** o **Inicios de sesión**). La actividad anónima no entra en este ranking; se indica aparte
    como **Accesos anónimos (no incluidos)**.

Un proyecto o una capa que ya no existe aparece marcado como **(eliminado)**.

## Actividad por día y hora

Un mapa de calor con los días de la semana (de lunes a domingo) y las 24 horas del día. Cuanto más
intenso es el color, más actividad hubo a esa hora. Pase el ratón por una celda para ver el número
de eventos. Elija la actividad en el desplegable de la tarjeta. Sirve, por ejemplo, para elegir el
mejor momento para una parada de mantenimiento.

## Elementos sin uso

![Tarjeta Elementos sin uso](img/estadisticas-sin-uso.png)

Lista los **Proyectos** o las **Capas** que no se han usado en los últimos **30 días sin uso**,
**90 días sin uso** (por defecto), **180 días sin uso** o **1 año sin uso**. Primero aparecen los
que no se han usado **Nunca**, y después los de uso más antiguo.

La tabla muestra el **Nombre**, el **Título**, el **Espacio de trabajo** (en las capas) y el
**Último uso**, y tiene buscador y paginación.

Esta tarjeta no depende de los filtros de la parte superior: siempre mira hacia atrás desde hoy.

!!! warning "Antes de retirar nada"
    Si la actividad se registra desde hace menos tiempo que el plazo elegido, el panel lo avisa:
    los elementos usados antes de esa fecha pueden aparecer como sin uso. Además, una capa solo
    cuenta como usada cuando alguien la enciende en el visor: las que ya se muestran al abrir el
    proyecto, o las que se consultan solo como servicio OGC desde otros programas, pueden aparecer
    aquí aunque se usen.

## Descargar los datos

Las tarjetas **Evolución de la actividad**, de rankings, **Elementos sin uso** y **Otras métricas**
tienen un botón **CSV** que descarga lo que muestra la tarjeta, con sus filtros. El fichero usa punto y
coma como separador y se abre directamente en Excel.

## Avisos del panel

- **Cálculo mejorado**: las cifras se calculan ahora en hora local y el recuento por usuario ya no
    omite ningún acceso, por lo que pueden diferir ligeramente de las que se mostraban antes. Se
    cierra con el aspa.
- **Todavía no se ha registrado actividad**: aún no hay datos; todas las cifras son cero.
- **No se han podido cargar los datos**: pulse **Reintentar**.

!!! note "Conservación de los datos"
    La actividad registrada no se borra automáticamente. Quien administra el servidor puede borrar
    los registros antiguos con la orden `statistics_purge`.
