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

#GTFS_CRONTAB = "2 0 * * *"
#GTFS_SCRIPT  = "##GTFS_SCRIPT##"

import environ


print('INFO: Loading plugin_trip_planner.')

env_trip_planner = environ.Env(
    GTFS_CRONTAB=(str,'2 0 * * *'),
    GTFS_SCRIPT=(str,'mkdir -p /var/www/media/data/GTFS; rm -f /var/otp/graphs/vlc/*.zip; cp /var/www/media/data/GTFS/*.zip /var/otp/graphs/vlc/; java -Xmx2G -jar /var/otp/otp-1.4.0-shaded.jar --build /var/otp/graphs/vlc; sudo service otp restart')
)

GTFS_CRONTAB = env_trip_planner('GTFS_CRONTAB')
GTFS_SCRIPT  = env_trip_planner('GTFS_SCRIPT')