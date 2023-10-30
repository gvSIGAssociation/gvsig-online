# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2023 SCOLAB.

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
@author: Cesar Martinez <cmartinez@scolab.es>
'''

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import sys, os
import glob
import re


class Command(BaseCommand):
    """
    Extracts Javascript translation messages from Javascripts blocks within Django HTML templates
    to a _trans.gvsigol.js file.

    Messages are extracted from gettext("") function calls. A regular expression is used, so
    some false positives may be included in the output file. Multiline gettext calls are not
    detected.

    This step is necessary since djangojs domain in makemessages command fails with some Django
    HTML templates, so we extract the messages to a plain Javascript file which will be later
    processed using makemessages -d djangojs.
    """
    help = "Extracts javascript translation messages from html templates to a plain js file"
    regexp = re.compile(r"gettext *\( *([\"'])((?:(?!\1)[^\\]|\\.)*)\1 *\)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trans_file = None

    def get_file(self, app_path):
        if self.trans_file is None:
            js_folder = os.path.join(app_path, 'static', 'js', 'lib')
            if not os.path.isdir(js_folder):
                os.makedirs(js_folder)
            js_file = os.path.join(js_folder, '_trans.gvsigol.js')
            self.trans_file = open(js_file, 'w', encoding="utf8")
            self.stdout.write(
                'Created file: {}'.format(js_file)
            )
        return self.trans_file
    
    def close_file(self):
        try:
            if self.trans_file is not None:
                self.tran_file.close()
        except:
            pass
        finally:
            self.trans_file = None

    def get_messages(self, template_path, app_path):
        template = open(template_path, 'r', encoding='utf-8')
        for line in template:
            
            for match in self.regexp.finditer(line):
                if match is not None:
                    if match.group(0) != '':
                        try:
                            self.get_file(app_path).write(match.group(0) + ';\n')
                        except Exception as e:
                            print(e)

    def walk_templates(self, app_path):
        templates = os.path.join(app_path, 'templates')
        if os.path.isdir(templates):
            for (dirpath, dirnames, filenames) in os.walk(templates):
                for filename in filenames:
                    self.get_messages(os.path.join(dirpath, filename), app_path)
            self.close_file()


    def handle(self, *args, **options):
        for p in sorted(set(sys.path)):
            if os.path.basename(p) == 'gvsigol':
                for app_name in glob.glob(p + '/gvsigol_*'):
                    print('Processing templates for {}'.format(app_name))
                    app_path = os.path.join(p, app_name)
                    self.walk_templates(app_path)
            else:
                if os.path.isdir(os.path.join(p, "gvsigol_" + os.path.basename(p))):
                    app_name = "gvsigol_" + os.path.basename(p)
                    print('Processing templates for {}'.format(app_name))
                    app_path = os.path.join(p, app_name)
                    self.walk_templates(app_path)
        self.stdout.write(
            self.style.SUCCESS('Successfully extracted Javascript messages from HTML templates')
        )
