# gvsigol_plugin_catalog

Plugin de gvSIG Online que integra el catálogo de metadatos con **GeoNetwork 4.x**.

La búsqueda se hace a través del backend de gvSIG Online. La creación, actualización y borrado de metadatos usan la API REST de GeoNetwork.

Con GeoNetwork autenticado solo con usuarios locales, el plugin usa **HTTP Basic**. Con **Keycloak / OpenID Connect**, hace falta el modo **Bearer** (`openidconnectbearer` en GeoNetwork).

---

## Modos de autenticación

| `GEONETWORK_AUTH_TYPE` | Uso | GeoNetwork |
|---|---|---|
| `basic` (por defecto) | Usuario/contraseña locales de GeoNetwork | Seguridad `default` (o DB local habilitada) |
| `bearer` | Access token OIDC de la service account de Keycloak (client credentials) | `GEONETWORK_SECURITY_TYPE=openidconnectbearer` |

Con `openidconnect` (solo login web OIDC) **no** se aceptan Basic ni Bearer de forma usable para la API del plugin. Hay que usar `openidconnectbearer`.

---

## Variables de entorno del plugin

| Variable | Descripción | Ejemplo |
|---|---|---|
| `GEONETWORK_BASE_URL` | URL pública de GeoNetwork (UI / enlaces) | `https://ejemplo.dominio/geonetwork` |
| `GEONETWORK_INTERNAL_URL` | URL que usa el backend para llamar a la API | `http://geonetwork-headless:8080/geonetwork` |
| `GEONETWORK_AUTH_TYPE` | `basic` o `bearer` | `bearer` |
| `GEONETWORK_USER` | Usuario local de GeoNetwork. Solo con `GEONETWORK_AUTH_TYPE=basic` | `admin` |
| `GEONETWORK_PASS` | Contraseña de ese usuario. Solo con `basic` | *(secret)* |
| `GEONETWORK_OIDC_TOKEN_URL` | Endpoint token de Keycloak | `https://ejemplo.dominio/auth/realms/gvsigonline/protocol/openid-connect/token` |
| `GEONETWORK_OIDC_CLIENT_ID` | Client OIDC de GeoNetwork | `geonetwork-client` |
| `GEONETWORK_OIDC_CLIENT_SECRET` | Secret del client. En `bearer` es la credencial de la service account | *(secret)* |
| `GEONETWORK_OIDC_SCOPE` | Scopes del grant client credentials. El plugin quita `offline_access` porque ese scope es el refresh token de un usuario | `openid email profile` |
| `GEONETWORK_GROUP` | Nombre del grupo workspace donde se insertan los metadatos. Si no existe, la creación falla. Un valor numérico se acepta como id | `gvsigol` |
| `GEONETWORK_EDITOR_PATH` | Ruta SPA del editor | `/srv/spa/catalog.search` |
| `CATALOG_API_VERSION` | Versión API (`gn4`) | `gn4` |
| `CATALOG_AUTO_CREATE_METADATA` | Crear metadatos al publicar capas | `True` / `False` |
| `CATALOG_METADATA_STANDARD` | Estándar de las plantillas del plugin si el cliente no trae ninguna, o desempate si trae varias | vacío (= ISO 19139:2007), `iso19115-3`, `mgb-2.0` |
| `CATALOG_TIMEOUT` | Timeout HTTP (segundos) | `10` |

Si no se define `GEONETWORK_OIDC_TOKEN_URL`, se construye a partir de `OIDC_OP_BASE_URL` + `OIDC_OP_REALM_NAME` de gvSIG Online.

El plugin debe estar en `GVSIGOL_PLUGINS` (p.ej. `...,gvsigol_plugin_catalog`).

### Estándares de metadatos

La lectura y actualización de registros XML ya no asume ISO 19139. El plugin elige un gestor según el documento:

| Gestor | Detección (lectura y plantilla de cliente) |
|---|---|
| ISO 19139:2007 | raíz `gmd:MD_Metadata` |
| ISO 19115-1 / 19115-3 | raíz `mdb:MD_Metadata` |
| Perfil MGB 2.0 | 19115-3 con `mdb:metadataProfile` = `Perfil MGB 2.0` |

El gestor MGB 2.0 es una subclase del de 19115-3: solo cambia la plantilla, la detección del perfil y la lectura de `cit:CI_UFCode` / `cit:administrativeArea`.

Al crear un metadato el estándar sale de la plantilla, igual que al leer sale del XML:

1. Si la aplicación cliente (`gvsigol_app_*`) tiene ficheros en `mdtemplates/`, se detecta el estándar de ese XML y se rellena esa plantilla (contacto e institución del cliente).
2. Si no hay plantilla de cliente, se usa la plantilla del plugin. `CATALOG_METADATA_STANDARD` elige cuál; vacío deja ISO 19139:2007.
3. Si el cliente trae plantillas de más de un estándar, `CATALOG_METADATA_STANDARD` elige entre ellas. Si está vacío, se usa la más específica (MGB, luego 19115-3, luego 19139).

Nombres que se buscan en `mdtemplates/`:

- `dataset.xml` o `dataset19139.xml`
- `dataset19115-3.xml`
- `dataset-mgb.xml` o `dataset19115-3.mgb.xml`

El nombre no fija el estándar: se mira la raíz y, en su caso, `metadataProfile`.

Consulta y ficha de detalle usan el reader del estándar detectado; la búsqueda en GeoNetwork 4 (Elasticsearch) es independiente del XML.

---

## Configuración de Keycloak

Realm típico: `gvsigonline`. Client: `geonetwork-client`.

### Client `geonetwork-client`

1. **Client authentication**: ON (confidential).
2. **Standard flow**: ON (login web en GeoNetwork).
3. **Service accounts**: ON (el plugin obtiene el Bearer con client credentials).
4. **Direct access grants**: OFF.
5. **Valid redirect URIs**: `https://<host>/geonetwork/*`
6. **Valid post logout redirect URIs**: `https://<host>/geonetwork/*`
7. **Web origins**: `https://<host>`

### Roles de cliente (perfiles GeoNetwork)

Crear en el client: `Administrator`, `Reviewer`, `Editor`, `RegisteredUser`, `Guest`, `UserAdmin`, `Monitor`.

Asignar al menos `Administrator` (o `Editor`) a la service account `service-account-geonetwork-client` (pestaña **Service account roles**).

### Mappers

1. **Client roles** (`oidc-usermodel-client-role-mapper`):
   - Claim: `resource_access.${client_id}.roles` (o equivalente)
   - Activar: *Add to ID token*, *Add to access token*, *Add to userinfo*
2. **Audience** (`oidc-audience-mapper`), recomendado:
   - Included client audience: `geonetwork-client`
   - En el access token

GeoNetwork (`openidconnectbearer` + Keycloak) resuelve roles vía **userinfo**. Sin roles en userinfo, el usuario puede autenticarse con privilegios insuficientes.

### Service account

Keycloak crea el usuario `service-account-geonetwork-client` al activar **Service accounts**. El plugin no envía usuario ni contraseña: el token sale de `client_id` + `client_secret`.

Ese usuario debe tener el rol de cliente `Administrator` (o `Editor`). `GEONETWORK_USER` / `GEONETWORK_PASS` no intervienen en modo `bearer`.

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
  │  client credentials (client id + secret de geonetwork-client)
  ▼
Keycloak  ── access_token de service-account-geonetwork-client (roles Administrator)
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
GEONETWORK_OIDC_SCOPE=openid email profile
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
  -d "grant_type=client_credentials" \
  -d "client_id=$GEONETWORK_OIDC_CLIENT_ID" \
  -d "client_secret=$GEONETWORK_OIDC_CLIENT_SECRET" \
  -d "scope=openid email profile"
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

### Borrado de metadatos al eliminar capas

Al borrar una capa desde **Servicios → Capas**, el plugin escucha la señal `layer_deleted` y elimina el registro asociado en GeoNetwork.

En despliegues con **OpenID (`GEONETWORK_AUTH_TYPE=bearer`)** el borrado exige:

1. Token OIDC de la service account (`GEONETWORK_OIDC_CLIENT_ID` / `GEONETWORK_OIDC_CLIENT_SECRET`).
2. Roles de cliente en **userinfo** (`Administrator` o al menos `Editor`).
3. Cabecera CSRF (`X-XSRF-TOKEN`) alineada con la sesión autenticada.

Si el DELETE en GeoNetwork falla (403 CSRF / privilegios insuficientes), el metadato puede quedar huérfano en el catálogo. Revisar los logs de gvSIG Online buscando `GeoNetwork metadata delete failed`.

| Síntoma | Causa habitual |
|---|---|
| 403 al crear metadatos | Auth falsa/Guest, o usuario sin `Editor`/`Administrator` |
| 401 Bearer `invalid_user_info_response` | Token con `iss` distinto al de la metadata (usar token URL pública) |
| Token OK pero perfil Guest/RegisteredUser | Roles de cliente no van a **userinfo** |
| `gn_auth` falla en modo bearer | Falta secret, Service accounts OFF, o URL de token incorrecta |
| Basic Auth con OIDC-only | GeoNetwork no acepta login local; cambiar a `bearer` + `openidconnectbearer` |
| Capa borrada pero metadato sigue en GeoNetwork | DELETE falló con OIDC (CSRF/privilegios); ver logs `metadata delete failed` |

Las peticiones a `/srv/api/*` deben llevar `Accept: application/json`. Sin ese header, GeoNetwork puede responder *Service not found* vía el servlet Jeeves.

---

## Referencias

- GeoNetwork 4.2 – [Authentication mode (OIDC / Bearer)](https://docs.geonetwork-opensource.org/4.2/administrator-guide/managing-users-and-groups/authentication-mode/)
- Despliegue k8s de referencia: `docker/k8s/geonetwork.yaml` y sección GeoNetwork de `docker/k8s/README.md`
