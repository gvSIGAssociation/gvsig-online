from gvsigol.settings import GVSIGOL_AUTH_BACKEND
OIDC_RP_CLIENT_ID = 'geoserver-client'
OIDC_RP_CLIENT_SECRET = '54ba588b-723c-4626-85c3-e7d18b221fd2'
OIDC_OP_AUTHORIZATION_ENDPOINT = "https://keycloak.scolab.eu/auth/realms/migrate.gvsigonline.com/protocol/openid-connect/auth"
OIDC_OP_TOKEN_ENDPOINT = "https://keycloak.scolab.eu/auth/realms/migrate.gvsigonline.com/protocol/openid-connect/token"
OIDC_OP_USER_ENDPOINT = "https://keycloak.scolab.eu/auth/realms/migrate.gvsigonline.com/protocol/openid-connect/userinfo"
OIDC_OP_JWKS_ENDPOINT = "https://keycloak.scolab.eu/auth/realms/migrate.gvsigonline.com/protocol/openid-connect/certs"
OIDC_OP_LOGOUT_ENDPOINT = "https://keycloak.scolab.eu/auth/realms/migrate.gvsigonline.com/protocol/openid-connect/logout"
OIDC_OP_LOGOUT_URL_METHOD = GVSIGOL_AUTH_BACKEND + ".provider_logout"
OIDC_RP_SIGN_ALGO = 'RS256'
OIDC_STORE_ACCESS_TOKEN = True
OIDC_STORE_ID_TOKEN = True
OIDC_RP_SCOPES = 'openid email geoserver-client'