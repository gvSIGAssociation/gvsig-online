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
from gvsigol import settings
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.shortcuts import render_to_response, RequestContext, HttpResponse, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from gvsigol_core.models import Project
from gvsigol_auth import services as auth_services
from gvsigol_auth.utils import superuser_required, staff_required
from gvsigol_services import geographic_servers
from gvsigol_services import utils as services_utils
from gvsigol_services.models import Workspace, Server
from django.views.decorators.csrf import csrf_exempt
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
import json
import re

from utils import get_actions

from actstream import action
from actstream.models import Action

from dateutil import parser
from datetime import datetime
from importlib import import_module
from django.contrib.contenttypes.models import ContentType

@csrf_exempt
def get_target_by_user(request, plugin_name, action_name):
    if request.method == 'POST':
        operation_id = plugin_name +'/' + action_name
        #actions = Action.objects.get(verb=operation_id)

        username = request.POST.get('username')
        user_id = 'all' #by default for all users
        if username:
            if username == 'anonymous' or username == 'all': #special cases: 'all' and 'anonymous' (in 'anonymous', target id and contenttype will be the same)
                user_id = username
            else:
                users = User.objects.filter(username=username) #username is a concrete name
                if users.__len__() > 0:
                    user_id = users[0].id

        #num_rows = request.POST.get('number_rows')
        end_date = request.POST.get('end_date')
        end_date_string = None
        if end_date:
            try:
                dt = parser.parse(end_date)
                end_date_py = datetime(dt.year, dt.month, dt.day,dt.hour, dt.minute, dt.second)
                end_date_string = end_date_py.strftime("'%Y/%m/%d %H:%M:%S'")
            except StandardError, e:
                print "Failed get end date", e


        start_date = request.POST.get('start_date')
        start_date_string = None
        if start_date:
            try:
                dt = parser.parse(start_date)
                start_date_py = datetime(dt.year, dt.month, dt.day,dt.hour, dt.minute, dt.second)
                start_date_string = start_date_py.strftime("'%Y/%m/%d %H:%M:%S'")
            except StandardError, e:
                print "Failed get start date", e


        get_count = request.POST.get('get_count') == 'true'
        target_id = None

        group_by_date = request.POST.get('group_by_date') == 'true'
        date_pattern = request.POST.get('date_pattern')

        reverse = request.POST.get('reverse') == 'true'

        actions = get_actions(operation_id, reverse, get_count, user_id, target_id, start_date_string, end_date_string, group_by_date, date_pattern)

        #Operate with the query results
        results = {}

        if get_count:
            results["count"] = actions
            count_results = results
        else:

            results["count"] = actions
            count_results = results
            #count_results = {}
            #for action in actions:
            #    key = str(action[4]) #target_id
            #    if not key in count_results:
            #        count_results[key] = []
            #    count_results[key].append(action[0])


        return HttpResponse(json.dumps(count_results, indent=4), content_type='application/json')


@csrf_exempt
def get_targets_from_content_type(request):
    if request.method == 'POST':
        content_type_id = request.POST.get('content_type_id')
        field_name = request.POST.get('field_name')

        targets_bd = []
        if content_type_id and content_type_id.__len__() > 0:
            cctt = ContentType.objects.get(id=content_type_id)
            model_class = cctt.model_class()
            targets_bd = model_class.objects.all()

        targets = {}
        for target_bd in targets_bd:
            if hasattr(target_bd, field_name):
                targets[target_bd.id] = str(getattr(target_bd, field_name))
            else:
                targets[target_bd.id] = str(target_bd)

        response = {
            'targets': targets
        }

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')



@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def statistics_list(request):
    statistics_conf = []
    for app in settings.INSTALLED_APPS:
        try:
            mod = import_module('%s.settings' % app)
            if mod:
                print app
                if hasattr(mod, 'STATISTICS'):
                    print mod.STATISTICS
                    statistics_conf = statistics_conf + mod.STATISTICS
        except:
            pass


    projects = Project.objects.all()
    users = User.objects.all()
    response = {
        'users': users,
        'projects': projects,
        'statistics_conf': statistics_conf
    }
    return render_to_response('statistics_list.html', response, context_instance=RequestContext(request))
