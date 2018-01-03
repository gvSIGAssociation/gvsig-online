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
from models import Survey, SurveySection
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
            return redirect('survey_list')
        
        except Exception as e:
            try:
                msg = e.get_message()
            except:
                msg = _("Error: survey could not be published")
            form.add_error(None, msg)
                
    else:
        form = SurveyForm(instance=survey)
        
        response= {
            'form': form,
            'survey': survey
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
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def survey_section_add(request):
    newTransformationRule = None
    if request.method == 'POST':
        try:
            transformation_id = request.POST.get('transformation_id')
            transformation = Transformation.objects.get(id=transformation_id)
            
            newTransformationRule = TransformationRule()
            field_name = request.POST.get('field_name')
            newTransformationRule.field_name = field_name
            
            field_params = request.POST.get('field_params')
            newTransformationRule.field_params = field_params
            
            newTransformationRule.transformation = transformation
            newTransformationRule.save()
            
            response = {
                'rule' : {
                    'id': newTransformationRule.id,
                    'field_name': newTransformationRule.field_name
                     }
            }
        except Exception as e:
            try:
                msg = e.get_message()
            except:
                msg = _("Error: transformation could not be published")


    if newTransformationRule == None:
        response = {
        }
        
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def survey_section_update(request, survey_section_id):
    transformation_rule = TransformationRule.objects.get(id=transformation_rule_id)
    if request.method == 'POST':
        try:
            field_name = request.POST.get('field_name')
            transformation_rule.field_name = field_name
            
            field_params = request.POST.get('field_params')
            transformation_rule.field_params = field_params
            
            transformation_rule.save()
            
        except Exception as e:
            try:
                msg = e.get_message()
            except:
                msg = _("Error: transformation could not be published")

    response = {
                'rule' : {
                    'id': transformation_rule.id,
                    'field_name': transformation_rule.field_name,
                    'field_params': transformation_rule.field_params
                     }
            }
        
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def survey_section_delete(request, survey_section_id):
    tr_removed = False
    if request.method == 'POST':
        try:
            transformation_rule = TransformationRule.objects.get(id=transformation_rule_id)
            transformation_rule.delete()
            
            response = {
                'rule' : {
                    'id': transformation_rule_id
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



