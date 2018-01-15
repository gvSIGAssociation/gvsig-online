# -*- coding: utf-8 -*-
from django.utils.translation import ugettext as _
from gvsigol_core import utils as core_utils

supported_srs = tuple((x['code'].replace('EPSG:',''),x['code']+' - '+x['title']) for x in core_utils.get_supported_crs_array())
supported_srs_and_blank = (('', '---------'),) + supported_srs


SURVEY_FUNCTIONS = [{
        'string' : {
            'db_type': 'character_varying',
            'method_name': 'string',
            'description': _('String'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'string',
                'value': ''
                },{ 
                'key': _('Is label'),
                'id': 'is_label',
                'type': 'combostring',
                'values': [['true', _('Yes')], ['false', _('No')]],
                'value': 'true'
                }]
            }
        },{
        'dynamicstring' : {
            'db_type': 'character_varying',
            'method_name': 'dynamicstring',
            'description': _('Multiple String'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'string',
                'value': ''
                }]
            }
        },{
        'integer' : {
            'db_type': 'integer',
            'method_name': 'integer',
            'description': _('Integer'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'integer',
                'value': ''
                },{ 
                'key': _('Min'),
                'id': 'min',
                'type': 'integer',
                'value': ''
                },{ 
                'key': _('Max'),
                'id': 'max',
                'type': 'integer',
                'value': ''
                }]
            }
        },{
        'double' : {
            'db_type': 'double',
            'method_name': 'double',
            'description': _('Double'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'double',
                'value': ''
                },{ 
                'key': _('Min'),
                'id': 'min',
                'type': 'double',
                'value': ''
                },{ 
                'key': _('Max'),
                'id': 'max',
                'type': 'double',
                'value': ''
                }]
            }
        },{
        'date' : {
            'db_type': 'date',
            'method_name': 'date',
            'description': _('Date'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'date',
                'value': ''
                }]
            }
        },{
        'time' : {
            'db_type': 'timestamp',
            'method_name': 'time',
            'description': _('Time'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'time',
                'value': ''
                }]
            }
        },{
        'label' : {
            'db_type': 'character_varying',
            'method_name': 'label',
            'description': _('Label'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'string',
                'value': ''
                },{ 
                'key': _('Size'),
                'id': 'size',
                'type': 'integer',
                'value': '20'
                },{ 
                'key': _('URL'),
                'id': 'url',
                'type': 'string',
                'value': ''
                }]
            }
        },{
        'labelwithline' : {
            'db_type': 'character_varying',
            'method_name': 'labelwithline',
            'description': _('Label with line'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'string',
                'value': ''
                },{ 
                'key': _('Size'),
                'id': 'size',
                'type': 'integer',
                'value': '20'
                },{ 
                'key': _('URL'),
                'id': 'url',
                'type': 'string',
                'value': ''
                }]
            }
        },{
        'boolean' : {
            'db_type': 'boolean',
            'method_name': 'boolean',
            'description': _('Boolean'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'boolean',
                'value': ''
                }]
            }
        },{
        'stringcombo' : {
            'db_type': 'character_varying',
            'method_name': 'stringcombo',
            'description': _('Stringcombo'),
            'fields' : [{ 
                'key': _('Item'),
                'id': 'item',
                'type': 'stringcombo',
                'value': ''
                }]
            }
        },{
        'multistringcombo' : {
            'db_type': 'character_varying',
            'method_name': 'multistringcombo',
            'description': _('Multistringcombo'),
            'fields' : [{ 
                'key': _('Item'),
                'id': 'item',
                'type': 'multistringcombo',
                'value': ''
                }]
            }
        },{
        'connectedstringcombo' : {
            'db_type': 'character_varying',
            'method_name': 'connectedstringcombo',
            'description': _('Connected Stringcombo'),
            'fields' : [{ 
                'key': _('Item'),
                'id': 'item',
                'type': 'connectedstringcombo',
                'value': ''
                }]
            }
        },{
        'pictures' : {
            'db_type': '',
            'method_name': 'pictures',
            'description': _('Pictures'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'pictures',
                'value': ''
                }]
            }
        },{
        'sketch' : {
            'db_type': '',
            'method_name': 'sketch',
            'description': _('Sketch'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'sketch',
                'value': ''
                }]
            }
        },{
        'map' : {
            'db_type': 'character_varying',
            'method_name': 'map',
            'description': _('Map'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'map',
                'value': ''
                }]
            }
        },{
        'hidden' : {
            'db_type': 'character_varying',
            'method_name': 'hidden',
            'description': _('Hidden'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'string',
                'value': ''
                }]
            }
        },{
        'primary_key' : {
            'db_type': 'character_varying',
            'method_name': 'primary_key',
            'description': _('Primary key'),
            'fields' : [{ 
                'key': _('Value'),
                'id': 'value',
                'type': 'string',
                'value': ''
                }]
            }
        }
    ]