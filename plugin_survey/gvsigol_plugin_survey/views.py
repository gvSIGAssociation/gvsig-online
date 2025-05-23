# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2007-2015 gvSIG Association.

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
from geoserver.layergroup import LayerGroup
'''

@author: jbadia <jbadia@scolab.es>
'''
from .models import Survey, SurveySection, SurveyReadGroup, SurveyWriteGroup
from gvsigol_auth.models import UserGroup, UserGroupUser
from gvsigol_core.models import Project, ProjectRole, ProjectLayerGroup
from gvsigol_services.models import Workspace, Datastore, Layer, LayerGroup, LayerReadRole, LayerWriteRole
from gvsigol_services import geographic_servers
from gvsigol_services.views import layer_delete_operation
from .forms import SurveyForm, SurveySectionForm, UploadFileForm
from gvsigol_core import utils as core_utils
from gvsigol_services import utils
from gvsigol import settings
from gvsigol_services.backend_postgis import Introspect

from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.views.decorators.http import require_http_methods, require_safe,require_POST, require_GET
from django.contrib.auth.decorators import login_required
from gvsigol_auth import auth_backend
from gvsigol_auth.utils import superuser_required, staff_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
import json
from django.utils.translation import ugettext as _
from django.db import IntegrityError
from django.shortcuts import render
from .settings import SURVEY_FUNCTIONS
from django.urls import reverse
from gvsigol.settings import LANGUAGES

import re
import unicodedata
import os
import shutil
import tempfile
import logging
import sqlite3

DEFAULT_BUFFER_SIZE = 1048576
## 2xx: upload errors
SYNCERROR_UPLOAD="ERROR_GOL_200-Error on sync upload"
SYNCERROR_LAYER_NOT_LOCKED="ERROR_GOL_201-Layer is not locked: {0}"
SYNCERROR_FILEPARAM_MISSING="ERROR_GOL_202-'fileupload' param missing or incorrect"
SYNCERROR_FILE_MISSING='ERROR_GOL_203-No valid file was provided'
SYNCERROR_INCONSISTENT_LAYER_STATUS="ERROR_GOL_204-Inconsistent status for layer: {0}"
SYNCERROR_INVALID_DB="ERROR_GOL_205-The file is not a valid Sqlite3 db"
SYNCERROR_UNREADABLE_LAYER="ERROR_GOL_206-The layer can't be read: {0}"

logger = logging.getLogger(__name__)


_valid_name_regex=re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")
    
@login_required()
@require_safe
@staff_required
def survey_list(request):
    admin_role = auth_backend.get_admin_role()
    user_roles = auth_backend.get_roles(request)
    if admin_role in user_roles:
        # Es admin
        surveys = list(Survey.objects.all().order_by('id'))
    else:
        surveys = list(Survey.objects.filter(surveyreadgroup__role__in=user_roles).distinct().order_by('id'))
            
    response = {
        'surveys': surveys
    }
    return render(request, 'survey_list.html', response)


@login_required()
@require_safe
@staff_required
def surveys(request):
    surveys = []
    
    admin_role = auth_backend.get_admin_role()
    user_roles = auth_backend.get_roles(request)
    if admin_role in user_roles:
        # Es admin
        for survey in Survey.objects.all().order_by('id'):
            aux = {
                'name': survey.name,
                'title': survey.title
                }
            
            surveys.append(aux)
    else:
        for survey in Survey.objects.filter(surveyreadgroup__role__in=user_roles).distinct().order_by('id'):
            aux = {
                'name': survey.name,
                'title': survey.title
                }
            
            surveys.append(aux)
            
            
    response = {
        'surveys': surveys
    }
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')




@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def survey_add(request):
    if request.method == 'POST':
        form = SurveyForm(request.POST)
        has_errors = False
        try:
            newSurvey = Survey()

            name = request.POST.get('name')
            newSurvey.name = name
            
            title = request.POST.get('title')
            newSurvey.title = title
            
            datastore = request.POST.get('datastore')
            newSurvey.datastore_id = datastore
            
            exists = False
            projects = Project.objects.all()
            for p in projects:
                if name == p.name:
                    exists = True
            
            if name == '':
                message = _('You must enter an survey name')
                return render(request, 'survey_add.html', {'message': message, 'form': form})
            
            if _valid_name_regex.search(name) == None:
                message = _("Invalid survey name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
                return render(request, 'survey_add.html', {'message': message, 'form': form})
              
            if not exists:     
                newSurvey.save()
                return redirect('survey_update', survey_id=newSurvey.id)
            else:
                message = _('Exists a project with the same name')
                return render(request, 'survey_add.html', {'message': message, 'form': form})
        
       
            #msg = _("Error: fill all the survey fields")
            #form.add_error(None, msg)
            
        except Exception as e:
            try:
                msg = e.get_message()
            except:
                msg = _("Error: survey could not be published")
            form.add_error(None, msg)

    else:
        form = SurveyForm()
        
    return render(request, 'survey_add.html', {'form': form})



@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def survey_update(request, survey_id):
    survey = Survey.objects.get(id=survey_id)
    if request.method == 'POST':
        form = SurveyForm(request.POST)
        try:
            title = request.POST.get('title')
            survey.title = title
           
            datastore = request.POST.get('datastore')
            survey.datastore_id = datastore
           
            survey.save()
            
            ordered = request.POST.get('order')
            
            if ordered.__len__() > 0:
                ids = ordered.split(',')
                count = 0
                for id in ids:
                    section = SurveySection.objects.get(id=id)
                    section.order = count
                    section.save()
                    count = count + 1
            
            return HttpResponseRedirect(reverse('survey_permissions', kwargs={'survey_id': survey_id}))
        
        except Exception as e:
            try:
                msg = e.get_message()
            except:
                msg = _("Error: survey could not be published")
            form.add_error(None, msg)
                
    else:
        form = SurveyForm(instance=survey)
    
    if not request.user.is_superuser:
        form.fields['datastore'].queryset = (Datastore.objects.filter(created_by=request.user.username) |
                  Datastore.objects.filter(defaultuserdatastore__username=request.user.username)).distinct().order_by('name')
    
    sections = SurveySection.objects.filter(survey_id=survey.id).order_by('order')
    
    image = ''
    if survey.project_id:
        p = survey.project
        image = p.image_url
    
    response= {
        'form': form,
        'survey': survey,
        'image': image,
        'sections': sections
    }
        
    return render(request, 'survey_update.html', response)



@login_required()
@require_POST
@staff_required
def survey_delete(request, survey_id):
    try:
        tr = Survey.objects.get(id=survey_id)
        tr.delete()
    except Exception as e:
        return HttpResponse('Error deleting survey: ' + str(e), status=500)

    return redirect('survey_list')




@login_required()
@require_safe
@staff_required
def survey_definition_by_name(request, survey_name):
    survey = Survey.objects.filter(name=survey_name).first()
    if not survey:
        return HttpResponse('Error getting definition of survey: ' + survey_name, status=500)
    return survey_definition(request, survey.id)


@login_required()
@require_safe
@staff_required
def survey_definition(request, survey_id):
    result = []
    try:
        survey = Survey.objects.get(id=survey_id)
        sections = SurveySection.objects.filter(survey_id=survey.id).order_by('order')
        
        for section in sections:
            aux_section = {}
            aux_section["sectionname"] = section.name
            aux_section["sectiontitle"] = section.title
            aux_section["sectiondescription"] = section.title
            definition = '[]'
            if section.definition:
                definition = section.definition
            aux_section["forms"] = json.loads(definition)
            result.append(aux_section)
        
    except Exception as e:
        return HttpResponse('Error getting definition of survey: ' + str(e), status=500)
    
    response = {
            'json': result
        }
    
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')



@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def survey_section_add(request, survey_id):
    newSurveySection = None
    survey = Survey.objects.get(id=survey_id)
    
    if request.method == 'POST':
        try:
            form = SurveySectionForm(request.POST)
            newSurveySection = SurveySection()
            field_name = request.POST.get('name')
            newSurveySection.name = field_name
            
            title = request.POST.get('title')
            newSurveySection.title = title
            
            srs = request.POST.get('srs')
            newSurveySection.srs = srs
            
            definition = request.POST.get('definition')
            newSurveySection.definition = definition
            
            newSurveySection.order = SurveySection.objects.filter(survey_id=survey.id).count()
            
            newSurveySection.survey = survey
            newSurveySection.save()
            
            return redirect('survey_section_update', survey_section_id=newSurveySection.id)
            
        except Exception as e:
            try:
                msg = e.get_message()
            except:
                msg = _("Error: transformation could not be published")


    form = SurveySectionForm()
        
    return render(request, 'survey_section_add.html', {'form': form, 'survey': survey})


@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def survey_section_update(request, survey_section_id):
    newSurveySection = SurveySection.objects.get(id=survey_section_id)
    if request.method == 'POST':
        try:
            form = SurveySectionForm(request.POST)
            field_name = request.POST.get('name')
            newSurveySection.name = field_name
            
            title = request.POST.get('title')
            newSurveySection.title = title
            
            srs = request.POST.get('srs')
            newSurveySection.srs = srs
            
            definition = request.POST.get('definition')
            newSurveySection.definition = definition
            
            newSurveySection.save()
            
            return redirect('survey_update', survey_id=newSurveySection.survey.id)
            
        except Exception as e:
            try:
                msg = e.get_message()
            except:
                msg = _("Error: transformation could not be published")


    form = SurveySectionForm(instance=newSurveySection)
    field_definitions = SURVEY_FUNCTIONS
    params =  {
        'form': form, 
        'section': newSurveySection, 
        'survey': newSurveySection.survey, 
        'field_definitions': json.dumps(field_definitions)
    }
        
    return render(request, 'survey_section_update.html',  params)




@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def survey_section_delete(request, survey_section_id):
    tr_removed = False
    if request.method == 'POST':
        try:
            survey_section = SurveySection.objects.get(id=survey_section_id)
            survey_section.delete()
            
            response = {
                'rule' : {
                    'id': survey_section.id
                     }
            }
            
            tr_removed = True
        except Exception as e:
            try:
                msg = e.get_message()
            except:
                msg = _("Error: transformation could not be removed")


    if not tr_removed:
        response = {
        }
        
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@login_required()
@staff_required
def survey_permissions(request, survey_id):
    if request.method == 'POST':
        assigned_read_roles = []
        assigned_write_roles = []
        for key in request.POST:
            if 'read-usergroup-' in key:
                assigned_read_roles.append(key.split('-')[2])
            if 'write-usergroup-' in key:
                assigned_write_roles.append(key.split('-')[2])
                
        try:     
            survey = Survey.objects.get(id=int(survey_id))
        except Exception as e:
            return HttpResponseNotFound('<h1>Survey not found{0}</h1>'.format(survey.name))
        
        agroup = auth_backend.get_admin_role()
        
        read_roles = []
        
        # clean existing groups and assign them again if necessary
        SurveyReadGroup.objects.filter(survey=survey).delete()
        for role in assigned_read_roles:
            try:
                lrg = SurveyReadGroup()
                lrg.survey = survey
                lrg.role = role
                lrg.save()
                #read_groups.append(group)
            except Exception as e:
                pass
            
        SurveyWriteGroup.objects.filter(survey=survey).delete()
        for role in assigned_write_roles:
            try:
                lrg = SurveyWriteGroup()
                lrg.survey = survey
                lrg.role = role
                lrg.save()
                #read_groups.append(group)
            except Exception as e:
                pass
                        
        return redirect('survey_list')
    else:
        try:
            survey = Survey.objects.get(pk=survey_id)
            rgroups = get_all_read_roles_checked_by_survey(survey)   
            wgroups = get_all_write_roles_checked_by_survey(survey)   
            return render(request, 'survey_permissions_add.html', {'survey_id': survey.id, 'name': survey.name,  'read_groups': rgroups,  'write_groups': wgroups})
        except Exception as e:
            return HttpResponseNotFound('<h1>Survey not found: {0}</h1>'.format(survey_id))


def get_all_read_roles_checked_by_survey(survey):
    role_list = auth_backend.get_all_roles()
    read_roles = SurveyReadGroup.objects.filter(survey=survey)
    
    roles = []
    for r in role_list:
        if r != 'admin' and r != 'public':
            role = {}
            for lrg in read_roles:
                if lrg.role == role:
                    group['read_checked'] = True
            
            role['id'] = r
            role['name'] = r
            role['description'] = ''
            roles.append(group)
    
    return roles  

def get_all_write_roles_checked_by_survey(survey):
    role_list = auth_backend.get_all_roles()
    write_roles = SurveyWriteGroup.objects.filter(survey=survey)
    
    roles = []
    for r in role_list:
        if r != 'admin' and r != 'public':
            role = {}
            for lrg in write_roles:
                if lrg.role == r:
                    group['write_checked'] = True
            
            role['id'] = r
            role['name'] = r
            role['description'] = ''
            roles.append(role)
    
    return roles  

def prepare_string(s):
    return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')).replace (" ", "_").replace ("-", "_").lower()


@login_required()
@require_POST
@staff_required
def survey_update_project(request, survey_id):
    try:
        survey = Survey.objects.get(id=survey_id)
        sections = SurveySection.objects.filter(survey=survey).order_by('order')
        permissions = SurveyReadGroup.objects.filter(survey=survey)
        
        '''
        Create the project
        '''
        if survey.project_id != None:
            project = Project.objects.get(id=survey.project_id)
            project.delete()
        
        
        project = Project(
                    name = survey.name,
                    title = survey.title,
                    description = survey.title,
                    center_lat = 0,
                    center_lon = 0,
                    zoom = 2,
                    extent = '-31602124.97422327,-7044436.526761844,31602124.97422327,7044436.526761844',
                    toc_order = {},
                    toc_mode = 'toc_hidden',
                    created_by = request.user.username,
                    is_public = False
                )
        project.save()
        
        survey.project_id = project.id
        survey.save()
        
        lgname = str(project.id) + '_' + str(survey_id) + '_' + survey.name + '_' + request.user.username
        layergroup = LayerGroup(
            name = lgname,
            title = survey.name,
            cached = False,
            created_by = request.user.username
        )
        layergroup.save()
        
        survey.layer_group_id = layergroup.id
        survey.save()
        
        gs = geographic_servers.get_instance().get_server_by_id(survey.datastore.workspace.server.id)
        gs.reload_nodes()
        
        project_layergroup = ProjectLayerGroup(
            project = project,
            layer_group = layergroup
        )
        project_layergroup.save()
        assigned_layergroups = []
        prj_lyrgroups = ProjectLayerGroup.objects.filter(project_id=project.id)
        for prj_lyrgroup in prj_lyrgroups:
            assigned_layergroups.append(prj_lyrgroup.layer_group.id)
        
        toc_structure = core_utils.get_json_toc(assigned_layergroups)
        project.toc_order = toc_structure
        project.save()
        
        for permission in permissions:
            project_role = ProjectRole(
                project = project,
                role = permission.role
            )
            project_role.save()
            
            
        '''
        Create the layers
        '''
        if project:
            lyorder = 0
            for section in sections:
                survey_section_update_project_operation(request, survey, section, lyorder)
                lyorder = lyorder + 1
            
        response = {
                'result': 'OK'
            }
    
    except Exception as e:
        response = {
                'result': 'Error', 
                'message': str(e)
        
            }
    
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@login_required()
@require_POST
@staff_required
def survey_section_update_project(request, section_id):
    section = SurveySection.objects.get(id=section_id)
    survey = section.survey
    lyorder = 0
    if section.layer_id != None:
        lyorder = section.layer.order

    survey_section_update_project_operation(request, survey, section, lyorder)
    
    response = {
            'result': 'OK'
        }
    
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')



def survey_section_update_project_operation(request, survey, section, lyorder):
    if section.layer_id != None:
        layer_delete_operation(request, section.layer_id)
    
    gs = geographic_servers.get_instance().get_server_by_id(survey.datastore.workspace.server.id)
    try:
        gs.deleteTable(survey.datastore, section.name)
        gs.deleteResource(
            survey.datastore.workspace,
            survey.datastore,
            section.name)
    except:
        pass
    
    geom_type = 'Point'
    fields = []
    field_defs = []
    field_definitions = SURVEY_FUNCTIONS
    if section.definition:
        definitions = json.loads(section.definition)
        for definition in definitions:
            form_name = definition["formname"]
            for item in definition['formitems']:
                item_type = item['type']
                for db_item in field_definitions:
                    for key in db_item:
                        if key == item_type:
                            db_type = db_item[key]['db_type']
                            if db_type != None and db_type.__len__() > 0:
                                aux = {
                                    'id': str(section.id)+'_'+form_name+'_'+item['key'],
                                    'name': form_name+'_'+item['key'],
                                    'type' : db_type
                                }
                                fields.append(aux)
                                
                                field_def = {}
                                field_def['name'] = form_name+'_'+item['key']
                                for id, language in LANGUAGES:
                                    field_def['title-'+id] = item['title']
                                field_def['visible'] = True
                                field_def['editableactive'] = True
                                field_def['editable'] = True
                                for control_field in settings.CONTROL_FIELDS:
                                    if field_def['name'] == control_field['name']:
                                        field_def['editableactive'] = False
                                        field_def['editable'] = False
                                field_def['infovisible'] = True
                                field_defs.append(field_def)
                                
    section.name = prepare_string(section.name)
    gs.createTableFromFields(survey.datastore, section.name, geom_type, section.srs, fields)
    
    # first create the resource on the backend
    try:
        gs.createResource(
            survey.datastore.workspace,
            survey.datastore,
            section.name,
            section.title
        )
    except:
        pass
    
    try:
        gs.setQueryable(
            survey.datastore.workspace.name,
            survey.datastore.name,
            survey.datastore.type,
            section.name,
            True
        )
    except:
        pass
    
        
    layer = Layer(
        datastore = survey.datastore,
        layer_group = survey.layer_group,
        name = section.name,
        title = section.title,
        abstract = section.title,
        type = 'v_PostGIS',
        visible = True,
        queryable =True,
        cached = False,
        single_image = False,
        time_enabled = False,
        highlight = False,
        order = lyorder,
        created_by = request.user.username,
    )
    layer.save()
   
    style_name = survey.datastore.workspace.name + '_' + layer.name + '_default'
    gs.createDefaultStyle(layer, style_name)
    gs.setLayerStyle(layer, style_name, True)
    layer = gs.updateThumbnail(layer, 'create')
    layer.save()
    
    section.layer_id = layer.id
    section.save()
    
    layer_conf = {
        'fields': field_defs
        }
    layer.conf = layer_conf
    layer.save()
    
    core_utils.toc_add_layer(layer)
    gs.createOrUpdateGeoserverLayerGroup(survey.layer_group)
    gs.reload_nodes()


    permissionsr = SurveyReadGroup.objects.filter(survey=survey)
    permissionsw = SurveyWriteGroup.objects.filter(survey=survey)
    groupsr = []
    groupsw = []
    for permission in permissionsr:
        groupsr.append(permission.role)
        
        try:
            lwr = LayerReadRole()
            lwr.layer = section.layer
            lwr.role = permission.role
            lwr.save()
        except:
            pass
        
    for permission in permissionsw:
        groupsw.append(permission.role)
        
        try:
            lwg = LayerWriteRole()
            lwg.layer = section.layer
            lwg.role = permission.role
            lwg.save()
        except:
            pass
                
                
    gs.setLayerDataRules(layer, groupsr, groupsw)
    gs.reload_nodes()



def add_result_from_survey(request, db_name, id, lon, lat, altim, ts, description, text, form, style, isdirty):
    feature_definitions = json.loads(form)
    table_name = feature_definitions['sectionname']
    fields = get_fields_from_definition(feature_definitions['forms'])
    
    survey  = Survey.objects.filter(name=db_name).first()
    section = SurveySection.objects.filter(name=table_name,survey_id=survey.id).first()
    
    if survey and section:
        sql=''
        sql_fields='wkb_geometry,modified_by'
        sql_values="ST_GeomFromEWKT('SRID="+str(section.srs)+";MULTIPOINT(("+str(lon)+" "+str(lat)+"))'),'" + request.user.username + "'"
        for field in fields:
            sql_fields = sql_fields + ',' + field['name']
            value = field['value']
            if field['type'] == 'character_varying':
                value = "'" + field['value'] + "'"
            sql_values = sql_values + ',' + value
            
        sql = '(' + sql_fields + ') VALUES (' + sql_values +')'
        
        params = json.loads(survey.datastore.connection_params)
        host = params['host']
        port = params['port']
        dbname = params['database']
        user = params['user']
        passwd = params['passwd']
        schema = params.get('schema', 'public')
        
        i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
        i.insert_sql(schema, table_name, sql)
        #print sql
        
        
    
def get_fields_from_definition(definitions):
    field_definitions = SURVEY_FUNCTIONS
    fields = []
    for definition in definitions:
        form_name = definition["formname"]
        for item in definition['formitems']:
            item_type = item['type']
            for db_item in field_definitions:
                for key in db_item:
                    if key == item_type:
                        db_type = db_item[key]['db_type']
                        if db_type != None and db_type.__len__() > 0:
                            aux = {
                                'id': form_name+'_'+item['key'],
                                'name': form_name+'_'+item['key'],
                                'type' : db_type,
                                'value': item['value']
                            }
                            fields.append(aux)
                            
    return fields


def handle_uploaded_file(f):
    (index, path) = tempfile.mkstemp(suffix='.gpap', dir='/tmp')
    with open(path, 'a') as itemfile:
        for chunk in f.chunks():
            itemfile.write(chunk)
        itemfile.close()
    return path
    

@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def survey_upload_db(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        #if form.is_valid():
        path = handle_uploaded_file(request.FILES.get('fileupload'))
        
        survey_id = request.POST.get('name')
        survey = Survey.objects.get(id=survey_id)

        if path and survey:
            conn = None
            try:
                conn = sqlite3.connect(path) #'/home/jose/Escritorio/geopaparazzi_20180115_185005.gpap')
                db_name = survey.name
                c = conn.cursor()
                for row in c.execute('SELECT _id, lon, lat, altim, ts, description, text, form, style, isdirty FROM notes;'):
                    print(row)
                    add_result_from_survey(request, db_name, row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9])
            except Exception as e:
                logger.exception(SYNCERROR_UPLOAD)
                return HttpResponseBadRequest(SYNCERROR_UPLOAD)
            finally:
                if conn != None:
                    conn.close()
                os.remove(path)
                
        return JsonResponse({'result': 'OK'})
    
    else:
        form = UploadFileForm()
        
        admin_role = auth_backend.get_admin_role()
        user_roles = auth_backend.get_roles(request)
        if admin_role in user_roles:
            # Es admin
            surveys = list(Survey.objects.all().order_by('id'))
        else:
            surveys = list(Survey.objects.filter(surveyreadgroup__role__in=user_roles).distinct().order_by('id'))                
                
        return render(request, 'survey_upload.html', {'form': form,  'surveys': surveys})
    
    



@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def survey_upload(request):
    
    response = {'response': 'OK'}
    return render(request, 'survey_upload.html', response)

        
