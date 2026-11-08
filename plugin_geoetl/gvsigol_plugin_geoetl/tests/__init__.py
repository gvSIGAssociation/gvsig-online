# -*- coding: utf-8 -*-
"""Los tests del asistente parten de los interruptores apagados, tenga lo que tenga el contenedor."""

_ASSISTANT_DEFAULTS = {
    'ETL_ASSISTANT_ENGINE': 'legacy',
    'ETL_ASSISTANT_EXECUTION': 'inline',
    'ETL_ASSISTANT_STREAMING': False,
    'ETL_ASSISTANT_TOKEN_STREAMING': False,
    'ETL_ASSISTANT_ACTIONS': False,
    'ETL_ASSISTANT_QUESTIONS': False,
    'ETL_ASSISTANT_ALTERNATIVES': False,
    'ETL_ASSISTANT_PARAM_PICKER': False,
    'ETL_ASSISTANT_NEXT_STEPS': False,
    'ETL_ASSISTANT_COLUMNS': False,
}

try:
    from gvsigol_plugin_geoetl import settings as _geoetl_settings
    for _name, _value in _ASSISTANT_DEFAULTS.items():
        setattr(_geoetl_settings, _name, _value)
except Exception:  # noqa: BLE001 - algunos tests se ejecutan sin Django
    pass
