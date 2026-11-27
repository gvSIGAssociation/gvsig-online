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

import logging

import environ

logging.getLogger(__name__).info('Loading plugin_trip_planner.')

# GTFS_SCRIPT is executed with `bash -e -c`, so wildcards work and it stops at the
# first failing command. The environment variable $GTFS_DIR points to the directory
# where the GTFS files are downloaded (MEDIA_ROOT/data/plugin_trip_planner/GTFS).
env_trip_planner = environ.Env(
    GTFS_CRONTAB=(str, '2 0 * * *'),
    GTFS_SCRIPT=(str, 'rm -f /var/otp/graphs/vlc/*.zip; cp "$GTFS_DIR"/*.zip /var/otp/graphs/vlc/; java -Xmx2G -jar /var/otp/otp-1.4.0-shaded.jar --build /var/otp/graphs/vlc; sudo service otp restart')
)

GTFS_CRONTAB = env_trip_planner('GTFS_CRONTAB')
GTFS_SCRIPT  = env_trip_planner('GTFS_SCRIPT')