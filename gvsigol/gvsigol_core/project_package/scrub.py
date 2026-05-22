# -*- coding: utf-8 -*-
import copy
import json

_SECRET_KEYS = frozenset({
    'password', 'passwd', 'secret', 'token', 'api_key', 'apikey', 'authorization',
    'client_secret', 'refresh_token',
})


def scrub_value(obj):
    if isinstance(obj, dict):
        return scrub_dict(obj)
    if isinstance(obj, list):
        return [scrub_value(x) for x in obj]
    return obj


def scrub_dict(d):
    out = {}
    for k, v in d.items():
        lk = str(k).lower()
        if lk in _SECRET_KEYS:
            out[k] = '****'
        elif lk == 'connection_params':
            if isinstance(v, str):
                try:
                    parsed = json.loads(v)
                except Exception:
                    out[k] = v
                else:
                    out[k] = json.dumps(scrub_dict(parsed))
            elif isinstance(v, dict):
                out[k] = scrub_dict(v)
            else:
                out[k] = v
        elif isinstance(v, dict):
            out[k] = scrub_dict(v)
        elif isinstance(v, list):
            out[k] = [scrub_value(x) for x in v]
        else:
            out[k] = v
    return out


def scrub_json_tree(tree):
    return scrub_value(copy.deepcopy(tree))


def assert_no_password_leak(text):
    """Raise ValueError if obvious secret patterns appear (for tests)."""
    lower = text.lower()
    for needle in ('"password": "', "'password': '", '"passwd": "', 'password='):
        if needle in lower and '****' not in text:
            raise ValueError('Possible password leak in serialized content')
