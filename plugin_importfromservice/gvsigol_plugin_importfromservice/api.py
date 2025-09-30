# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2019 SCOLAB.

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

@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
import logging
import json
import requests
import xml.etree.ElementTree as ET
from django.http.response import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from gvsigol_plugin_baseapi.validation import HttpException
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from gvsigol_services.models import ServiceUrl
import json

logger = logging.getLogger(__name__)


def crear_xml_consulta(termino, start_position=1, max_records=50):
    """Crea el XML de consulta CSW con los parámetros especificados"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<csw:GetRecords
    xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:apiso="http://www.opengis.net/cat/csw/apiso/1.0"
    service="CSW"
    version="2.0.2"
    resultType="results"
    startPosition="{start_position}"
    maxRecords="{max_records}"
    outputSchema="http://www.isotc211.org/2005/gmd">

  <csw:Query typeNames="gmd:MD_Metadata">
    <csw:ElementSetName>full</csw:ElementSetName>
    <csw:Constraint version="1.1.0">
      <ogc:Filter>
        <ogc:PropertyIsLike wildCard="%" singleChar="_" escapeChar="\\">
          <ogc:PropertyName>apiso:Title</ogc:PropertyName>
          <ogc:Literal>%{termino}%</ogc:Literal>
        </ogc:PropertyIsLike>
      </ogc:Filter>
    </csw:Constraint>
  </csw:Query>
</csw:GetRecords>"""


def tiene_servicios_web(urls):
    """Verifica si las URLs contienen servicios WMS o WFS"""
    servicios_web = ['wms', 'wfs', 'mapserver', 'geoserver']
    
    for url in urls:
        url_lower = url.lower()
        if any(servicio in url_lower for servicio in servicios_web):
            return True
    return False





def detectar_idioma_endpoint(url):
    """Detecta el idioma basándose en el endpoint de la URL"""
    if '/spa/' in url:
        return 'spa'
    elif '/eng/' in url:
        return 'eng'
    elif '/cat/' in url:
        return 'cat'
    else:
        return 'spa'  # Por defecto español


def obtener_texto_por_idioma(versiones, idioma_preferido):
    """Obtiene el texto en el idioma preferido, con fallbacks"""
    if not versiones:
        return None
    
    # Mapeo de códigos de idioma
    lang_map = {
        'spa': 'default',  # Español es el default
        'eng': 'eng',
        'cat': 'cat'
    }
    
    idioma_codigo = lang_map.get(idioma_preferido, 'default')
    
    # Intentar obtener el idioma preferido
    if idioma_codigo in versiones:
        return versiones[idioma_codigo]
    
    # Fallback 1: Si es inglés y no existe, probar default
    if idioma_preferido == 'eng' and 'default' in versiones:
        return versiones['default']
    
    # Fallback 2: Si es catalán y no existe, probar default
    if idioma_preferido == 'cat' and 'default' in versiones:
        return versiones['default']
    
    # Fallback final: cualquier versión disponible
    return next(iter(versiones.values())) if versiones else None


def extraer_todas_versiones_idioma(elemento, ns):
    """Extrae todas las versiones de idioma disponibles de un elemento"""
    versiones = {}
    
    if elemento is None:
        return versiones
    
    # Texto por defecto (generalmente en español)
    char_string = elemento.find('.//gco:CharacterString', ns)
    if char_string is not None and char_string.text:
        versiones['default'] = char_string.text
    
    # Buscar elementos PT_FreeText para contenido multiidioma
    pt_freetext = elemento.find('.//gmd:PT_FreeText', ns)
    if pt_freetext is not None:
        for text_group in pt_freetext.findall('.//gmd:textGroup', ns):
            localised_string = text_group.find('.//gmd:LocalisedCharacterString', ns)
            if localised_string is not None:
                locale = localised_string.get('locale', '')
                text = localised_string.text
                if text:
                    # Extraer código de idioma del locale (ej: "#cat" -> "cat")
                    lang_code = locale.replace('#', '') if locale.startswith('#') else locale
                    versiones[lang_code] = text
    
    return versiones


def extraer_informacion_servicios(datasets, urls_wms_unicas, urls_wfs_unicas):
    """
    Extrae información (título, descripción) de cada servicio desde los metadatos CSW.
    Combina inteligentemente los títulos de múltiples datasets que comparten la misma URL.
    """
    service_info = {}
    
    # Crear un diccionario que mapee URLs a MÚLTIPLES datasets
    url_to_datasets = {}
    
    for dataset in datasets:
        wms_urls = dataset.get('urls_wms', [])  # Corregido: usar 'urls_wms' en lugar de 'wms_urls'
        wfs_urls = dataset.get('urls_wfs', [])  # Corregido: usar 'urls_wfs' en lugar de 'wfs_urls'
        
        # Asociar cada URL con TODOS los datasets que la usan
        for url in wms_urls + wfs_urls:
            if url not in url_to_datasets:
                url_to_datasets[url] = []
            url_to_datasets[url].append({
                'title': dataset.get('titulo', 'Servicio sin título'),
                'description': dataset.get('abstract', ''),
                'keywords': dataset.get('keywords', []),
                'identifier': dataset.get('identificador', '')
            })
    
    # Procesar URLs únicas y combinar información de múltiples datasets
    all_unique_urls = list(set(urls_wms_unicas + urls_wfs_unicas))
    
    for url in all_unique_urls:
        if url in url_to_datasets:
            datasets_info = url_to_datasets[url]
            
            # Combinar títulos de forma inteligente
            unique_titles = []
            seen_titles = set()
            for ds in datasets_info:
                title = ds['title'].strip()
                # Normalizar para comparación (ignorar mayúsculas/minúsculas)
                title_normalized = title.lower()
                if title and title_normalized not in seen_titles and title != 'Servicio sin título':
                    unique_titles.append(title)
                    seen_titles.add(title_normalized)
            
            # Combinar keywords únicas
            all_keywords = []
            seen_keywords = set()
            for ds in datasets_info:
                for kw in ds['keywords']:
                    kw_normalized = kw.lower().strip()
                    if kw_normalized and kw_normalized not in seen_keywords:
                        all_keywords.append(kw)
                        seen_keywords.add(kw_normalized)
            
            # Seleccionar la descripción más completa (la más larga no vacía)
            descriptions = [ds['description'] for ds in datasets_info if ds['description'].strip()]
            best_description = max(descriptions, key=len) if descriptions else 'Sin descripción disponible'
            
            # Crear título combinado
            if len(unique_titles) == 0:
                # Fallback: usar el nombre de la URL
                combined_title = f"Servicio: {url.split('/')[-1].split('?')[0]}"
            elif len(unique_titles) == 1:
                combined_title = unique_titles[0]
            elif len(unique_titles) <= 3:
                # Si hay 2-3 títulos, unirlos con " | "
                combined_title = " | ".join(unique_titles)
            else:
                # Si hay muchos títulos, usar el primero y agregar un contador
                combined_title = f"{unique_titles[0]} (+{len(unique_titles)-1} datasets)"
            
            service_info[url] = {
                'title': combined_title,
                'description': best_description,
                'keywords': all_keywords,
                'identifier': datasets_info[0]['identifier'],  # Usar el primero como identificador principal
                'dataset_count': len(datasets_info)  # Número de datasets que usan este servicio
            }
            
        else:
            # Fallback para URLs sin información
            service_info[url] = {
                'title': f'Servicio: {url.split("/")[-1].split("?")[0]}',
                'description': 'Sin descripción disponible',
                'keywords': [],
                'identifier': '',
                'dataset_count': 0
            }
    
    #for url, info in service_info.items():
    
    return service_info

def separar_urls_servicios(urls):
    """Separa las URLs en listas de WMS y WFS"""
    urls_wms = []
    urls_wfs = []
    
    for url in urls:
        if not url:
            continue
            
        url_lower = url.lower()
        
        # Limpiar URL: eliminar todos los parámetros y el ? final
        clean_url = url
        if '?' in clean_url:
            clean_url = clean_url.split('?')[0]
        
        # Limpiar también posibles espacios o caracteres extra
        clean_url = clean_url.strip()
        
        # Convertir HTTPS a HTTP para evitar problemas de CORS
        if clean_url.startswith('https://'):
            clean_url = clean_url.replace('https://', 'http://')
        
        # Detectar WMS
        if ('wms' in url_lower and 'service=wms' in url_lower) or 'wmsserver' in url_lower or 'mapserver' in url_lower:
            if clean_url not in urls_wms:
                urls_wms.append(clean_url)
        
        # Detectar WFS
        elif ('wfs' in url_lower and 'service=wfs' in url_lower) or 'wfsserver' in url_lower:
            if clean_url not in urls_wfs:
                urls_wfs.append(clean_url)
        
        # Detectar servicios genéricos (MapServer/GeoServer) - asumir WMS si no está especificado
        elif any(servicio in url_lower for servicio in ['mapserver', 'geoserver']) and 'service=' not in url_lower:
            if clean_url not in urls_wms:
                urls_wms.append(clean_url)
    
    #for i, url in enumerate(urls_wms, 1):
    
    #for i, url in enumerate(urls_wfs, 1):
    
    return urls_wms, urls_wfs

def eliminar_duplicados_urls(datasets):
    """Elimina URLs duplicadas y agrupa datasets por URL única"""
    urls_wms_unicas = set()
    urls_wfs_unicas = set()
    datasets_con_urls_unicas = []
    
    for dataset in datasets:
        # Recopilar todas las URLs WMS únicas
        for url in dataset['urls_wms']:
            urls_wms_unicas.add(url)
        
        # Recopilar todas las URLs WFS únicas
        for url in dataset['urls_wfs']:
            urls_wfs_unicas.add(url)
        
        # Mantener el dataset para referencia de metadatos
        datasets_con_urls_unicas.append(dataset)
    
    # Crear resumen de URLs únicas
    resumen = {
        'datasets': datasets_con_urls_unicas,
        'urls_wms_unicas': list(urls_wms_unicas),
        'urls_wfs_unicas': list(urls_wfs_unicas),
        'total_datasets': len(datasets_con_urls_unicas),
        'total_urls_wms': len(urls_wms_unicas),
        'total_urls_wfs': len(urls_wfs_unicas)
    }
    
    return resumen


def hacer_getcapabilities_wms(url):
    """Hace GetCapabilities a un servicio WMS y devuelve las capas disponibles"""
    try:
        # Limpiar URL - manejo especial para ArcGIS
        if url.endswith('?'):
            url = url[:-1]
        
        # Para ArcGIS MapServer, mantener la estructura completa
        if 'MapServer/WmsServer' in url:
            base_url = url  # Mantener la URL completa para ArcGIS
        elif '?' in url:
            base_url = url.split('?')[0]
        else:
            base_url = url
        
        
        # Probar diferentes versiones de WMS
        versiones = ['1.3.0', '1.1.1', '1.1.0']
        capas = []
        
        for version in versiones:
            capabilities_url = f"{base_url}?service=WMS&request=GetCapabilities&version={version}"
            
            try:
                response = requests.get(capabilities_url, timeout=15)
                if response.status_code != 200:
                    continue
                
                # Parsear XML
                root = ET.fromstring(response.content)
                
                # Imprimir el XML para debug (primeras líneas)
                xml_str = ET.tostring(root, encoding='unicode')
                
                # Intentar diferentes namespaces
                namespaces_list = [
                    # WMS 1.3.0
                    {'wms': 'http://www.opengis.net/wms', 'xlink': 'http://www.w3.org/1999/xlink'},
                    # WMS 1.1.1
                    {'wms': 'http://www.opengis.net/wms', 'xlink': 'http://www.w3.org/1999/xlink'},
                    # Sin namespace (para algunos servidores)
                    {},
                    # Namespace alternativo
                    {'wms': 'http://www.opengis.net/wms/1.3.0'}
                ]
                
                for ns in namespaces_list:
                    
                    # Buscar capas con namespace
                    if ns:
                        layers = root.findall('.//wms:Layer[wms:Name]', ns)
                        if not layers:
                            layers = root.findall('.//wms:Layer', ns)
                    else:
                        # Sin namespace
                        layers = root.findall('.//Layer[Name]')
                        if not layers:
                            layers = root.findall('.//Layer')
                    
                    
                    for layer in layers:
                        if ns:
                            name_el = layer.find('wms:Name', ns)
                            title_el = layer.find('wms:Title', ns)
                        else:
                            name_el = layer.find('Name')
                            title_el = layer.find('Title')
                        
                        if name_el is not None and name_el.text:
                            # Verificar que no sea una capa duplicada
                            nombre_capa = name_el.text
                            if not any(c['Name'] == nombre_capa for c in capas):
                                capa = {
                                    'Name': nombre_capa,
                                    'Title': title_el.text if title_el is not None else nombre_capa,
                                    'service_type': 'wms',
                                    'service_url': base_url
                                }
                                capas.append(capa)
                    
                    if capas:  # Si encontramos capas, no probar más namespaces
                        break
                
                if capas:  # Si encontramos capas, no probar más versiones
                    break
                    
            except Exception as ve:
                continue
        
        
        # Mostrar todas las capas encontradas para debug
        #for i, capa in enumerate(capas, 1):
        
        return capas
        
    except Exception as e:
        return []


def hacer_getcapabilities_wfs(url):
    """Hace GetCapabilities a un servicio WFS y devuelve las capas disponibles"""
    try:
        # Limpiar URL
        if url.endswith('?'):
            url = url[:-1]
        if '?' in url:
            base_url = url.split('?')[0]
        else:
            base_url = url
        
        # Construir URL de GetCapabilities
        capabilities_url = f"{base_url}?service=WFS&request=GetCapabilities&version=2.0.0"
        
        
        response = requests.get(capabilities_url, timeout=15)
        if response.status_code != 200:
            return []
        
        # Parsear XML
        root = ET.fromstring(response.content)
        
        # Definir namespaces para WFS
        ns = {
            'wfs': 'http://www.opengis.net/wfs/2.0',
            'wfs11': 'http://www.opengis.net/wfs'  # Fallback para WFS 1.1
        }
        
        capas = []
        
        # Buscar FeatureTypes en WFS 2.0
        for feature_type in root.findall('.//wfs:FeatureType', ns):
            name_el = feature_type.find('wfs:Name', ns)
            title_el = feature_type.find('wfs:Title', ns)
            
            if name_el is not None and name_el.text:
                capa = {
                    'name': name_el.text,
                    'title': title_el.text if title_el is not None else name_el.text,
                    'service_type': 'wfs',
                    'service_url': base_url
                }
                capas.append(capa)
        
        # Si no encuentra en WFS 2.0, probar WFS 1.1
        if not capas:
            for feature_type in root.findall('.//wfs11:FeatureType', ns):
                name_el = feature_type.find('wfs11:Name', ns)
                title_el = feature_type.find('wfs11:Title', ns)
                
                if name_el is not None and name_el.text:
                    capa = {
                        'name': name_el.text,
                        'title': title_el.text if title_el is not None else name_el.text,
                        'service_type': 'wfs',
                        'service_url': base_url
                    }
                    capas.append(capa)
        
        return capas
        
    except Exception as e:
        return []


def debug_comparar_getcapabilities(url):
    """Función para comparar GetCapabilities normal vs CSW"""
    
    # Método 1: Como lo hace el frontend normal
    capas_normales = hacer_getcapabilities_wms(url)
    #for i, capa in enumerate(capas_normales[:5], 1):  # Solo primeras 5
    
    return capas_normales


def procesar_capabilities_servicios(urls_wms_unicas, urls_wfs_unicas):
    """Procesa GetCapabilities de todas las URLs únicas y devuelve capas combinadas"""
    todas_las_capas = []
    
    # Procesar servicios WMS con comparación de debug
    for url_wms in urls_wms_unicas:
        
        # Hacer debug comparison si es ArcGIS
        if 'arcgis' in url_wms.lower() or 'mapserver' in url_wms.lower():
            debug_comparar_getcapabilities(url_wms)
        
        capas_wms = hacer_getcapabilities_wms(url_wms)
        todas_las_capas.extend(capas_wms)
    
    # Procesar servicios WFS  
    for url_wfs in urls_wfs_unicas:
        capas_wfs = hacer_getcapabilities_wfs(url_wfs)
        todas_las_capas.extend(capas_wfs)
    
    # Agrupar capas por nombre para identificar las que están en ambos servicios
    capas_agrupadas = {}
    
    
    for capa in todas_las_capas:
        # Usar el nombre de la capa como clave (puede estar en WMS como "Name" o WFS como "name")
        nombre_capa_raw = capa.get('Name') or capa.get('name')
        if not nombre_capa_raw:
            continue
        
        # Normalizar el nombre para evitar problemas de espacios, caracteres invisibles, prefijos, etc.
        nombre_capa = nombre_capa_raw.strip()
        
        # Remover prefijos comunes de namespaces (ms:, gml:, etc.)
        if ':' in nombre_capa:
            nombre_capa = nombre_capa.split(':', 1)[1]
        
            
        # Obtener el título de la capa
        titulo_capa = capa.get('Title') or capa.get('title') or nombre_capa
        
        if nombre_capa not in capas_agrupadas:
            capas_agrupadas[nombre_capa] = {
                'name': nombre_capa,  # Para WFS
                'Name': nombre_capa,  # Para WMS (compatibilidad)
                'title': titulo_capa,
                'Title': titulo_capa,  # Para WMS (compatibilidad)
                'wms_available': False,
                'wfs_available': False,
                'wms_url': None,
                'wfs_url': None
            }
        else:
            # Actualizar el título si el nuevo es más descriptivo
            titulo_existente = capas_agrupadas[nombre_capa]['title']
            if len(titulo_capa) > len(titulo_existente):
                capas_agrupadas[nombre_capa]['title'] = titulo_capa
                capas_agrupadas[nombre_capa]['Title'] = titulo_capa
        
        # Marcar disponibilidad según tipo de servicio
        if capa['service_type'] == 'wms':
            capas_agrupadas[nombre_capa]['wms_available'] = True
            capas_agrupadas[nombre_capa]['wms_url'] = capa['service_url']
        elif capa['service_type'] == 'wfs':
            capas_agrupadas[nombre_capa]['wfs_available'] = True
            capas_agrupadas[nombre_capa]['wfs_url'] = capa['service_url']
        
        # Debug: mostrar estado actual de la capa
        servicios_actuales = []
        if capas_agrupadas[nombre_capa]['wms_available']:
            servicios_actuales.append("WMS")
        if capas_agrupadas[nombre_capa]['wfs_available']:
            servicios_actuales.append("WFS")
    
    # Convertir a lista y mostrar resumen
    capas_finales = list(capas_agrupadas.values())
    
    for i, capa in enumerate(capas_finales, 1):
        servicios = []
        if capa['wms_available']:
            servicios.append("WMS")
        if capa['wfs_available']:
            servicios.append("WFS")
    
    # Debug adicional: detectar nombres similares que podrían ser duplicados
    nombres_capas = [capa['name'] for capa in capas_finales]
    #for i, nombre in enumerate(nombres_capas):
        
    # Buscar nombres que podrían ser duplicados
    """for i, nombre1 in enumerate(nombres_capas):
        for j, nombre2 in enumerate(nombres_capas[i+1:], i+1):
            if nombre1.lower().strip() == nombre2.lower().strip():
            elif abs(len(nombre1) - len(nombre2)) <= 2 and nombre1.replace(' ', '') == nombre2.replace(' ', ''):"""
    
    wms_count = sum(1 for c in capas_finales if c['wms_available'])
    wfs_count = sum(1 for c in capas_finales if c['wfs_available'])
    both_count = sum(1 for c in capas_finales if c['wms_available'] and c['wfs_available'])
    
    return capas_finales


def procesar_respuesta_csw(root, ns, idioma_preferido='spa'):
    """Procesa la respuesta XML y extrae la información de los datasets"""
    datasets = []
    
    # Recorrer datasets usando el formato ISO 19139 (gmd:MD_Metadata)
    for md in root.findall(".//gmd:MD_Metadata", ns):
        # Buscar gmd:MD_DataIdentification dentro de cada MD_Metadata
        data_id = md.find(".//gmd:MD_DataIdentification", ns)
        if data_id is None:
            continue
            
        # URLs de distribución
        urls = []
        for online_resource in md.findall(".//gmd:distributionInfo//gmd:CI_OnlineResource", ns):
            url_el = online_resource.find(".//gmd:URL", ns)
            if url_el is not None:
                urls.append(url_el.text)

        # Filtrar solo datasets que tengan servicios WMS/WFS
        if not tiene_servicios_web(urls):
            continue
            
        # Título con selección de idioma
        title_el = data_id.find(".//gmd:citation//gmd:title", ns)
        title_versions = extraer_todas_versiones_idioma(title_el, ns)
        title = obtener_texto_por_idioma(title_versions, idioma_preferido) or "SIN TÍTULO"

        # Abstract con selección de idioma
        abstract_el = data_id.find(".//gmd:abstract", ns)
        abstract_versions = extraer_todas_versiones_idioma(abstract_el, ns)
        abstract = obtener_texto_por_idioma(abstract_versions, idioma_preferido) or "SIN ABSTRACT"

        # Identificador del recurso
        identifier_el = md.find(".//gmd:fileIdentifier//gco:CharacterString", ns)
        identifier = identifier_el.text if identifier_el is not None else "SIN ID"

        # Keywords/subjects
        keywords = []
        for keyword in data_id.findall(".//gmd:descriptiveKeywords//gco:CharacterString", ns):
            if keyword.text:
                keywords.append(keyword.text)

        # Separar URLs de servicios web en WMS y WFS
        urls_wms, urls_wfs = separar_urls_servicios(urls)

        datasets.append({
            'identificador': identifier,
            'titulo': title,
            'abstract': abstract,
            'keywords': keywords,
            'urls_wms': urls_wms,
            'urls_wfs': urls_wfs,
            'idioma_usado': idioma_preferido
        })
    
    return datasets


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # To not perform the csrf check previously happening


class ServicesView(ListAPIView):
    serializer_class = None
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    @swagger_auto_schema(operation_id='get_services', operation_summary='',
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'])
    def get(self, request):
        try:
            wms_queryset = ServiceUrl.objects.filter(type='WMS')
            wfs_queryset = ServiceUrl.objects.filter(type='WFS')
            csw_queryset = ServiceUrl.objects.filter(type='CSW')

            wms = []
            for wms_serv in wms_queryset:
                wms.append({
                    'title': wms_serv.title,
                    'url': wms_serv.url
                })

            wfs = []
            for wfs_serv in wfs_queryset:
                wfs.append({
                    'title': wfs_serv.title,
                    'url': wfs_serv.url
                })

            csw = []
            for csw_serv in csw_queryset:
                csw.append({
                    'title': csw_serv.title,
                    'url': csw_serv.url
                })

            response = {
                'wms': wms,
                'wfs': wfs,
                'csw': csw
            }
            return JsonResponse(response, safe=False)

        except HttpException as e:
            return e.get_exception()


class CSWSearchView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    @swagger_auto_schema(operation_id='search_csw', operation_summary='Search CSW catalog',
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    def post(self, request):
        try:
            # Obtener datos de la petición
            service_url = request.data.get('service_url', '')
            search_query = request.data.get('search_query', '')
            
            # Validaciones básicas
            if not service_url:
                return JsonResponse({'error': 'Service URL is required'}, status=400)
            
            if not search_query:
                return JsonResponse({'error': 'Search query is required'}, status=400)
            
            
            # Detectar idioma del endpoint
            idioma_endpoint = detectar_idioma_endpoint(service_url)
            
            # Definir namespaces
            ns = {
                "csw": "http://www.opengis.net/cat/csw/2.0.2",
                "gmd": "http://www.isotc211.org/2005/gmd",
                "gco": "http://www.isotc211.org/2005/gco",
                "gml": "http://www.opengis.net/gml"
            }
            
            # Crear XML para la consulta
            xml_data = crear_xml_consulta(search_query, start_position=1, max_records=50)
            
            # Cabeceras HTTP
            headers = {
                "Content-Type": "application/xml"
            }
            
            # Hacer la petición POST al servicio CSW
            response = requests.post(service_url, data=xml_data.encode('utf-8'), headers=headers, timeout=30)
            
            if response.status_code != 200:
                return JsonResponse({'error': f'CSW service error: {response.status_code}'}, status=400)
            
            # Parsear XML
            root = ET.fromstring(response.content)
            
            # Obtener información de la respuesta
            search_results = root.find(".//csw:SearchResults", ns)
            if search_results is None:
                return JsonResponse({
                    'records': [],
                    'total_results': 0,
                    'message': 'No se encontraron resultados en el servicio CSW'
                })
            
            records_matched = int(search_results.get('numberOfRecordsMatched', 0))
            records_returned = int(search_results.get('numberOfRecordsReturned', 0))
            
            
            # Procesar los datasets
            datasets = procesar_respuesta_csw(root, ns, idioma_endpoint)
            
            # Eliminar URLs duplicadas
            resumen = eliminar_duplicados_urls(datasets)
            
            # NUEVO FLUJO: Solo devolver URLs al frontend
            
            # Extraer información de servicios desde los datasets
            service_info = extraer_informacion_servicios(datasets, resumen['urls_wms_unicas'], resumen['urls_wfs_unicas'])
            
            response_data = {
                'status': 'success',
                'urls_wms': resumen['urls_wms_unicas'],
                'urls_wfs': resumen['urls_wfs_unicas'],
                'service_info': service_info,  # Nueva información de servicios
                'total_datasets': len(datasets),
                'search_query': search_query,
                'service_url': service_url,
                'language': idioma_endpoint,
                'debug_info': {
                    'datasets_encontrados': len(datasets),
                    'urls_wms_encontradas': resumen['total_urls_wms'],
                    'urls_wfs_encontradas': resumen['total_urls_wfs'],
                    'message': f'Búsqueda CSW completada. Frontend procesará {resumen["total_urls_wms"]} URLs WMS y {resumen["total_urls_wfs"]} URLs WFS.'
                }
            }
            
            return JsonResponse(response_data, safe=False)
            
            # COMENTADO: Todo el bloque de GetCapabilities se movió al frontend
            """
            for i, url in enumerate(resumen['urls_wms_unicas'], 1):
            for i, url in enumerate(resumen['urls_wfs_unicas'], 1):
            
            # PROCESAR GETCAPABILITIES DE WMS Y WFS
            capas_procesadas = []
            
            # 1. Procesar servicios WMS
            for i, url_wms in enumerate(resumen['urls_wms_unicas'], 1):
                capas_wms = hacer_getcapabilities_wms(url_wms)
                for capa in capas_wms:
                    capa['service_type'] = 'wms'
                    capa['service_url'] = url_wms
                    capas_procesadas.append(capa)
            
            # 2. Procesar servicios WFS
            for i, url_wfs in enumerate(resumen['urls_wfs_unicas'], 1):
                capas_wfs = hacer_getcapabilities_wfs(url_wfs)
                for capa in capas_wfs:
                    capa['service_type'] = 'wfs'
                    capa['service_url'] = url_wfs
                    capas_procesadas.append(capa)
            
            
            # 3. Agrupar capas por nombre
            todas_las_capas = capas_procesadas
            
            # Agrupar capas por nombre para identificar las que están en ambos servicios
            capas_agrupadas = {}
            
            
            for capa in todas_las_capas:
                # Usar el nombre de la capa como clave (puede estar en WMS como "Name" o WFS como "name")
                nombre_capa_raw = capa.get('Name') or capa.get('name')
                if not nombre_capa_raw:
                    continue
                
                # Normalizar el nombre para evitar problemas de espacios, caracteres invisibles, prefijos, etc.
                nombre_capa = nombre_capa_raw.strip()
                
                # Remover prefijos comunes de namespaces (ms:, gml:, etc.)
                if ':' in nombre_capa:
                    nombre_capa = nombre_capa.split(':', 1)[1]
                
                
                # Debug específico para UMD
                if 'UMD' in nombre_capa or 'Aforos' in nombre_capa:
                
                # Obtener el título de la capa
                titulo_capa = capa.get('Title') or capa.get('title') or nombre_capa
                
                if nombre_capa not in capas_agrupadas:
                    capas_agrupadas[nombre_capa] = {
                        'name': nombre_capa,  # Para WFS
                        'Name': nombre_capa,  # Para WMS (compatibilidad)
                        'title': titulo_capa,
                        'Title': titulo_capa,  # Para WMS (compatibilidad)
                        'wms_available': False,
                        'wfs_available': False,
                        'wms_url': None,
                        'wfs_url': None
                    }
                else:
                    # Actualizar el título si el nuevo es más descriptivo
                    titulo_existente = capas_agrupadas[nombre_capa]['title']
                    if len(titulo_capa) > len(titulo_existente):
                        capas_agrupadas[nombre_capa]['title'] = titulo_capa
                        capas_agrupadas[nombre_capa]['Title'] = titulo_capa
                
                # Marcar disponibilidad según tipo de servicio
                if capa['service_type'] == 'wms':
                    capas_agrupadas[nombre_capa]['wms_available'] = True
                    capas_agrupadas[nombre_capa]['wms_url'] = capa['service_url']
                elif capa['service_type'] == 'wfs':
                    capas_agrupadas[nombre_capa]['wfs_available'] = True
                    capas_agrupadas[nombre_capa]['wfs_url'] = capa['service_url']
                
                # Debug: mostrar estado actual de la capa
                servicios_actuales = []
                if capas_agrupadas[nombre_capa]['wms_available']:
                    servicios_actuales.append("WMS")
                if capas_agrupadas[nombre_capa]['wfs_available']:
                    servicios_actuales.append("WFS")
            
            # Convertir a lista y mostrar resumen
            capas_finales = list(capas_agrupadas.values())
            
            for i, capa in enumerate(capas_finales, 1):
                servicios = []
                if capa['wms_available']:
                    servicios.append("WMS")
                if capa['wfs_available']:
                    servicios.append("WFS")
            
            # Debug adicional: detectar nombres similares que podrían ser duplicados
            nombres_capas = [capa['name'] for capa in capas_finales]
            for i, nombre in enumerate(nombres_capas):
                
            # Buscar nombres que podrían ser duplicados
            for i, nombre1 in enumerate(nombres_capas):
                for j, nombre2 in enumerate(nombres_capas[i+1:], i+1):
                    if nombre1.lower().strip() == nombre2.lower().strip():
                    elif abs(len(nombre1) - len(nombre2)) <= 2 and nombre1.replace(' ', '') == nombre2.replace(' ', ''):
            
            # Verificación final: asegurar que no hay duplicados
            nombres_verificados = set()
            capas_sin_duplicados = []
            
            for capa in capas_finales:
                nombre = capa.get('name') or capa.get('Name')
                if nombre not in nombres_verificados:
                    nombres_verificados.add(nombre)
                    capas_sin_duplicados.append(capa)
                else:
            
            
            # Mostrar capas encontradas para enviar al frontend
            for i, capa in enumerate(capas_sin_duplicados, 1):
                servicios = []
                if capa['wms_available']:
                    servicios.append("WMS")
                if capa['wfs_available']:
                    servicios.append("WFS")
            
            # Verificación final: asegurar que no hay duplicados
            nombres_verificados = set()
            capas_sin_duplicados = []
            
            for capa in capas_finales:
                nombre = capa.get('name') or capa.get('Name')
                if nombre not in nombres_verificados:
                    nombres_verificados.add(nombre)
                    capas_sin_duplicados.append(capa)
                else:
            
            """
            # FIN DEL CÓDIGO COMENTADO - Todo el procesamiento GetCapabilities se movió al frontend

            return JsonResponse(response_data, safe=False)

        except requests.exceptions.Timeout:
            return JsonResponse({'error': 'Timeout al conectar con el servicio CSW'}, status=408)
        except requests.exceptions.RequestException as e:
            return JsonResponse({'error': f'Error de conexión: {str(e)}'}, status=400)
        except ET.ParseError as e:
            return JsonResponse({'error': 'Error al procesar la respuesta XML del servicio CSW'}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'Internal server error'}, status=500)