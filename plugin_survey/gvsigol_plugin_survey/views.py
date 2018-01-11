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
'''

@author: jbadia <jbadia@scolab.es>
'''
from models import Survey, SurveySection, SurveyUserGroup
from gvsigol_auth.models import UserGroup
from gvsigol_services.models import Layer
from forms import SurveyForm, SurveySectionForm
from gvsigol import settings

from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.views.decorators.http import require_http_methods, require_safe,require_POST, require_GET
from django.contrib.auth.decorators import login_required
from gvsigol_auth.utils import superuser_required, staff_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render_to_response, RequestContext, redirect
from django.http import  HttpResponse
import json
from django.utils.translation import ugettext as _
from django.db import IntegrityError
from django.shortcuts import render
from settings import SURVEY_FUNCTIONS
from django.core.urlresolvers import reverse

import re
import os


    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@staff_required
def survey_list(request):
    survey_list = Survey.objects.all().order_by('id')
    
    response = {
        'surveys': survey_list
    }
    return render_to_response('survey_list.html', response, context_instance=RequestContext(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
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
                        
            newSurvey.save()
            return redirect('survey_update', survey_id=newSurvey.id)
            
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



@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def survey_update(request, survey_id):
    survey = Survey.objects.get(id=survey_id)
    if request.method == 'POST':
        form = SurveyForm(request.POST)
        try:
            name = request.POST.get('name')
            survey.name = name
            
            title = request.POST.get('title')
            survey.title = title
           
            survey.save()
            
            ordered = request.POST.get('order')
    
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
        
        sections = SurveySection.objects.filter(survey_id=survey.id).order_by('order')
        
        response= {
            'form': form,
            'survey': survey,
            'sections': sections
        }
        
    return render(request, 'survey_update.html', response)



@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@staff_required
def survey_delete(request, survey_id):
    try:
        tr = Survey.objects.get(id=survey_id)
        tr.delete()
    except Exception as e:
        return HttpResponse('Error deleting survey: ' + str(e), status=500)

    return redirect('survey_list')


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@staff_required
def survey_update_project(request, survey_id):

    return redirect('survey_list')



@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
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



@login_required(login_url='/gvsigonline/auth/login_user/')
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


@login_required(login_url='/gvsigonline/auth/login_user/')
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




@login_required(login_url='/gvsigonline/auth/login_user/')
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


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def survey_permissions(request, survey_id):
    if request.method == 'POST':
        assigned_read_roups = []
        for key in request.POST:
            if 'read-usergroup-' in key:
                assigned_read_roups.append(int(key.split('-')[2]))
                
        try:     
            survey = Survey.objects.get(id=int(survey_id))
        except Exception as e:
            return HttpResponseNotFound('<h1>Survey not found{0}</h1>'.format(survey.name))
        
        agroup = UserGroup.objects.get(name__exact='admin')
        
        read_groups = []
        
        # clean existing groups and assign them again if necessary
        SurveyUserGroup.objects.filter(survey=survey).delete()
        for group in assigned_read_roups:
            try:
                group = UserGroup.objects.get(id=group)
                lrg = SurveyUserGroup()
                lrg.survey = survey
                lrg.user_group = group
                lrg.save()
                #read_groups.append(group)
            except Exception as e:
                pass
                        
        return redirect('survey_list')
    else:
        try:
            survey = Survey.objects.get(pk=survey_id)
            groups = get_all_user_groups_checked_by_survey(survey)   
            return render_to_response('survey_permissions_add.html', {'survey_id': survey.id, 'name': survey.name,  'groups': groups}, context_instance=RequestContext(request))
        except Exception as e:
            return HttpResponseNotFound('<h1>Survey not found: {0}</h1>'.format(survey_id))


def get_all_user_groups_checked_by_survey(survey):
    groups_list = UserGroup.objects.all()
    read_groups = SurveyUserGroup.objects.filter(survey=survey)
    
    groups = []
    for g in groups_list:
        if g.name != 'admin' and g.name != 'public':
            group = {}
            for lrg in read_groups:
                if lrg.user_group_id == g.id:
                    group['read_checked'] = True
            
            group['id'] = g.id
            group['name'] = g.name
            group['description'] = g.description
            groups.append(group)
    
    return groups  


