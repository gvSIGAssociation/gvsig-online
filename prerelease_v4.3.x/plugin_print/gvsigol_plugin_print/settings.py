# -*- coding: utf-8 -*-
import environ
import os

print('INFO: Loading plugin print.')

env_plugin_print = environ.Env(
    PRINT_URL=(str,'/print'),
    PRINT_LEGAL_ADVICE=(str,'La información y cartografía disponible en este geoportal es propiedad de ........')
)

PRINT_PROVIDER = {
    'url': env_plugin_print('PRINT_URL'),
    'legal_advice': env_plugin_print('PRINT_LEGAL_ADVICE'),
    'default_scales': [10000000, 5000000, 1000000, 500000, 250000, 100000, 50000, 25000, 10000, 5000, 2000, 1000, 500]
}