"""
WSGI config for gvsigol project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gvsigol.settings")

print('INFO wsgi.py: Setting DJANGO_SETTINGS_MODULE to gvsigol.settings')

if os.environ.get("DEBUG_REMOTE") and os.environ.get("DEBUG_REMOTE")=='True' and os.environ.get("UWSGI_ENABLED") and os.environ.get("UWSGI_ENABLED")=='True' :
    #if os.environ.get('RUN_MAIN') or os.environ.get('WERKZEUG_RUN_MAIN'):
    try:
        import debugpy
        debugpy.configure(python="/usr/local/bin/python3") 
        debugpy.listen(("0.0.0.0", 6000))                
        print('INFO: Start the VS Code debugger now, waiting...')                
        debugpy.wait_for_client()
        print('INFO: Ready for debugging on port 6000....') 
    except:
        print('WARNING: Problem loading debugpy.') 
        pass
    #else:
    #    print('INFO: not RUN_MAIN neither WERKZEUG_RUN_MAIN')
            
application = get_wsgi_application()
