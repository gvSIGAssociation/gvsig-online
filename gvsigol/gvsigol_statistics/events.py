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
Registro de eventos de uso (actstream).

Punto único para registrar accesos desde el core y los plugins. Nunca lanza
excepciones: un fallo al registrar una estadística no debe romper la petición.

    from gvsigol_statistics.events import record_event, VERB_PROJECT
    record_event(request.user, VERB_PROJECT, action_object=project, channel=CHANNEL_SPA)

Convenciones (las mismas que ya usaba gvSIG Online):
- Si el usuario es anónimo, el actor es el propio objeto (p. ej. el proyecto).
- El canal ('classic', 'spa', 'mobile') se guarda en Action.data['channel'].
'''

import datetime
import hashlib
import logging

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

logger = logging.getLogger('gvsigol')

VERB_LOGIN = 'gvsigol_auth/login'
VERB_PROJECT = 'gvsigol_core/get_conf'
VERB_LAYER = 'gvsigol_services/layer_activate'

CHANNEL_CLASSIC = 'classic'
CHANNEL_SPA = 'spa'
CHANNEL_MOBILE = 'mobile'

# Clave de sesión de Django con el id del usuario cuyo login ya se ha registrado
SESSION_LOGIN_KEY = '_gol_stats_login'


def _is_user(obj):
    return isinstance(obj, get_user_model())


def actor_for(user, action_object):
    """Usuario autenticado, o el propio objeto si es anónimo (convención de gvSIG Online)."""
    if user is not None and getattr(user, 'is_authenticated', False):
        return user
    return action_object


def hash_key(value):
    """Identificador opaco (no se guardan identificadores de sesión en claro)."""
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:24]


def record_event(actor, verb, action_object=None, target=None, channel=None,
                 dedupe_seconds=0, dedupe_data=None, **extra):
    """
    Registra una acción. Devuelve True si se ha guardado y False si se ha omitido
    (duplicado o error).

    dedupe_seconds: no registra si ya existe la misma acción (actor, verbo, objeto)
        en los últimos N segundos. Solo se aplica a actores que son usuarios: con
        anónimos el actor es el objeto y se perderían visitas de personas distintas.
    dedupe_data: dict; no registra si ya existe una acción del mismo actor y verbo
        cuyo Action.data contiene esos valores (p. ej. la misma sesión de Keycloak).
    """
    if actor is None:
        return False
    try:
        from actstream import action
        from actstream.models import Action

        if dedupe_seconds or dedupe_data:
            qs = Action.objects.filter(
                verb=verb,
                actor_content_type=ContentType.objects.get_for_model(actor),
                actor_object_id=str(actor.pk)).order_by()
            if dedupe_data:
                if qs.filter(**{'data__%s' % k: v for k, v in dedupe_data.items()}).exists():
                    return False
            if dedupe_seconds and _is_user(actor):
                recent = qs.filter(timestamp__gte=timezone.now() - datetime.timedelta(seconds=dedupe_seconds))
                if channel:
                    recent = recent.filter(data__channel=channel)
                if action_object is not None:
                    recent = recent.filter(
                        action_object_content_type=ContentType.objects.get_for_model(action_object),
                        action_object_object_id=str(action_object.pk))
                if recent.exists():
                    return False

        data = dict(extra)
        if dedupe_data:
            data.update(dedupe_data)
        if channel:
            data['channel'] = channel
        kwargs = {'verb': verb}
        if action_object is not None:
            kwargs['action_object'] = action_object
        if target is not None:
            kwargs['target'] = target
        # actstream guarda en Action.data los argumentos que no reconoce
        kwargs.update(data)
        action.send(actor, **kwargs)
        return True
    except Exception:
        logger.exception("statistics: no se pudo registrar %s", verb)
        return False


def on_user_logged_in(sender, request, user, **kwargs):
    """
    Receptor de la señal user_logged_in (login local, LDAP, OIDC del admin…).

    La renovación silenciosa de OIDC (SessionRefresh) vuelve a llamar a login() con
    el mismo usuario y conserva la sesión: se reconoce por la marca de sesión y no
    se cuenta. Un login nuevo tras cerrar sesión o con otro usuario sí se cuenta.
    """
    session = getattr(request, 'session', None) if request is not None else None
    if session is not None and session.get(SESSION_LOGIN_KEY) == user.pk:
        return
    record_event(user, VERB_LOGIN, channel=CHANNEL_CLASSIC)
    if session is not None:
        try:
            session[SESSION_LOGIN_KEY] = user.pk
        except Exception:
            logger.exception("statistics: no se pudo marcar el login en la sesión")
