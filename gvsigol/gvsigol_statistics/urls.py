from functools import wraps

from django.http import HttpResponseForbidden
from django.urls import URLPattern, URLResolver, include, path

from gvsigol_statistics import api, api_events, views


def _superuser_only(view):
    @wraps(view)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return HttpResponseForbidden()
        return view(request, *args, **kwargs)
    return wrap


def _protect(patterns):
    """
    Copia las rutas de actstream exigiendo superusuario en todas (algunas de sus
    vistas y feeds son públicas y muestran la actividad de los usuarios).
    Se conservan las URLs y los nombres.
    """
    protected = []
    for p in patterns:
        if isinstance(p, URLResolver):
            protected.append(URLResolver(p.pattern, _protect(p.url_patterns), p.default_kwargs,
                                         p.app_name, p.namespace))
        elif isinstance(p, URLPattern):
            protected.append(URLPattern(p.pattern, _superuser_only(p.callback), p.default_args, p.name))
    return protected


app_name="gvsigol_statistics"
urlpatterns = [
    path('activity/', include(_protect(include('actstream.urls')[0].urlpatterns))),
    path('get_registered_actions/<plugin_name>/<action_name>/', views.get_registered_actions, name='get_registered_actions'),
    path('register_action/', views.register_action, name='statistics_register_action'),

    path('get-targets-from-content-type/', views.get_targets_from_content_type, name='get_targets_from_content_type'),

    path('statistics_list/', views.statistics_list, name='statistics_list'),
    path('statistics_list/legacy/', views.statistics_legacy, name='statistics_legacy'),

    # API JSON v1 (solo lectura, superusuarios)
    path('api/v1/metrics/', api.metrics, name='api_metrics'),
    path('api/v1/summary/', api.summary, name='api_summary'),
    path('api/v1/timeseries/', api.timeseries, name='api_timeseries'),
    path('api/v1/top/', api.top, name='api_top'),
    path('api/v1/heatmap/', api.heatmap, name='api_heatmap'),
    path('api/v1/unused/', api.unused, name='api_unused'),

    # Registro de eventos desde la SPA (DRF, token Bearer)
    path('api/v1/events/session/', api_events.SessionEventView.as_view(), name='api_event_session'),
    path('api/v1/events/layer/', api_events.LayerEventView.as_view(), name='api_event_layer'),
]
