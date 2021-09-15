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

from django.shortcuts import render, HttpResponse, redirect, render
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

from .utils import get_actions

from actstream import action
from actstream.models import Action

from dateutil import parser
from datetime import datetime
from importlib import import_module
from django.contrib.contenttypes.models import ContentType
from builtins import str as text


@csrf_exempt
def register_action(request):
    if request.method == 'POST':

        actor_id = request.POST.get('actor_id')
        actor_type = request.POST.get('actor_type')
        if not actor_type:
            actor_type = 'user'
        actor_app = request.POST.get('actor_app')
        target_id = request.POST.get('target_id')
        target_type = request.POST.get('target_type')
        target_app = request.POST.get('target_app')
        action_object_id = request.POST.get('action_object_id')
        action_object_type = request.POST.get('action_object_type')
        action_object_app = request.POST.get('action_object_app')

        actor_class = get_class_from_content_type(actor_app, actor_type)
        actor = None
        if actor_class and actor_id:
            actor = actor_class.objects.get(id=actor_id)

        action_object_class = get_class_from_content_type(action_object_app, action_object_type)
        action_object = None
        if action_object_class and action_object_id:
            action_object = action_object_class.objects.get(id=action_object_id)

        target_class = get_class_from_content_type(target_app, target_type)
        target = None
        if target_class and target_id:
            target = target_class.objects.get(id=target_id)

        verb = request.POST.get('verb')

        data = request.POST.get('data')
        description = request.POST.get('description')


        try:
            if not data:
                action.send(actor, verb=verb, action_object=action_object, target=target, description=description)
            else:
                action.send(actor, verb=verb, action_object=action_object, target=target, data=data, description=description)

            result = {
                'status' : 'OK'
            }

        except Exception as e:
            result = {
                'status' : 'ERROR',
                'msg': str(e)
            }

        return HttpResponse(json.dumps(result, indent=4), content_type='application/json')

@csrf_exempt
def get_registered_actions(request, plugin_name, action_name):
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
            except Exception as e:
                print("Failed get end date", e)


        start_date = request.POST.get('start_date')
        start_date_string = None
        if start_date:
            try:
                dt = parser.parse(start_date)
                start_date_py = datetime(dt.year, dt.month, dt.day,dt.hour, dt.minute, dt.second)
                start_date_string = start_date_py.strftime("'%Y/%m/%d %H:%M:%S'")
            except Exception as e:
                print("Failed get start date", e)


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


def get_class_from_content_type(content_type_app, content_type_name):
    if content_type_app:
        content_type_app = content_type_app.lower()
    if content_type_name:
        content_type_name = content_type_name.lower()
    if content_type_app and content_type_app.__len__() > 0 and content_type_name and content_type_name.__len__() > 0:
        cctt = ContentType.objects.filter(app_label=content_type_app, model=content_type_name)
        if cctt.__len__() > 0:
            model_class = cctt[0].model_class()
            return model_class

    if content_type_name and content_type_name.__len__() > 0:
        cctt = ContentType.objects.filter(model=content_type_name)
        if cctt.__len__() > 0:
            model_class = cctt[0].model_class()
            return model_class

    if content_type_name and content_type_name.__len__() > 0:
        cctt = ContentType.objects.get(id=content_type_name)
        model_class = cctt.model_class()
        return model_class

    return None

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
                targets[target_bd.id] = text(getattr(target_bd, field_name))
            else:
                targets[target_bd.id] = text(target_bd)

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
                #print(app)
                if hasattr(mod, 'STATISTICS'):
                    #print(mod.STATISTICS)
                    translated_stats = []
                    for stat in mod.STATISTICS:
                        stat["title"] = _(stat["title"])
                        stat["target_title"] = _(stat["target_title"])
                        statistics_conf.append(stat)
        except:
            pass

    users = User.objects.all()
    response = {
        'users': users,
        'statistics_conf': statistics_conf
    }
    return render(request, 'statistics_list.html', response)
