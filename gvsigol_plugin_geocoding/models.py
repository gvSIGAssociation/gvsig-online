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
@author: José Badía <jbadia@scolab.es>
'''
from django.db import models
from gvsigol import settings
from gvsigol_plugin_geocoding import settings as geocoding_setting
from gvsigol_services.models import Datastore
from django.utils.translation import ugettext as _
import json

def get_default_provider_icon():
    return settings.BASE_URL + '/static/img/geocoding/toponimo.png'
    #return '/gvsigonline/static/img/geocoding/toponimo.png'


class Logstashetl(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=150, null=False)
    config = models.TextField(null=False)
    provider_id = models.IntegerField()


class Provider(models.Model):   
    type = models.CharField(max_length=100)
    category = models.CharField(max_length=100, null=True, blank=True)
    
    #datastore = models.ForeignKey(Datastore, null=True, blank=True)
    #resource = models.CharField(max_length=100, null=True, blank=True)   
    params = models.TextField()
    
    #table_name = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    image = models.ImageField(upload_to='images', default=get_default_provider_icon, null=True, blank=True)
    order = models.IntegerField(null=False, default=10)
    last_update = models.DateTimeField(auto_now_add=False, null=True, blank=True) 
    
    def __str__(self):
        values = dict(geocoding_setting.GEOCODING_SUPPORTED_TYPES).get(self.type)
        cadena = str(values)
        
        if self.type == 'googlemaps' or self.type == 'nominatim' or self.type == 'new_cartociudad' or self.type == 'ide_uy' or self.type == 'uy_sudir':
            return cadena
        
        params = json.loads(self.params)
        if 'datastore_id' in params:
            datastore = Datastore.objects.get(id=params['datastore_id'])
            cadena = cadena + '  (' + str(datastore.name)
            if self.type == 'user' or self.type == 'postgres':
                cadena = cadena + ' - ' + params['resource'] #+ ' (' + params['id_field'] + ', ' + params['text_field'] + ', ' + params['geom_field'] + ')'           
            cadena = cadena + ')'
        
        return  cadena


def translations_placeholder():
    test = _("gvsigol_plugin_geocoding manual title")
    test = _("gvsigol_plugin_geocoding manual desc")