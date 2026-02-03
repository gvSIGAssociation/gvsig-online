# -*- coding: utf-8 -*-
from lxml import etree as ET
from builtins import str as text
from abc import ABCMeta, abstractmethod
from future.utils import with_metaclass

_registry = []
_CONFIG = {'DEFAULT_MANAGER': None}


class BaseStandardManager(with_metaclass(ABCMeta, object)):
    def get_code(self):
        """
        A string identifying the metadata standard managed by this class, e.g. "ISO19139:2007"
        """
        pass
    
    def get_priority(self):
        """
        The priority is used to decide which manager should be used to update a metadata record.
        If several managers are able to update a record (according to the can_update() method,
        then the one with higher priority will be selected.
        """
        return 100
    
    @abstractmethod
    def get_updater_instance(self, metadata_record):
        pass
    @abstractmethod
    def get_reader_instance(self, metadata_record):
        pass
    
    def get_updater(self, metadata_record):
        if self.can_update(metadata_record):
            return self.get_updater_instance(metadata_record)
        return None
    def get_reader(self, metadata_record):
        if self.can_extract(metadata_record):
            return self.get_reader_instance(metadata_record)
        return None
    
    @abstractmethod
    def can_update(self, metadata_record):
        """
        Whether this manager is able to update the provided metadata record.
        Note that a manager might be read/only, so it would be able to extract
        information from the record but not to update it. 
        """
        pass
    
    @abstractmethod
    def can_extract(self, metadata_record):
        """
        Whether this manager is able to parse and extract information from
        the provided metadata record.
        """
        pass
    
    @abstractmethod
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

class XmlStandardReader(object):
    def __init__(self, metadata_record):
        if ET.iselement(metadata_record):
            self.tree = metadata_record
        else:
            self.tree = ET.fromstring(metadata_record)
    @abstractmethod
    def get_title(self, extent_tuple, thumbnail_url):
        pass
    @abstractmethod
    def get_abstract(self, extent_tuple, thumbnail_url):
        pass
    
    @abstractmethod
    def get_identifier(self):
        pass

    @abstractmethod
    def get_crs(self):
        pass

    @abstractmethod
    def get_transfer_options(self):
        pass

    
    def tostring(self, encoding='unicode'):
        return ET.tostring(self.tree, encoding=encoding)

def _prioritysorter(item):
    return item.get_priority()

def register(standard_manager, default=False):
    _registry.append(standard_manager)
    _registry.sort(key=_prioritysorter, reverse=True)
    if default:
        _CONFIG['DEFAULT_MANAGER'] = standard_manager

def get_updater(metadata_record):
    tree = ET.fromstring(metadata_record)
    for manager in _registry:
        updater = manager.get_updater(tree)
        if updater:
            return updater

def get_reader(metadata_record):
    tree = ET.fromstring(metadata_record)
    for manager in _registry:
        reader = manager.get_reader(tree)
        if reader:
            return reader

def create(mdtype, mdfields, mdcode=None):
    if not mdcode:
        return _CONFIG['DEFAULT_MANAGER'].create(mdtype, mdfields)
    for manager in _registry:
        if manager.get_code() == mdcode:
            return manager.create(mdtype, mdfields)
