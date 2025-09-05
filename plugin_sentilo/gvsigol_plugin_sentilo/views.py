# -*- coding: utf-8 -*-
from django.shortcuts import HttpResponse, render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import logging
from gvsigol_plugin_sentilo.services.sentilo import populate_sentilo_configs, process_sentilo_request, delete_sentilo_request
from gvsigol_plugin_sentilo.services.cleanup import clean_all_configured_tables
from gvsigol_plugin_sentilo.forms import SentiloConfigurationForm
from gvsigol_plugin_sentilo.models import SentiloConfiguration

LOGGER = logging.getLogger('gvsigol')

def sentilo_conf(request):        
    if request.method == 'GET':
        form = SentiloConfigurationForm()
        return render(request, 'sentilo_conf.html', {'form': form})
    
    if request.method == 'POST':
        form = SentiloConfigurationForm(request.POST)
        if form.is_valid():
            instance = form.save()
            process_sentilo_request(instance)
       
        return redirect('list_sentilo_configs') 

def list_sentilo_configs(request):
    configs = SentiloConfiguration.objects.all()
    configs = populate_sentilo_configs(configs)
    if len(configs) == 0:
        return redirect('sentilo_conf')
    return render(request, 'sentilo_list.html', {'configs': configs})

def delete_sentilo_config(request, config_id):
    if request.method == 'DELETE':
        # Get the SentiloConfiguration object by ID or return a 404 error if it doesn't exist
        delete_sentilo_request(config_id)
        return HttpResponse('Config deleted successfully')
    return HttpResponse('Method not allowed')

@require_http_methods(["POST"])
def manual_cleanup(request):
    """
    Ejecuta la limpieza manual de todas las tablas Sentilo configuradas.
    Endpoint para ser llamado desde el frontend.
    """
    try:
        LOGGER.info("[Sentilo Cleanup] Manual cleanup triggered by user")
        clean_all_configured_tables()
        return JsonResponse({
            'success': True,
            'message': 'Limpieza ejecutada correctamente. Revisa los logs para más detalles.'
        })
    except Exception as e:
        LOGGER.error("[Sentilo Cleanup] Manual cleanup failed: %s", str(e))
        return JsonResponse({
            'success': False,
            'message': f'Error durante la limpieza: {str(e)}'
        }, status=500)