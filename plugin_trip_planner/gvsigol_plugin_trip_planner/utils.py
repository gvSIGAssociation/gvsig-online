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

import datetime
import logging
import os

import pytz
import requests
from dateutil.parser import parse as parsedate
from tzlocal import get_localzone

logger = logging.getLogger(__name__)

# Some GTFS publishers serve their feeds with invalid/self-signed certificates.
# Keep the historical behaviour (no verification) but apply it consistently.
VERIFY_SSL = False
TIMEOUT = (30, 600)  # (connect, read) seconds


def _localize_naive(dt, tz):
    """Naive datetime in local wall time → aware. pytz zones use .localize(); ZoneInfo uses .replace()."""
    if dt.tzinfo is not None:
        return dt
    localize = getattr(tz, "localize", None)
    if localize is not None:
        return localize(dt)
    return dt.replace(tzinfo=tz)


def download_file(url, dstFile):
    """Download url into dstFile atomically. Returns True on success, False otherwise.
    An existing dstFile is left untouched if the download fails."""
    tmpFile = dstFile + '.tmp'
    try:
        os.makedirs(os.path.dirname(dstFile), exist_ok=True)
        with requests.get(url, allow_redirects=True, verify=VERIFY_SSL, timeout=TIMEOUT, stream=True) as r:
            r.raise_for_status()
            with open(tmpFile, 'wb') as out:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    out.write(chunk)
        os.replace(tmpFile, dstFile)
        return True
    except Exception:
        logger.exception('Error downloading %s into %s', url, dstFile)
        try:
            if os.path.exists(tmpFile):
                os.remove(tmpFile)
        except OSError:
            pass
        return False


def download_file_if_newer(url, dstFile):
    """Download url only if the remote Last-Modified is newer than dstFile.
    Returns True if a new file was downloaded."""
    try:
        r = requests.head(url, allow_redirects=True, verify=VERIFY_SSL, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.exceptions.RequestException:
        logger.exception('Error checking %s', url)
        return False

    url_time = r.headers.get('last-modified')
    if not url_time:
        return download_file(url, dstFile)

    url_date = parsedate(url_time)
    file_time = datetime.datetime.fromtimestamp(os.path.getmtime(dstFile))
    utc_dt = _localize_naive(file_time, get_localzone()).astimezone(pytz.utc)

    if url_date > utc_dt:
        return download_file(url, dstFile)
    return False
