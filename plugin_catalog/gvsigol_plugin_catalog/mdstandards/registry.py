# -*- coding: utf-8 -*-
from lxml import etree as ET
from builtins import str as text

_registry = []
_CONFIG = {'DEFAULT_MANAGER': None}

class BaseStandardManager(object):
    def getcode(self):
        """
        A string identifying the metadata standard managed by this class, e.g. "ISO19139:2007"
        """
        pass
    
    def getpriority(self):
        """
        The priority is used to decide which manager should be used to update a metadata record.
        If several managers are able to update a record (according to the canupdate() method,
        then the one with higher priority will be selected.
        """
        return 100
    
    def getupdaterinstance(self, metadata_record):
        pass
    
    def getupdater(self, metadata_record):
        if self.canupdate(metadata_record):
            return self.getupdaterinstance(metadata_record)
        return None
    def canupdate(self, metadata_record):
        return False
    
    def create(self, mdtype, mdfields):
        pass


class XmlStandardUpdater(object):
    def __init__(self, metadata_record):
        if ET.iselement(metadata_record):
            self.tree = metadata_record
        else:
            self.tree = ET.fromstring(metadata_record)
            
    def update_all(self, extent_tuple, thumbnail_url):
        return self
    
    def tostring(self, encoding='unicode'):
        return ET.tostring(self.tree, encoding=encoding)

def _prioritysorter(item):
    return item.getpriority()

def register(standard_manager, default=False):
    _registry.append(standard_manager)
    _registry.sort(key=_prioritysorter, reverse=True)
    if default:
        _CONFIG['DEFAULT_MANAGER'] = standard_manager

def getupdater(metadata_record):
    tree = ET.fromstring(metadata_record)
    for manager in _registry:
        updater = manager.getupdater(tree)
        if updater:
            return updater

def create(mdtype, mdfields, mdcode=None):
    if not mdcode:
        return _CONFIG['DEFAULT_MANAGER'].create(mdtype, mdfields)
    for manager in _registry:
        if manager.getcode() == mdcode:
            return manager.create(mdtype, mdfields)
