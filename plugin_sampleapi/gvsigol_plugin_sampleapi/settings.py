# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2024 SCOLAB.

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
@author: <jvhigon@scolab.es>
'''

import environ
import os

print('INFO: Loading sample API')

env = environ.Env(
    THROW_ERROR=(bool,False)
)

THROW_ERROR = env('THROW_ERROR')
