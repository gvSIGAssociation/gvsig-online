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
@author: jrodrigo <jrodrigo@scolab.es>
'''

from django.shortcuts import HttpResponse
import settings
import json
import requests
from django.views.decorators.csrf import csrf_exempt
from xml.etree import ElementTree

from django.contrib.gis.geos import Polygon, Point, MultiPoint, GeometryCollection

def get_conf(request):
    if request.method == 'POST':
        response = {
            'url_catastro': settings.URL_CATASTRO
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')


@csrf_exempt
def get_provincias(request):
    if request.method == 'POST':
        provincias_url = settings.URL_API_CATASTRO + '/OVCCallejero.asmx/ConsultaProvincia';

        r = requests.get(url = provincias_url, params = {})
        response = r.content

        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')


@csrf_exempt
def get_municipios(request):
    if request.method == 'POST':
        provincia = request.POST.get('provincia')

        municipio_url = settings.URL_API_CATASTRO + '/OVCCallejero.asmx/ConsultaMunicipio?Provincia='+provincia+'&Municipio=';

        r = requests.get(url = municipio_url, params = {})
        response = r.content

        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')



@csrf_exempt
def get_vias(request):
    if request.method == 'POST':
        provincia = request.POST.get('provincia')
        municipio = request.POST.get('municipio')

        address_url = settings.URL_API_CATASTRO + '/OVCCallejero.asmx/ConsultaVia?Provincia='+provincia+'&Municipio='+municipio+"&TipoVia="+"&NombreVia=";

        r = requests.get(url = address_url, params = {})
        response = r.content

        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')



@csrf_exempt
def get_rc_by_coords(request):
    if request.method == 'POST':
        xcen = request.POST.get('xcen')
        ycen = request.POST.get('ycen')
        srs = request.POST.get('srs')

        response = {}
        response['xcen'] = xcen
        response['ycen'] = ycen
        response['srs'] = srs

        address_url = settings.URL_API_CATASTRO + '/OVCCoordenadas.asmx/Consulta_RCCOOR?SRS='+srs+'&Coordenada_X='+xcen+'&Coordenada_Y='+ycen
        r = requests.get(url = address_url, params = {})

        tree = ElementTree.fromstring(r.content)

        for aux1 in tree.iter('{http://www.catastro.meh.es/}coordenadas'):
            for aux2 in aux1.iter('{http://www.catastro.meh.es/}coord'):
                for aux3 in aux2.iter('{http://www.catastro.meh.es/}pc'):
                    for aux5 in aux3.iter('{http://www.catastro.meh.es/}pc1'):
                        response['rc'] = aux5.text
                    for aux5 in aux3.iter('{http://www.catastro.meh.es/}pc2'):
                        response['rc'] += aux5.text

                for aux3 in aux2.iter('{http://www.catastro.meh.es/}ldt'):
                    response['address'] = aux3.text

        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')


@csrf_exempt
def get_rc_info(request):
    if request.method == 'POST':
        xcen = request.POST.get('xcen')
        ycen = request.POST.get('ycen')
        srs = request.POST.get('srs')

        if srs:
            srs = srs.replace("EPSG:", "")

        if xcen and ycen and srs:
            address_url = 'https://www1.sedecatastro.gob.es/CYCBienInmueble/OVCListaBienes.aspx?origen=Carto&huso='+srs+'&x='+xcen+'&y='+ycen

            r = requests.get(url = address_url, params = {})
            response = r.content
            response = response.replace('<script src="/MasterPage/js/jquery.min.js"></script>','')
            response = response.replace('<link href="../RecursosComunes/Estilos/jquery-ui.css" rel="stylesheet" type="text/css">','')
            response = response.replace('../Cartografia', 'https://www1.sedecatastro.gob.es/Cartografia')
            response = response.replace('/MasterPage', 'https://www1.sedecatastro.gob.es/MasterPage')
            response = response.replace('../RecursosComunes', 'https://www1.sedecatastro.gob.es/RecursosComunes')
            response = response.replace('../CYCBienInmueble', 'https://www1.sedecatastro.gob.es/CYCBienInmueble')

            response = response.replace('<link href="https://www1.sedecatastro.gob.es/MasterPage/css/noframes2.css"  type="text/css" rel="stylesheet" >','')
            response = response.replace('<link href="https://www1.sedecatastro.gob.es/RecursosComunes/Estilos/jquery-ui.css" rel="stylesheet" type="text/css" />','')
            response = response.replace('<link href="https://www1.sedecatastro.gob.es/MasterPage/css/bootstrap.min.css" rel="stylesheet">','')
            response = response.replace('<link href="https://www1.sedecatastro.gob.es/MasterPage/css/print.css" type="text/css" rel="stylesheet" media="print">','')
            response = response.replace('<script src="https://www1.sedecatastro.gob.es/MasterPage/js/bootstrap.min.js"  type="text/javascript"></script>','')

        else:
            response = ''

        return HttpResponse(response, content_type='plain/html')

@csrf_exempt
def get_referencia_catastral_polygon(request):
    if request.method == 'POST':
        ref_catastral = request.POST.get('ref_catastral').lstrip()
        srs='EPSG::4326'

        catastral_url = 'http://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx?service=wfs&version=2&request=getfeature&STOREDQUERIE_ID=GetParcel&refcat='+ref_catastral+'&srsname='+srs
        r = requests.get(url = catastral_url, params = {})
        tree = ElementTree.fromstring(r.content)
        features = []

        prefix3 = '{http://www.opengis.net/gml/3.2}'
        poslist = tree.findall(".//"+ prefix3 + "posList")

        features = []
        for points in poslist:
            dimension = points.attrib['srsDimension']
            count = points.attrib['srsDimension']

            feature = {
                'coords' : points.text,
                'srs': srs.replace('::', ':'),
                'dimension': dimension,
                'count': count
            }

            features.append(feature)

        response = {
            'featureCollection': features
        }

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@csrf_exempt
def get_referencia_catastral(request):
    if request.method == 'POST':
        srs = 'EPSG:4326'
        typex = request.POST.get('tipo')
        params_str = request.POST.get('params')
        params = json.loads(params_str)

        rc = ''
        response = {}

        if typex == 'ref_catastral':
            provincia = params['provincia']
            municipio = params['municipio']
            rc = params['rc'].lstrip()

            '''
            url = settings.URL_API_CATASTRO + "/OVCCallejero.asmx/Consulta_DNPRC?Provincia="+provincia+"&Municipio="+municipio+"&RC="+rc

            r = requests.get(url = url, params = {})
            tree = ElementTree.fromstring(r.content)
            '''

        if typex == 'location':
            provincia = params['provincia']
            municipio = params['municipio']
            urban_radio = params['urban_radio']

            url = ""

            if urban_radio:
                tipovia = params['tipovia']
                nombrevia = params['nombrevia']
                numerovia = params['numerovia']
                bloquevia = params['bloquevia']
                escaleravia = params['escaleravia']
                plantavia = params['plantavia']
                puertavia = params['puertavia']

                url = settings.URL_API_CATASTRO + "/OVCCallejero.asmx/Consulta_DNPLOC"
                url += "?Provincia="+provincia+"&Municipio="+municipio
                url += "&Sigla="+tipovia+"&Calle="+nombrevia+"&Numero="+numerovia
                url += "&Bloque="+bloquevia+"&Escalera="+escaleravia+"&Planta="+plantavia+"&Puerta="+puertavia
            else:
                poligonovia = params['poligonovia']
                parcelavia = params['parcelavia']

                url = settings.URL_API_CATASTRO + "/OVCCallejero.asmx/Consulta_DNPPP"
                url += "?Provincia="+provincia+"&Municipio="+municipio+"&Poligono="+poligonovia+"&Parcela="+parcelavia

            print 'Location url: ' + url
            r = requests.get(url = url, params = {})
            tree = ElementTree.fromstring(r.content)

            for aux1 in tree.iter('{http://www.catastro.meh.es/}bico'):
                for aux2 in aux1.iter('{http://www.catastro.meh.es/}bi'):
                    for aux3 in aux2.iter('{http://www.catastro.meh.es/}idbi'):
                        for aux4 in aux3.iter('{http://www.catastro.meh.es/}rc'):
                            for aux5 in aux4.iter('{http://www.catastro.meh.es/}pc1'):
                                rc = aux5.text
                            for aux5 in aux4.iter('{http://www.catastro.meh.es/}pc2'):
                                rc += aux5.text
                            print 'Referencia catastral: ' + rc


            for aux1 in tree.iter('{http://www.catastro.meh.es/}lrcdnp'):
                for aux2 in aux1.iter('{http://www.catastro.meh.es/}rcdnp'):
                    for aux4 in aux2.iter('{http://www.catastro.meh.es/}rc'):
                        for aux5 in aux4.iter('{http://www.catastro.meh.es/}pc1'):
                            rc = aux5.text
                        for aux5 in aux4.iter('{http://www.catastro.meh.es/}pc2'):
                            rc += aux5.text
                        print 'Referencia catastral: ' + rc

        if typex == 'reg_code':
            address_url = settings.URL_API_CATASTRO + '/OVCCallejero.asmx/ConsultaVia?Provincia='+provincia+'&Municipio='+municipio+"&TipoVia="+"&NombreVia="

            r = requests.get(url = address_url, params = {})
            tree = ElementTree.fromstring(r.content)


        if rc.__len__() > 0:
            final_url = settings.URL_API_CATASTRO + "/OVCCoordenadas.asmx/Consulta_CPMRC?Provincia=&Municipio=&SRS="+ srs +"&RC="+ rc[0:14]

            r = requests.get(url = final_url, params = {})
            tree = ElementTree.fromstring(r.content)

            for aux1 in tree.iter('{http://www.catastro.meh.es/}coordenadas'):
                for aux2 in aux1.iter('{http://www.catastro.meh.es/}coord'):
                    for aux3 in aux2.iter('{http://www.catastro.meh.es/}geo'):
                        for aux5 in aux3.iter('{http://www.catastro.meh.es/}xcen'):
                            response['xcen'] = aux5.text
                        for aux5 in aux3.iter('{http://www.catastro.meh.es/}ycen'):
                            response['ycen'] = aux5.text
                        response['srs'] = srs
                        response['rc'] = rc[0:14]
                    for aux3 in aux2.iter('{http://www.catastro.meh.es/}ldt'):
                        response['address'] = aux3.text


        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')