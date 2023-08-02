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
import json
import logging
import os

from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponse

from gvsigol import settings as core_settings
from gvsigol import settings
from gvsigol_services import utils as servicesutils
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django_sendfile import sendfile

logging.basicConfig()
logger = logging.getLogger(__name__) 


