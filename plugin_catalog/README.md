# gvsigol_plugin_catalog

Plugin de gvSIG Online que integra el catálogo de metadatos con **GeoNetwork 4.x**.

La búsqueda se hace a través del backend de gvSIG Online. La creación, actualización y borrado de metadatos usan la API REST de GeoNetwork.

Con GeoNetwork autenticado solo con usuarios locales, el plugin usa **HTTP Basic**. Con **Keycloak / OpenID Connect**, hace falta el modo **Bearer** (`openidconnectbearer` en GeoNetwork).

---

## Modos de autenticación

| `GEONETWORK_AUTH_TYPE` | Uso | GeoNetwork |
|---|---|---|
| `basic` (por defecto) | Usuario/contraseña locales de GeoNetwork | Seguridad `default` (o DB local habilitada) |
| `bearer` | Access token OIDC de Keycloak (password grant) | `GEONETWORK_SECURITY_TYPE=openidconnectbearer` |

Con `openidconnect` (solo login web OIDC) **no** se aceptan Basic ni Bearer de forma usable para la API del plugin. Hay que usar `openidconnectbearer`.

---

## Variables de entorno del plugin

| Variable | Descripción | Ejemplo |
|---|---|---|
| `GEONETWORK_BASE_URL` | URL pública de GeoNetwork (UI / enlaces) | `https://ejemplo.dominio/geonetwork` |
| `GEONETWORK_INTERNAL_URL` | URL que usa el backend para llamar a la API | `http://geonetwork-headless:8080/geonetwork` |
| `GEONETWORK_AUTH_TYPE` | `basic` o `bearer` | `bearer` |
| `GEONETWORK_USER` | Usuario API (`basic`) o usuario Keycloak (`bearer`) | `catalog-api` |
| `GEONETWORK_PASS` | Contraseña del usuario anterior | *(secret)* |
| `GEONETWORK_OIDC_TOKEN_URL` | Endpoint token de Keycloak | `https://ejemplo.dominio/auth/realms/gvsigonline/protocol/openid-connect/token` |
| `GEONETWORK_OIDC_CLIENT_ID` | Client OIDC de GeoNetwork | `geonetwork-client` |
| `GEONETWORK_OIDC_CLIENT_SECRET` | Secret del client | *(secret)* |
| `GEONETWORK_OIDC_SCOPE` | Scopes del password grant | `openid email profile offline_access` |
| `GEONETWORK_EDITOR_PATH` | Ruta SPA del editor | `/srv/spa/catalog.search` |
| `CATALOG_API_VERSION` | Versión API (`gn4`, `api0.1`, `legacy3.2`) | `gn4` |
| `CATALOG_AUTO_CREATE_METADATA` | Crear metadatos al publicar capas | `True` / `False` |
| `CATALOG_TIMEOUT` | Timeout HTTP (segundos) | `10` |

Si no se define `GEONETWORK_OIDC_TOKEN_URL`, se construye a partir de `OIDC_OP_BASE_URL` + `OIDC_OP_REALM_NAME` de gvSIG Online.

El plugin debe estar en `GVSIGOL_PLUGINS` (p.ej. `...,gvsigol_plugin_catalog`).

---

## Configuración de Keycloak

Realm típico: `gvsigonline`. Client: `geonetwork-client`.

### Client `geonetwork-client`

1. **Client authentication**: ON (confidential).
2. **Standard flow**: ON (login web en GeoNetwork).
3. **Direct access grants**: ON (el plugin obtiene el Bearer con password grant).
4. **Valid redirect URIs**: `https://<host>/geonetwork/*`
5. **Valid post logout redirect URIs**: `https://<host>/geonetwork/*`
6. **Web origins**: `https://<host>`

### Roles de cliente (perfiles GeoNetwork)

Crear en el client: `Administrator`, `Reviewer`, `Editor`, `RegisteredUser`, `Guest`, `UserAdmin`, `Monitor`.

Asignar al menos `Administrator` (o `Editor`) al usuario de servicio del plugin.

### Mappers

1. **Client roles** (`oidc-usermodel-client-role-mapper`):
   - Claim: `resource_access.${client_id}.roles` (o equivalente)
   - Activar: *Add to ID token*, *Add to access token*, *Add to userinfo*
2. **Audience** (`oidc-audience-mapper`), recomendado:
   - Included client audience: `geonetwork-client`
   - En el access token

GeoNetwork (`openidconnectbearer` + Keycloak) resuelve roles vía **userinfo**. Sin roles en userinfo, el usuario puede autenticarse con privilegios insuficientes.

### Usuario de servicio

Ejemplo: `catalog-api`, habilitado, con contraseña permanente y rol de cliente `Administrator` en `geonetwork-client`.

Ese usuario y contraseña son `GEONETWORK_USER` / `GEONETWORK_PASS` del backend.

---

## Configuración de GeoNetwork

### Variables relevantes

```bash
GEONETWORK_SECURITY_TYPE=openidconnectbearer
OPENIDCONNECT_CLIENTID=geonetwork-client
OPENIDCONNECT_CLIENTSECRET=<secret>
OPENIDCONNECT_IDTOKENROLELOCATION=resource_access.geonetwork-client.roles
OPENIDCONNECT_SCOPES=openid email profile offline_access
OPENIDCONNECT_SERVERMETADATA_CONFIG_URL=https://<host>/auth/realms/gvsigonline/.well-known/openid-configuration
```

- `openidconnectbearer`: login OIDC en el navegador **y** API con `Authorization: Bearer <access_token>`.
- La metadata OIDC (`OPENIDCONNECT_SERVERMETADATA_CONFIG_URL`) debe ser la **URL pública** del realm (mismo `iss` que el access token).

### Issuer del token

El plugin debe pedir el token al **mismo issuer** que usa GeoNetwork en su metadata.

| Origen del token | Resultado típico |
|---|---|
| URL pública (`https://<host>/auth/realms/.../token`) | OK: `iss` coincide; userinfo pública OK |
| URL interna del cluster (`http://keycloak-service:8080/auth/...`) | Falla: `iss` distinto; GeoNetwork obtiene 401 en userinfo |

Por eso `GEONETWORK_OIDC_TOKEN_URL` debe ser la URL pública (o una que emita el mismo `iss`).

---

## Flujo Bearer (resumen)

```
gvSIG Online (plugin_catalog)
  │  password grant (GEONETWORK_USER / PASS + client secret)
  ▼
Keycloak  ── access_token (roles Administrator en resource_access)
  │  Authorization: Bearer <token>
  ▼
GeoNetwork API (/srv/api/...)  ── valida JWT + userinfo ── usuario con perfil GN
```

El token se cachea en proceso hasta cerca de su caducidad (`oidc_token.py`).

---

## Ejemplo de configuración (backend)

```bash
GEONETWORK_BASE_URL=https://ejemplo.dominio/geonetwork
GEONETWORK_INTERNAL_URL=http://geonetwork-headless:8080/geonetwork
GEONETWORK_AUTH_TYPE=bearer
GEONETWORK_OIDC_TOKEN_URL=https://ejemplo.dominio/auth/realms/gvsigonline/protocol/openid-connect/token
GEONETWORK_OIDC_CLIENT_ID=geonetwork-client
GEONETWORK_OIDC_CLIENT_SECRET=<secret>
GEONETWORK_OIDC_SCOPE=openid email profile offline_access
GEONETWORK_USER=catalog-api
GEONETWORK_PASS=<password>
CATALOG_API_VERSION=gn4
```

Con Basic (sin Keycloak en la API):

```bash
GEONETWORK_AUTH_TYPE=basic
GEONETWORK_USER=admin
GEONETWORK_PASS=admin
GEONETWORK_INTERNAL_URL=http://geonetwork:8080/geonetwork
```

---

## Comprobaciones rápidas

1. **Token Keycloak** (desde el backend):

```bash
curl -sk -X POST "$GEONETWORK_OIDC_TOKEN_URL" \
  -d "grant_type=password" \
  -d "client_id=$GEONETWORK_OIDC_CLIENT_ID" \
  -d "client_secret=$GEONETWORK_OIDC_CLIENT_SECRET" \
  -d "username=$GEONETWORK_USER" \
  -d "password=$GEONETWORK_PASS" \
  -d "scope=openid email profile offline_access"
```

El JWT debe incluir `resource_access.geonetwork-client.roles` con `Administrator` (o `Editor`), y `iss` igual al de la metadata OIDC.

2. **API GeoNetwork**:

```bash
# CSRF / sesión
curl -sk -c /tmp/gn.ck -b /tmp/gn.ck -H 'Accept: application/json' \
  "$GEONETWORK_INTERNAL_URL/srv/api/me"

# Con Bearer
curl -sk -c /tmp/gn.ck -b /tmp/gn.ck \
  -H 'Accept: application/json' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-XSRF-TOKEN: <XSRF-TOKEN de la cookie>" \
  "$GEONETWORK_INTERNAL_URL/srv/api/me"
```

Respuesta esperada: HTTP 200 con usuario y `profile` tipo `Administrator`.

3. En gvSIG Online: crear metadatos de una capa (`/gvsigonline/catalog/create_metadata/<id>/`). Un 403 *"Access is denied... more privileges"* suele indicar sesión Guest (auth fallida o roles no llegan por userinfo).

---

## Problemas frecuentes

| Síntoma | Causa habitual |
|---|---|
| 403 al crear metadatos | Auth falsa/Guest, o usuario sin `Editor`/`Administrator` |
| 401 Bearer `invalid_user_info_response` | Token con `iss` distinto al de la metadata (usar token URL pública) |
| Token OK pero perfil Guest/RegisteredUser | Roles de cliente no van a **userinfo** |
| `gn_auth` falla en modo bearer | Falta secret/user/pass, Direct Access Grants OFF, o URL de token incorrecta |
| Basic Auth con OIDC-only | GeoNetwork no acepta login local; cambiar a `bearer` + `openidconnectbearer` |

Las peticiones a `/srv/api/*` deben llevar `Accept: application/json`. Sin ese header, GeoNetwork puede responder *Service not found* vía el servlet Jeeves.

---

## Referencias

- GeoNetwork 4.2 – [Authentication mode (OIDC / Bearer)](https://docs.geonetwork-opensource.org/4.2/administrator-guide/managing-users-and-groups/authentication-mode/)
- Despliegue k8s de referencia: `docker/k8s/geonetwork.yaml` y sección GeoNetwork de `docker/k8s/README.md`
