from django.conf.urls import url

urlpatterns = [
    url(r'^login_user/$', 'gvsigol_auth.views.login_user', name='login_user'), 
    url(r'^logout_user/$', 'gvsigol_auth.views.logout_user', name='logout_user'),
]