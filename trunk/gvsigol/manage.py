#!/usr/bin/env python
import os
import sys

#reload(sys)
#sys.setdefaultencoding('ISO-8859-1')

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gvsigol.settings")
    # CMI: to correctly use it from command line
    #sys.path.append("/home/cesar/projects/scolab/gvsig-online/wsgol2/app_dev")
    # END CMI

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

