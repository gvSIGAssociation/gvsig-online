# -*- coding: utf-8 -*-


from .iso19139_2007 import Iso19139_2007Manager
from . import registry
registry.register(Iso19139_2007Manager(), True)