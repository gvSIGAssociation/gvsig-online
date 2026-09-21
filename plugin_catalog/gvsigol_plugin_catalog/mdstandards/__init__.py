# -*- coding: utf-8 -*-


from .iso19139_2007 import Iso19139_2007Manager
from .iso19115_3 import Iso19115_3Manager
from .iso19115_3_mgb import Iso19115_3MgbManager
from . import registry

# ISO 19139 remains the default for new records unless CATALOG_METADATA_STANDARD says otherwise.
registry.register(Iso19139_2007Manager(), True)
registry.register(Iso19115_3Manager())
registry.register(Iso19115_3MgbManager())