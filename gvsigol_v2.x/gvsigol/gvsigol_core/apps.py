from __future__ import unicode_literals

from django.apps import AppConfig
import threading
import schedule
import time

sch = schedule.default_scheduler
job_thread = None

class my_schedule_thread(threading.Thread):
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
            time.sleep(5)
            
    def stop(self):
        self.continue_loop = False

class GvsigolCoreConfig(AppConfig):
    name = 'gvsigol_core'
    label = 'gvsigol_core'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('Project'))

        try:
            # ensure we have a proper environment
            self.config_gdaltools()
            
            print('Scheduled tasks manager..... ON')
            global sch, job_thread
            current_thread = threading.current_thread()
            for thread in threading.enumerate():
                if thread == current_thread:
                    continue
                if isinstance(thread, my_schedule_thread):
                    job_thread = thread
            
            if job_thread == None:
                job_thread = my_schedule_thread(sch)
                job_thread.start()
            
            print("Starting tasks....")
            self.init_tasks()
            
        except:
            pass
        
    def init_tasks(self):
        from gvsigol_core import tasks
        schedule.every().hour.do(tasks.clean_shared_views)

    def config_gdaltools(self):
        import gdaltools
        from gvsigol.settings import GDALTOOLS_BASEPATH
        
        if GDALTOOLS_BASEPATH and GDALTOOLS_BASEPATH != '':
            gdaltools.Wrapper.BASEPATH = GDALTOOLS_BASEPATH
