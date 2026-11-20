# -*- coding: utf-8 -*-
'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
'''
API de registro de eventos para la SPA (DRF: acepta el token Bearer de Keycloak
con las clases de autenticación configuradas en el despliegue).

POST api/v1/events/session/  -> login en la SPA (uno por sesión de Keycloak)
POST api/v1/events/layer/    -> el usuario activa una capa en el visor

Responden siempre 202 salvo errores de entrada (400) o de permisos (401/403):
la SPA no espera la respuesta y nunca debe fallar por estas llamadas.
'''

import base64
import json
import logging

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from .events import (CHANNEL_MOBILE, CHANNEL_SPA, VERB_LAYER, VERB_LOGIN,
                     actor_for, hash_key, record_event)

logger = logging.getLogger('gvsigol')

CHANNELS = (CHANNEL_SPA, CHANNEL_MOBILE)


class EventRateThrottle(SimpleRateThrottle):
    """Límite por usuario o IP para que nadie infle las estadísticas a mano."""
    scope = 'gvsigol_statistics_events'
    rate = '120/min'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = 'user-%s' % request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


def _channel(request):
    channel = request.data.get('channel') if hasattr(request, 'data') else None
    return channel if channel in CHANNELS else CHANNEL_SPA


def token_session_key(token):
    """
    Identificador de la sesión de Keycloak a partir del token de acceso, ya validado
    por la clase de autenticación de DRF: 'sid' (o 'session_state' en versiones
    antiguas). Si no hay, se usa 'auth_time' (momento del login). None si no es un JWT.
    """
    if isinstance(token, bytes):
        token = token.decode('utf-8', 'ignore')
    if not isinstance(token, str) or token.count('.') != 2:
        return None
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload.encode('ascii')))
    except Exception:
        return None
    for claim in ('sid', 'session_state', 'auth_time'):
        if claims.get(claim):
            return '%s:%s' % (claim, claims[claim])
    return None


class SessionEventView(APIView):
    """La SPA lo llama al tener un usuario autenticado. Cuenta un login por sesión de Keycloak."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [EventRateThrottle]

    def post(self, request):
        session_key = token_session_key(request.auth)
        if session_key:
            recorded = record_event(request.user, VERB_LOGIN, channel=_channel(request),
                                    dedupe_data={'session': hash_key(session_key)})
        else:
            # Sin identificador de sesión (p. ej. autenticación básica): como mucho
            # un login cada 8 horas por usuario
            recorded = record_event(request.user, VERB_LOGIN, channel=_channel(request),
                                    dedupe_seconds=8 * 3600)
        return Response({'recorded': recorded}, status=202)


class LayerEventView(APIView):
    """El usuario ha activado una capa en el visor de la SPA."""
    permission_classes = [AllowAny]
    throttle_classes = [EventRateThrottle]

    def post(self, request):
        from gvsigol_services.models import Layer
        layer_id = request.data.get('layer_id')
        try:
            layer = Layer.objects.get(pk=int(layer_id))
        except (TypeError, ValueError, Layer.DoesNotExist):
            return Response({'status': 'ERROR', 'msg': 'Unknown layer'}, status=400)
        recorded = record_event(actor_for(request.user, layer), VERB_LAYER, action_object=layer,
                                channel=_channel(request))
        return Response({'recorded': recorded}, status=202)
