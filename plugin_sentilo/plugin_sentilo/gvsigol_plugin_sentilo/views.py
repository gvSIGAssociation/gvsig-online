# -*- coding: utf-8 -*-
from django.shortcuts import HttpResponse, render, redirect
from gvsigol_plugin_sentilo.services.sentilo import populate_sentilo_configs, process_sentilo_request, delete_sentilo_request
from gvsigol_plugin_sentilo.forms import SentiloConfigurationForm
from gvsigol_plugin_sentilo.models import SentiloConfiguration

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