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

import requests
import urllib
import os
import datetime
import pytz
import ssl
from dateutil.parser import parse as parsedate
from tzlocal import get_localzone # $ pip install tzlocal
from __builtin__ import False


def download_file(url, dstFile):
    try:
        unverified_context = ssl._create_unverified_context()        
        urllib.urlretrieve(url, dstFile, context = unverified_context)
        return True
    except Exception as e:
        print(e)
        return False
    

def download_file_if_newer(url, dstFile):
    try :
        r = requests.head(url)
        if 'last-modified' in r.headers.keys():
            url_time = r.headers['last-modified']
        else:
            return download_file(url, dstFile)
        url_date = parsedate(url_time)
        
        file_time = datetime.datetime.fromtimestamp(os.path.getmtime(dstFile))
        tz = get_localzone()
        local_dt = tz.localize(file_time)
        utc_dt = local_dt.astimezone(pytz.utc)
    
        if url_date > utc_dt :
            return download_file(url, dstFile)
        else:
            return False
    except requests.exceptions.RequestException as e:
        print e
        return False
