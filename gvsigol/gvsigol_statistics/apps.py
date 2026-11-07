

from django.apps import AppConfig


class GvsigolStatisticsConfig(AppConfig):
    name = 'gvsigol_statistics'
    verbose_name = 'Statistics plugin'

    def ready(self):
        # Cuenta los inicios de sesión que pasan por django.contrib.auth.login()
        # (local, LDAP, OIDC del admin). Los de la SPA llegan por la API de eventos.
        from django.contrib.auth.signals import user_logged_in
        from gvsigol_statistics.events import on_user_logged_in
        user_logged_in.connect(on_user_logged_in, dispatch_uid='gvsigol_statistics_login')
