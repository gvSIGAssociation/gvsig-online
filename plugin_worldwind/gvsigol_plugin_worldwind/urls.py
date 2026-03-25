from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('ww_providers_list/', views.list, name='list'),
    path('ww_provider_add/', views.add, name='add'),
    path('ww_provider_delete/<int:id>/', views.delete, name='delete'),
    path('ww_provider_conf/<int:id>/', views.conf, name='conf')
]