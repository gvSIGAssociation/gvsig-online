# Estadísticas de uso de gvSIG Online (`gvsigol_statistics`)

Registra el uso de la plataforma (inicios de sesión, proyectos abiertos y capas activadas) y lo muestra en un panel para
superusuarios en **Administración → Estadísticas** (`/gvsigonline/statistics/statistics_list/`).

Es distinto de `gvsigol_audit`: auditoría escribe una línea de log por cada petición HTTP (para Loki/Grafana) y no usa la
base de datos; estadísticas guarda solo eventos de negocio en la tabla `actstream_action` (django-activity-stream) y los
agrega para mostrarlos.

## Qué se registra

| Evento | Verbo | Actor | Objeto | Canales |
|---|---|---|---|---|
| Inicio de sesión | `gvsigol_auth/login` | usuario | — | `classic`, `spa` |
| Apertura de proyecto | `gvsigol_core/get_conf` | usuario, o el proyecto si es anónimo | proyecto | `classic`, `spa`, `mobile` |
| Activación de capa | `gvsigol_services/layer_activate` | usuario, o la capa si es anónimo | capa | `classic`, `spa` |

- **Anónimo** = el actor es el propio objeto (convención histórica de gvSIG Online).
- El canal se guarda en `Action.data['channel']`. Los eventos anteriores a esta versión no tienen canal.

### De dónde llegan

- **Logins de Django** (local, LDAP, `REMOTE_USER`, OIDC del panel de administración): señal `user_logged_in`
  (`events.on_user_logged_in`). La renovación silenciosa de OIDC (`SessionRefresh`, cada
  `OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS`) no cuenta: se reconoce por una marca en la sesión.
- **Logins de la SPA** (Keycloak, `@scolab/authprovider-oidc`): `POST api/v1/events/session/`. Se cuenta **un login por
  sesión de Keycloak** (claim `sid`, `session_state` o `auth_time` del token; solo se guarda un hash). Sin esos claims,
  como mucho uno cada 8 horas por usuario.
- **Proyectos en la SPA y la app móvil**: `plugin_projectapi` (`ProjectConfView` y `PublicProjectConfView`) cuando se pide
  un proyecto concreto. La misma apertura repetida en menos de 10 s cuenta una vez.
- **Capas en la SPA**: `apps/common/.../LayerTree/layerStatistics.js` → `POST api/v1/events/layer/` al encender una capa.
- **Visor clásico**: `gvsigol_core.views` (carga de proyecto) y `gvsigol_services.views.register_action` (capas).

Para registrar eventos desde código propio, usar siempre `record_event`, que nunca lanza excepciones:

```python
from gvsigol_statistics.events import record_event, actor_for, VERB_PROJECT, CHANNEL_SPA

record_event(actor_for(request.user, project), VERB_PROJECT, action_object=project, channel=CHANNEL_SPA)
```

## Métricas de plugins

Una app o plugin puede declarar métricas propias en su `settings.py` (mismo formato de siempre). Aparecen en la tarjeta
«Otras métricas» del panel y en la vista clásica:

```python
STATISTICS = [{
    'id': 'gvsigol_plugin_x',        # verbo = '<id>/<operation>'
    'operation': 'download',
    'count': 1,                       # distingue varias entradas con el mismo verbo
    'reverse_petition': False,        # True: ranking por usuario; False: por objeto
    'title': _('Downloads'),
    'target_title': _('Layers'),
    'target_field': 'title',          # campo para etiquetar los objetos
}]
```

y registrar los eventos con `record_event(actor, 'gvsigol_plugin_x/download', action_object=obj)`.

## API

Todas las rutas cuelgan de `/gvsigonline/statistics/`.

### Lectura (GET, solo superusuarios)

Parámetros comunes: `from`, `to` (`YYYY-MM-DD`, hora local, ambos incluidos; por defecto los últimos 30 días),
`user` (nombre de usuario o `anonymous`), `project` (id). Los errores de parámetros devuelven 400 en JSON.

| Ruta | Devuelve |
|---|---|
| `api/v1/metrics/` | Métricas declaradas y fecha del primer evento |
| `api/v1/summary/` | KPI del periodo y del anterior de igual duración, con % de cambio |
| `api/v1/timeseries/?verb=&interval=day\|week\|month` | Serie sin huecos (autenticados / anónimos / total) |
| `api/v1/top/?verb=&by=object\|user&limit=` | Ranking con etiqueta, %, usuarios únicos y último acceso |
| `api/v1/heatmap/?verb=` | Matriz 7 × 24 (lunes a domingo × hora local) |
| `api/v1/unused/?type=project\|layer&days=` | Proyectos o capas sin uso en N días (`partial_coverage` si no hay datos suficientes) |

`timeseries`, `top` y `unused` aceptan `format=csv` (separador `;`, UTF-8 con BOM para Excel).

Todas las respuestas incluyen `tracking_since` (primer evento registrado) para poder avisar de la cobertura.

### Registro (POST, para la SPA)

| Ruta | Autenticación | Cuerpo |
|---|---|---|
| `api/v1/events/session/` | obligatoria (token Bearer) | `{"channel": "spa"}` |
| `api/v1/events/layer/` | opcional | `{"layer_id": 12, "channel": "spa"}` |

Responden 202 y están limitadas a 120 peticiones por minuto por usuario o IP.

### Compatibilidad

Se mantienen sin cambios las rutas antiguas que usa la vista clásica (`get_registered_actions/…`,
`get-targets-from-content-type/`, `register_action/`) y su formato de respuesta, pero ahora exigen sesión
(superusuario para lectura). Las rutas de actstream (`activity/…`) también exigen superusuario.

## Panel

- `statistics_list/`: panel (KPI, evolución, rankings, mapa de calor, elementos sin uso, otras métricas).
- `statistics_list/legacy/`: vista clásica por pestañas. Se conserva por compatibilidad, pero no está enlazada desde el
  panel ni desde el menú: solo es accesible escribiendo la URL.

La vista clásica conserva su cálculo histórico: periodos en la zona horaria de PostgreSQL y modo «por usuario» que
omite los accesos en los que coinciden el id del usuario y el del objeto. El panel nuevo calcula en hora local
(`TIME_ZONE`) y no omite accesos, por eso las cifras pueden diferir ligeramente.

## Despliegue

1. `python manage.py migrate gvsigol_statistics`: crea el índice `gol_stats_action_verb_ts` sobre
   `actstream_action (verb, timestamp)` con `CREATE INDEX CONCURRENTLY` (no bloquea la tabla).
2. `collectstatic` (ficheros nuevos en `static/gvsigol_statistics/`).
3. Para capturar los accesos de la SPA, desplegar también `plugin_projectapi` y `gvsigol-frontend`
   (`apps/common` y `apps/authprovider-oidc`). Las tres piezas funcionan con versiones anteriores de las demás:
   simplemente no se registran esos accesos.

Rendimiento medido con 600.000 eventos: resumen de 30 días ≈ 60 ms, de 12 meses ≈ 300 ms, de 3 años ≈ 340 ms.

## Retención

No se borra nada automáticamente. Para limpiar eventos antiguos (por ejemplo desde cron):

```bash
python manage.py statistics_purge --older-than-days 730 --dry-run   # solo cuenta
python manage.py statistics_purge --older-than-days 730             # borra por lotes
```

Solo borra verbos de estadísticas (nunca otras acciones de actstream), exige un mínimo de 30 días y acepta `--verb` y
`--batch-size`.

## Tests

```bash
python manage.py test gvsigol_statistics
```

Son `SimpleTestCase` (no necesitan base de datos de test).

## Traducciones

Los textos del panel usan el contexto `statistics` (`{% trans "…" context "statistics" %}` / `pgettext`), para que no
los sobrescriban traducciones del mismo texto en otras apps (los plugins y `gvsigol_core` van antes en `LOCALE_PATHS`).
