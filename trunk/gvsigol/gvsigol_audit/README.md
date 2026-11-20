# Sistema de Auditoría de gvSIG Online

## Descripción General

El sistema de auditoría de gvSIG Online registra todas las operaciones realizadas por los usuarios a través de APIs REST y vistas Django. Los logs se generan en formato JSON estructurado, compatible con herramientas de agregación de logs como **Grafana Loki** (usando Promtail o Fluent Bit como agentes).

## Arquitectura

El sistema de auditoría está centralizado en el módulo `gvsigol_audit` y puede ser utilizado tanto por el core como por plugins:

- **`gvsigol_audit.audit_registry`**: Registro centralizado de patrones de endpoints
- **`gvsigol_audit.audit_logger`**: Funciones para generar y escribir logs estructurados
- **`gvsigol_audit.audit_middleware`**: Middleware Django que intercepta y registra peticiones
- **`gvsigol_audit.audit_settings`**: Configuración del sistema de auditoría

Los plugins pueden registrar sus propios endpoints usando (solo necesario si `AUDIT_AUTO_DETECT=False`):
- **`gvsigol_audit.audit_registry`**: Sistema centralizado para registrar patrones de endpoints
- **`gvsigol_audit.view_audit_registry`**: Funciones helper para registrar vistas Django del core

## Modos de Logging

El sistema soporta tres modos de logging:

### 1. Modo `basic`
Registra información mínima esencial:
- Timestamp
- Método HTTP
- Path de la petición
- Usuario (o 'anonymous')
- ID de usuario
- Código de estado HTTP
- Tiempo de respuesta (ms)
- Dirección IP

### 2. Modo `full`
Incluye toda la información del modo `basic` más:
- Parámetros de consulta (query params)
- User-Agent
- Headers HTTP (con filtrado de datos sensibles)
- Cuerpo de la petición (request body) con filtrado de datos sensibles

### 3. Modo `compact` (por defecto)
Similar al modo `full`, pero además filtra las geometrías GeoJSON del request body para ahorrar espacio en los logs. Las geometrías se reemplazan por `[GEOMETRY_FILTERED]`.

## Detección Automática

**Por defecto, el sistema detecta automáticamente todas las operaciones de API REST y vistas Django** sin necesidad de registrar explícitamente cada endpoint. Esto significa que:

- ✅ **No es necesario modificar el `ready()` de cada plugin o core**
- ✅ **Todas las peticiones a `/api/*` se auditan automáticamente**
- ✅ **Todas las peticiones con headers JSON/XML se auditan automáticamente**
- ✅ **Todas las vistas Django bajo el prefijo de gvsigol (ej: `/gvsigonline/*`) se auditan automáticamente**

La detección automática está optimizada para rendimiento:
- Cachea valores calculados en la inicialización del middleware
- Utiliza operaciones O(1) o listas pequeñas
- Impacto en rendimiento: < 0.1 ms adicional por petición

Si prefieres control explícito, puedes desactivar la detección automática y registrar solo los endpoints que desees auditar (ver sección "Registro de Endpoints").

## Configuración

### Variables de Entorno

El sistema puede configurarse mediante variables de entorno:

```bash
# Habilitar/deshabilitar auditoría (default: False)
AUDIT_ENABLED=True

# Modo de logging: 'basic', 'full', o 'compact' (default: 'compact')
AUDIT_MODE=compact

# Ruta del archivo de log o 'stdout' para escribir a stdout (útil para Docker)
# Por defecto, si no se especifica, se usa stdout
AUDIT_LOG_PATH=stdout  # Valor por defecto
# O bien, para escribir a un archivo:
AUDIT_LOG_PATH=/opt/gvsigol_data/logs/audit.log

# Habilitar detección automática (default: True)
# Si es False, solo se auditarán endpoints registrados explícitamente
AUDIT_AUTO_DETECT=True
```

### Configuración en settings.py

También puede configurarse en el archivo `settings.py` principal:

```python
# Habilitar/deshabilitar auditoría (por defecto: False)
AUDIT_ENABLED = True

# Modo de logging (por defecto: 'compact')
AUDIT_MODE = 'compact'  # 'basic', 'full', o 'compact'

# Ruta del archivo de log (por defecto: 'stdout')
AUDIT_LOG_PATH = 'stdout'  # Valor por defecto, o ruta a archivo

# Habilitar detección automática (default: True)
AUDIT_AUTO_DETECT = True  # False para solo auditar endpoints registrados explícitamente

# Campos sensibles adicionales a filtrar
AUDIT_SENSITIVE_FIELDS = ['mi_campo_secreto', 'otro_campo']

# Rutas a excluir de la auditoría
AUDIT_EXCLUDE_PATHS = [
    '/api/v1/swagger/',
    '/api/v1/redoc/',
    '/api/v1/swagger.json',
]
```

## Filtrado de Datos Sensibles

El sistema filtra automáticamente los siguientes campos sensibles:

- `password`, `passwd`, `pwd`
- `secret`, `token`, `api_key`, `apikey`
- `access_token`, `refresh_token`
- `authorization`, `auth`, `credentials`
- `private_key`, `secret_key`, `session_key`

Los valores de estos campos se reemplazan por `[FILTERED]` en los logs.

También se filtran automáticamente los headers sensibles:
- `Authorization`
- `Cookie`
- `X-Api-Key`

## Registro de Endpoints (Opcional)

> **Nota:** Con `AUDIT_AUTO_DETECT=True` (por defecto), **no es necesario registrar endpoints**. El sistema detecta automáticamente todas las APIs REST y vistas Django. Solo necesitas registrar endpoints si:
> - Desactivas la detección automática (`AUDIT_AUTO_DETECT=False`)
> - Quieres auditar endpoints que no siguen los patrones estándar
> - Quieres tener control explícito sobre qué se audita

### Registro de APIs REST

Los plugins pueden registrar sus endpoints API REST en su `apps.py` usando directamente `gvsigol_audit`:

```python
from django.apps import AppConfig
from gvsigol_audit.audit_registry import register_audit_patterns

class MiPluginConfig(AppConfig):
    name = 'gvsigol_plugin_miplugin'
    
    def ready(self):
        # Registrar patrones específicos (solo necesario si AUDIT_AUTO_DETECT=False)
        # Útil para endpoints fuera de /api/* o /gvsigonline/*
        register_audit_patterns([
            '/mi-plugin/api/',
            '/mi-plugin/v1/',
            '/custom-endpoint/',  # Endpoint fuera de patrones estándar
        ])
```

### Registro de Vistas Django del Core

Las vistas Django del core se registran automáticamente en `gvsigol_audit.apps.py` cuando `AUDIT_AUTO_DETECT=True`. Los módulos del core son:

- `core/`
- `auth/`
- `services/`
- `symbology/`
- `filemanager/`
- `statistics/`

Para registrar vistas adicionales del core (solo necesario si `AUDIT_AUTO_DETECT=False`):

```python
from gvsigol_audit.view_audit_registry import register_core_view_pattern

register_core_view_pattern('/gvsigonline/mi-modulo/')
```

### Registro de Vistas Django de Plugins

Los plugins también pueden registrar sus vistas Django (solo necesario si `AUDIT_AUTO_DETECT=False` o si las vistas están fuera de `/gvsigonline/*`):

```python
from gvsigol_audit.audit_registry import register_audit_patterns
from django.conf import settings

class MiPluginConfig(AppConfig):
    name = 'gvsigol_plugin_miplugin'
    
    def ready(self):
        # Registrar vistas Django específicas
        gvsigol_path = getattr(settings, 'GVSIGOL_PATH', 'gvsigonline')
        register_audit_patterns([
            f'/{gvsigol_path}/miplugin/',
            '/custom-path/',
        ])
```

## Formato de los Logs

Los logs se generan en formato JSON, una línea por log (formato compatible con Loki):

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "method": "POST",
  "path": "/api/v1/layers/",
  "user": "admin",
  "user_id": 1,
  "status_code": 201,
  "response_time_ms": 125.45,
  "ip_address": "192.168.1.100",
  "query_params": {"format": "json"},
  "user_agent": "Mozilla/5.0...",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "[FILTERED]"
  },
  "request_body": {
    "name": "Mi Capa",
    "password": "[FILTERED]",
    "geometry": "[GEOMETRY_FILTERED]"
  }
}
```

## Integración con Grafana Loki

### Usando stdout (Recomendado para Docker)

Por defecto, si no se especifica `AUDIT_LOG_PATH`, los logs se escribirán a stdout (valor por defecto). Esto es ideal para Docker y contenedores, ya que los logs pueden ser capturados directamente por Promtail o Fluent Bit:

**docker-compose.yml:**
```yaml
services:
  gvsigol:
    environment:
      - AUDIT_LOG_PATH=stdout
      - AUDIT_MODE=compact
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**Promtail config (promtail-config.yml):**
```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: gvsigol
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'
    pipeline_stages:
      - json:
          expressions:
            timestamp: timestamp
            level: level
            method: method
            path: path
            user: user
            status_code: status_code
      - labels:
          level:
          method:
          user:
          status_code:
      - output:
          source: message
```

### Usando archivo de log

Si se configura una ruta de archivo, Promtail puede leer el archivo directamente:

**Promtail config:**
```yaml
scrape_configs:
  - job_name: gvsigol-audit
    static_configs:
      - targets:
          - localhost
        labels:
          job: gvsigol-audit
          __path__: /opt/gvsigol_data/logs/audit.log
    pipeline_stages:
      - json:
          expressions:
            timestamp: timestamp
            level: level
            method: method
            path: path
            user: user
            status_code: status_code
      - labels:
          level:
          method:
          user:
          status_code:
```

## Consultas en Grafana

Una vez que los logs están en Loki, puedes crear dashboards en Grafana con consultas LogQL:

```
# Todas las peticiones de un usuario
{job="gvsigol-audit"} | json | user="admin"

# Peticiones con tiempo de respuesta > 1 segundo
{job="gvsigol-audit"} | json | response_time_ms > 1000

# Errores (status_code >= 400)
{job="gvsigol-audit"} | json | status_code >= 400

# Peticiones POST a APIs
{job="gvsigol-audit"} | json | method="POST" | path=~"/api/.*"

# Tasa de peticiones por minuto
rate({job="gvsigol-audit"}[1m])
```

## Ejemplos de Uso

### Ejemplo 1: Configuración básica para desarrollo

```python
# settings.py
# Activar auditoría (por defecto está desactivada)
AUDIT_ENABLED = True
# Usar modo básico (por defecto es 'compact')
AUDIT_MODE = 'basic'
AUDIT_LOG_PATH = os.path.join(BASE_DIR, 'logs', 'audit.log')
```

### Ejemplo 2: Configuración para producción con Docker

```bash
# .env o docker-compose.yml
AUDIT_ENABLED=True
AUDIT_MODE=compact
AUDIT_LOG_PATH=stdout
```

### Ejemplo 3: Registrar endpoints personalizados (fuera de patrones estándar)

```python
# mi_plugin/apps.py
from django.apps import AppConfig
from gvsigol_audit.audit_registry import register_audit_patterns

class MiPluginConfig(AppConfig):
    name = 'gvsigol_plugin_miplugin'
    
    def ready(self):
        # Solo necesario si los endpoints están fuera de /api/* o /gvsigonline/*
        # Por ejemplo, endpoints personalizados en la raíz
        register_audit_patterns([
            '/mi-plugin/api/v1/',
            '/mi-plugin/api/v2/',
            '/custom-endpoint/',  # Fuera de patrones estándar
        ])
```

> **Nota:** Si todos tus endpoints están bajo `/api/*` o `/gvsigonline/*`, no necesitas registrarlos. La detección automática los cubrirá.

## Notas Importantes

1. **Detección Automática**: Por defecto, el sistema detecta automáticamente todas las APIs REST y vistas Django. No es necesario registrar endpoints manualmente a menos que desactives `AUDIT_AUTO_DETECT=False`.

2. **Rendimiento**: El sistema está optimizado para rendimiento:
   - Utiliza lazy loading y caché de patrones
   - Cachea valores calculados (prefijos, exclusiones) en la inicialización
   - Operaciones O(1) o listas pequeñas en la detección
   - Impacto estimado cuando está activado: < 0.1 ms adicional por petición
   - **Overhead cuando está desactivado (`AUDIT_ENABLED=False`)**: El middleware permanece en la lista de `MIDDLEWARE` pero realiza solo dos comparaciones booleanas por petición (una en `process_request` y otra en `process_response`), con un overhead estimado de < 0.01 ms por petición. Este overhead es despreciable comparado con el procesamiento normal de la petición HTTP y otros middlewares, por lo que es seguro mantener el middleware en la lista incluso cuando está desactivado. Esto permite activar/desactivar la auditoría mediante variables de entorno sin necesidad de modificar código.

3. **Seguridad**: Los datos sensibles se filtran automáticamente. Sin embargo, es recomendable revisar los logs periódicamente para asegurar que no se registran datos sensibles adicionales.

4. **Espacio en disco**: En modo `full`, los logs pueden ocupar mucho espacio, especialmente si hay muchas geometrías. Use el modo `compact` para reducir el tamaño.

5. **Docker**: Por defecto, los logs se escriben a stdout (valor por defecto de `AUDIT_LOG_PATH`), lo cual es ideal para Docker. Los logs pueden ser capturados directamente por Promtail o Fluent Bit sin configuración adicional.

6. **Fallback**: Si se especifica una ruta de archivo y no se puede escribir al archivo de log (por ejemplo, por permisos), el sistema automáticamente escribe a stdout como fallback.

7. **Exclusiones Automáticas**: El sistema excluye automáticamente paths estáticos, media y admin de la auditoría cuando se detectan bajo el prefijo de gvsigol.

## Troubleshooting

### Los logs no se generan

1. Verificar que `AUDIT_ENABLED=True`
2. Verificar que el middleware está en `MIDDLEWARE` en `settings.py`
3. Verificar que los endpoints están registrados correctamente
4. Revisar los logs de Django para errores

### Los logs ocupan mucho espacio

1. Cambiar a modo `compact` para filtrar geometrías
2. Cambiar a modo `basic` para información mínima
3. Configurar rotación de logs en Promtail/Fluent Bit

### No se capturan logs en Loki

1. Verificar que Promtail/Fluent Bit está configurado correctamente
2. Verificar que el formato de los logs es JSON válido
3. Verificar la configuración de labels en Promtail

## Referencias

- [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Promtail Documentation](https://grafana.com/docs/loki/latest/clients/promtail/)
- [Fluent Bit Documentation](https://docs.fluentbit.io/)

