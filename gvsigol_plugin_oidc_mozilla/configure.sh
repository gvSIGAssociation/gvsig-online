#!/bin/bash

echo "Running install script for oidc_mozilla plugin ..."
mv settings_tpl.py settings.py

if [ -z "$GVSIGOL_AUTH_BACKEND" ]; then
        echo "WARNING: GVSIGOL_AUTH_BACKEND is not defined, using 'gvsigol_auth'."
        GVSIGOL_AUTH_BACKEND="gvsigol_auth"
fi
if [ -z "$OIDC_OP_REALM_BASE_URL" ]; then
        echo "WARNING: OIDC_OP_REALM_BASE_URL is not defined, using BASE_URL + 'auth'."
        OIDC_OP_REALM_BASE_URL="$BASE_URL/auth"
fi
if [ -z "$OIDC_OP_AUTHORIZATION_ENDPOINT" ]; then
        echo "WARNING: OIDC_OP_AUTHORIZATION_ENDPOINT is not defined, using OIDC_OP_REALM_BASE_URL + '/protocol/openid-connect/auth'."
        OIDC_OP_REALM_BASE_URL="$OIDC_OP_REALM_BASE_URL/protocol/openid-connect/auth"
fi
if [ -z "$OIDC_OP_TOKEN_ENDPOINT" ]; then
        echo "WARNING: OIDC_OP_TOKEN_ENDPOINT is not defined, using OIDC_OP_REALM_BASE_URL + '/protocol/openid-connect/token'."
        OIDC_OP_TOKEN_ENDPOINT="$OIDC_OP_REALM_BASE_URL/protocol/openid-connect/token"
fi
if [ -z "$OIDC_OP_USER_ENDPOINT" ]; then
        echo "WARNING: OIDC_OP_USER_ENDPOINT is not defined, using OIDC_OP_REALM_BASE_URL + '/protocol/openid-connect/userinfo'."
        OIDC_OP_USER_ENDPOINT="$OIDC_OP_REALM_BASE_URL/protocol/openid-connect/userinfo"
fi
if [ -z "$OIDC_OP_JWKS_ENDPOINT" ]; then
        echo "WARNING: OIDC_OP_JWKS_ENDPOINT is not defined, using OIDC_OP_REALM_BASE_URL + '/protocol/openid-connect/certs'."
        OIDC_OP_JWKS_ENDPOINT="$OIDC_OP_REALM_BASE_URL/protocol/openid-connect/certs"
fi
if [ -z "$OIDC_OP_LOGOUT_ENDPOINT" ]; then
        echo "WARNING: OIDC_OP_LOGOUT_ENDPOINT is not defined, using OIDC_OP_REALM_BASE_URL + '/protocol/openid-connect/logout'."
        OIDC_OP_LOGOUT_ENDPOINT="$OIDC_OP_REALM_BASE_URL/protocol/openid-connect/logout"
fi
if [ -z "$OIDC_RP_CLIENT_ID" ]; then
        echo "WARNING: OIDC_RP_CLIENT_ID is not defined, using ''."
        OIDC_RP_CLIENT_ID=""
fi
if [ -z "$OIDC_RP_CLIENT_SECRET" ]; then
        echo "WARNING: OIDC_RP_CLIENT_SECRET is not defined, using ''."
        OIDC_RP_CLIENT_SECRET=""
fi

# debugging...
echo "GVSIGOL_AUTH_BACKEND" $GVSIGOL_AUTH_BACKEND
echo "OIDC_OP_REALM_BASE_URL" $OIDC_OP_REALM_BASE_URL
echo "OIDC_OP_AUTHORIZATION_ENDPOINT" $OIDC_OP_AUTHORIZATION_ENDPOINT
echo "OIDC_OP_TOKEN_ENDPOINT" $OIDC_OP_TOKEN_ENDPOINT
echo "OIDC_OP_USER_ENDPOINT" $OIDC_OP_USER_ENDPOINT
echo "OIDC_OP_JWKS_ENDPOINT" $OIDC_OP_JWKS_ENDPOINT
echo "OIDC_OP_LOGOUT_ENDPOINT" $OIDC_OP_LOGOUT_ENDPOINT
echo "OIDC_RP_CLIENT_ID" $OIDC_RP_CLIENT_ID
echo "OIDC_RP_CLIENT_SECRET" "xxxxxxxxxxx"

grep -rl "##GVSIGOL_AUTH_BACKEND##" | xargs sed -i "s/##GVSIGOL_AUTH_BACKEND##/$GVSIGOL_AUTH_BACKEND/g"
grep -rl "##OIDC_OP_REALM_BASE_URL##"  | xargs sed -i "s ##OIDC_OP_REALM_BASE_URL## $OIDC_OP_REALM_BASE_URL g"
grep -rl "##OIDC_OP_AUTHORIZATION_ENDPOINT##"  | xargs sed -i "s ##OIDC_OP_AUTHORIZATION_ENDPOINT## $OIDC_OP_AUTHORIZATION_ENDPOINT g"
grep -rl "##OIDC_OP_TOKEN_ENDPOINT##"  | xargs sed -i "s ##OIDC_OP_TOKEN_ENDPOINT## $OIDC_OP_TOKEN_ENDPOINT g"
grep -rl "##OIDC_OP_USER_ENDPOINT##" | xargs sed -i "s ##OIDC_OP_USER_ENDPOINT## $OIDC_OP_USER_ENDPOINT g" 
grep -rl "##OIDC_RP_CLIENT_ID##" | xargs sed -i "s/##OIDC_RP_CLIENT_ID##/$OIDC_RP_CLIENT_ID/g"
grep -rl "##OIDC_RP_CLIENT_ID##" | xargs sed -i "s/##OIDC_RP_CLIENT_ID##/$OIDC_RP_CLIENT_ID/g"
grep -rl "##OIDC_RP_CLIENT_SECRET##" | xargs sed -i "s/##OIDC_RP_CLIENT_SECRET##/$OIDC_RP_CLIENT_SECRET/g"
