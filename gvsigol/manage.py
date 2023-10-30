#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gvsigol.settings")
    # CMI: to correctly use it from command line
    #sys.path.append("/home/cesar/projects/scolab/gvsig-online/wsgol2/app_dev")
    # END CMI
    print('INFO: Setting DJANGO_SETTINGS_MODULE to gvsigol.settings')

    if os.environ.get("DEBUG_REMOTE") and os.environ.get("DEBUG_REMOTE")=='True':
        if os.environ.get('RUN_MAIN') or os.environ.get('WERKZEUG_RUN_MAIN'):
            try:
                import debugpy
                debugpy.listen(("0.0.0.0", 6000))                
                print('INFO: Start the VS Code debugger now, waiting...')                
                debugpy.wait_for_client()
                print('INFO: Ready for debugging on port 6000....') 
            except:
                print('WARNING: Problem loading debugpy.') 
                pass
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "ERROR: Couldn't import Django. Check PYTHONPATH and virtualenv"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
