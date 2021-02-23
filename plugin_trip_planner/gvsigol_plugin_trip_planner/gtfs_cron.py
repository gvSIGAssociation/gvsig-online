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
@author: Jose Badia <jbadia@scolab.es>
'''


from django.apps import AppConfig
from gvsigol.settings import CRONTAB_ACTIVE

import threading
import schedule
import time
import imp

sch = schedule.default_scheduler
job_thread = None

class gtfs_schedule_thread(threading.Thread):
    def __init__(self, s):
        threading.Thread.__init__(self)
        self.daemon = True  # OK for main to exit even if instance is still running
        self.schedule = s
        self.continue_loop = True
    
    def run(self):
        while self.continue_loop:
            #print "############################ "+self.name+"("+str(self.ident)+") in loop with " + str(self.schedule.jobs.__len__())
            self.schedule.run_pending()
            #gevent.sleep(1)
            time.sleep(60) # run each minute
            
    def stop(self):
        self.continue_loop = False
        
        

class trip_planner_schedule_tasks(AppConfig):
    name = 'gvsigol_plugin_trip_planner'
    verbose_name = "Task Manager for downloading GTFS files and recreating the Graph object"
    
    def thread_launcher(self):
        while 1:
            global sch
            #print "############################ 12341234 in loop with " + str(sch.jobs.__len__())
            sch.run_pending()
            #gevent.sleep(1)
            time.sleep(15)
    
    def ready(self):
        if CRONTAB_ACTIVE:
            print('Manager de tareas programadas..... ON')
            #socketvar = socket.socket
            #if socket.socket is greenlet.socket.socket:
            #print gevent.socket
            #g = gevent.spawn(self.thread_launcher)
            #g.join() 
            #else:
            
            global sch, job_thread
            current_thread = threading.current_thread()
            for thread in threading.enumerate():
                if thread == current_thread:
                    continue
                if isinstance(thread, gtfs_schedule_thread):
                    job_thread = thread
            
            if job_thread == None:
                job_thread = gtfs_schedule_thread(sch)
                job_thread.start()
            
            print("Starting cron....")
            spam_info = imp.find_module('gvsigol_auth')
            spam = imp.load_module('gvsigol_auth', *spam_info)
            
            from .views import initialize_trip_planner_cron
            
            initialize_trip_planner_cron(True)
            
        else:
            print('Manager de tareas programadas..... OFF')

    
    def remove_job(self, id):
        global sch
        print("############################    schedule=" + str(sch))
        for job in sch.jobs:
            for tag in job.tags:
                if tag == 'trip-planner-tasks':
                    sch.cancel_job(job)
                    if self.job_thread != None:
                        self.job_thread.continue_loop = False
                    self.job_thread = gtfs_schedule_thread(sch)
                    self.job_thread.start()
                    
    def run_job(self, id):
        global sch
        print("############################    schedule=" + str(sch))
        for job in sch.jobs:
            for tag in job.tags:
                if tag == 'trip-planner-tasks':
                    #job.run()
                    if self.job_thread != None:
                        self.job_thread.continue_loop = False
                    self.job_thread = gtfs_schedule_thread(sch)
                    self.job_thread.start()
        

    
    def initialize_trip_planner_gtfs_cron(self, is_cron_activated, time_update_programmed, interval_update_programmed, unit_update_programmed):
        global sch
        print("############################ 1- schedule.jobs=" + str(sch.jobs.__len__()))
        
        #self.remove_job(str(id))
        sch.clear('trip-planner-tasks')
        
        from .views import cron_trip_planner_refresh
        
        if is_cron_activated:
            days = "all"
            dt = time_update_programmed
            hour = '00:00'
            if dt:
                hour = "{:02d}:{:02d}".format(dt.hour, dt.minute)
            
            if interval_update_programmed and unit_update_programmed:
                time_value = interval_update_programmed
                time_unit = unit_update_programmed
                if time_unit == 'minutes':
                    sch.every(time_value).minutes.do(cron_trip_planner_refresh, id).tag('trip-planner-tasks', 'trip-planner-tasks')
                    print(("schedule.every("+str(time_value)+").minutes.do(action_launched, "+str(id) +").tag('trip-planner-tasks')"))
                if time_unit == 'hours':
                    sch.every(time_value).hours.at(hour).do(cron_trip_planner_refresh, id).tag('trip-planner-tasks', 'trip-planner-tasks')
                    print(("schedule.every("+str(time_value)+").hours.at("+hour+").do(action_launched, "+str(id) +").tag('trip-planner-tasks')"))
                if time_unit == 'days':
                    sch.every(time_value).days.at(hour).do(cron_trip_planner_refresh, id).tag('trip-planner-tasks', 'trip-planner-tasks')
                    print(("schedule.every("+str(time_value)+").days.at("+hour+").do(action_launched, "+str(id) +").tag('trip-planner-tasks')"))
            else:
                if hour:
                    sch.every(days).days.at(hour).do(cron_trip_planner_refresh, id).tag('trip-planner-tasks', 'trip-planner-tasks')
                    print(("schedule.every("+str(time_value)+").days.at("+hour+").do(action_launched, "+str(id) +").tag('trip-planner-tasks')"))
            
            #if not is_first_time:
                #self.run_job(str(id))
         
        print("############################ 2- schedule.jobs=" + str(sch.jobs.__len__()))
                       
