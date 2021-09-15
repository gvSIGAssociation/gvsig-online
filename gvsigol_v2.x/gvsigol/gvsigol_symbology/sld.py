# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

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
@author: Javi Rodrigo <jrodrigo@scolab.es>
'''
from lxml.etree import parse, Element, XMLSchema, tostring
from lxml import objectify
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen
from tempfile import NamedTemporaryFile
import os
import copy
import logging


class SLDNode(object):
    """
    A base class for all python objects that relate directly to SLD elements.
    An SLDNode contains references to the underlying parent node, underlying
    element node, and the namespace map.

    The SLDNode base class also contains utility methods to construct properties
    for child SLDNode objects.
    """

    _nsmap = {
        'sld': "http://www.opengis.net/sld",
        'ogc': "http://www.opengis.net/ogc",
        'xlink': "http://www.w3.org/1999/xlink",
        'xsi': "http://www.w3.org/2001/XMLSchema-instance"
    }
    """Defined namespaces in SLD documents."""

    def __init__(self, parent, descendant=True):
        """
        Create a new SLDNode. It is not necessary to call this directly, because
        all child classes should initialize the SLDNode internally.

        @type  parent: L{SLDNode}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: Does this element descend from the parent, or is it a sibling?
        """
        if parent is None:
            self._parent = None
        elif descendant:
            self._parent = parent._node
        else:
            self._parent = parent._parent
        self._node = None

    @staticmethod
    def makeproperty(ns, cls=None, name=None, docstring='', descendant=True):
        """
        Make a property on an instance of an SLDNode. If cls is omitted, the
        property is assumed to be a text node, with no corresponding class
        object. If name is omitted, the property is assumed to be a complex
        node, with a corresponding class wrapper.

        @type         ns: string
        @param        ns: The namespace of this property's node.
        @type        cls: class
        @param       cls: Optional. The class of the child property.
        @type       name: string
        @param      name: Optional. The name of the child property.
        @type  docstring: string
        @param docstring: Optional. The docstring to attach to the new property.
        @type  descendant: boolean
        @param descendant: Does this element descend from the parent, or is it a sibling?

        @rtype:  property attribute
        @return: A property attribute for this named property.
        """
        def get_property(self):
            """
            A generic property getter.
            """
            if cls is None:
                xpath = '%s:%s' % (ns, name)
            else:
                xpath = '%s:%s' % (ns, cls.__name__)

            xpath = self._node.xpath(xpath, namespaces=SLDNode._nsmap)
            if len(xpath) == 1:
                if cls is None:
                    return xpath[0].text
                else:
                    elem = cls.__new__(cls)
                    cls.__init__(elem, self, descendant=descendant)
                    return elem
            else:
                return None

        def set_property(self, value):
            """
            A generic property setter.
            """
            if cls is None:
                xpath = '%s:%s' % (ns, name)
            else:
                xpath = '%s:%s' % (ns, cls.__name__)

            xpath = self._node.xpath(xpath, namespaces=SLDNode._nsmap)
            if len(xpath) == 1:
                if cls is None:
                    xpath[0].text = value
                else:
                    xpath[0] = value._node
            else:
                if cls is None:
                    elem = self._node.makeelement('{%s}%s' % (SLDNode._nsmap[ns], name), nsmap=SLDNode._nsmap)
                    elem.text = value
                    self._node.append(elem)
                else:
                    self._node.append(value._node)

        def del_property(self):
            """
            A generic property deleter.
            """
            if cls is None:
                xpath = '%s:%s' % (ns, name)
            else:
                xpath = '%s:%s' % (ns, cls.__name__)

            xpath = self._node.xpath(xpath, namespaces=SLDNode._nsmap)
            if len(xpath) == 1:
                self._node.remove(xpath[0])

        return property(get_property, set_property, del_property, docstring)

    def get_or_create_element(self, ns, name):
        """
        Attempt to get the only child element from this SLDNode. If the node
        does not exist, create the element, attach it to the DOM, and return
        the class object that wraps the node.

        @type    ns: string
        @param   ns: The namespace of the new element.
        @type  name: string
        @param name: The name of the new element.
        @rtype: L{SLDNode}
        @return: The wrapped node, in the parent's property class. This will
                 always be a descendent of SLDNode.
        """
        if len(self._node.xpath('%s:%s' % (ns, name), namespaces=SLDNode._nsmap)) == 1:
            return getattr(self, name)

        return self.create_element(ns, name)

    def create_element(self, ns, name):
        """
        Create an element as a child of this SLDNode.

        @type    ns: string
        @param   ns: The namespace of the new element.
        @type  name: string
        @param name: The name of the new element.
        @rtype: L{SLDNode}
        @return: The wrapped node, in the parent's property class. This will
                 always be a descendent of SLDNode.
        """
        elem = self._node.makeelement('{%s}%s' % (SLDNode._nsmap[ns], name), nsmap=SLDNode._nsmap)
        self._node.append(elem)

        return getattr(self, name)


class CssParameter(SLDNode):
    """
    A css styling parameter. May be a child of L{Fill}, L{Font}, and L{Stroke}.
    """
    def __init__(self, parent, index, descendant=True):
        """
        Create a new CssParameter from an existing StyleItem.

        @type  parent: L{StyleItem}
        @param parent: The parent class object.
        @type   index: integer
        @param  index: The index of the node in the list of all CssParameters in the parent.
        @type  descendant: boolean
        @param descendant: Does this element descend from the parent, or is it a sibling?
        """
        super(CssParameter, self).__init__(parent, descendant=descendant)
        self._node = self._parent.xpath('sld:CssParameter', namespaces=SLDNode._nsmap)[index]

    def get_name(self):
        """
        Get the name attribute.

        @rtype: string
        @return: The value of the 'name' attribute.
        """
        return self._node.attrib['name']

    def set_name(self, value):
        """
        Set the name attribute.

        @type  value: string
        @param value: The value of the 'name' attribute.
        """
        self._node.attrib['name'] = value

    def del_name(self):
        """
        Delete the name attribute.
        """
        del self._node.attrib['name']

    Name = property(get_name, set_name, del_name, "The value of the 'name' attribute.")
    """The value of the 'name' attribute."""

    def get_value(self):
        """
        Get the text content.

        @rtype: string
        @return: The text content.
        """
        return self._node.text

    def set_value(self, value):
        """
        Set the text content.

        @type  value: string
        @param value: The text content.
        """
        self._node.text = value

    def del_value(self):
        """
        Delete the text content.
        """
        self._node.clear()

    Value = property(get_value, set_value, del_value, "The value of the parameter.")
    """The value of the parameter."""

class CssParameters(SLDNode):
    """
    A collection of L{CssParameter} nodes. This is a pythonic helper (list of
    nodes) that does not correspond to a true element in the SLD spec.
    """
    def __init__(self, parent):
        """
        Create a new list of CssParameters from the specified parent node.

        @type  parent: L{StyleItem}
        @param parent: The parent class item.
        """
        super(CssParameters, self).__init__(parent)
        self._node = None
        self._nodes = self._parent.xpath('sld:CssParameter', namespaces=SLDNode._nsmap)

    def __len__(self):
        """
        Get the number of L{CssParameter} nodes in this list.

        @rtype: integer
        @return: The number of L{CssParameter} nodes.
        """
        return len(self._nodes)

    def __getitem__(self, key):
        """
        Get one of the L{CssParameter} nodes in the list.

        @type  key: integer
        @param key: The index of the child node.
        @rtype: L{CssParameter}
        @return: The specific L{CssParameter} node.
        """
        return CssParameter(self, key, descendant=False)

    def __setitem__(self, key, value):
        """
        Set one of the L{CssParameter} nodes in the list with a new value.

        @type    key: integer
        @param   key: The index of the child node.
        @type  value: L{CssParameter}, etree.Element
        @param value: The new value of the specific child node.
        """
        if isinstance(value, CssParameter):
            self._nodes.replace(self._nodes[key], value._node)
        elif isinstance(value, Element):
            self._nodes.replace(self._nodes[key], value)

    def __delitem__(self, key):
        """
        Delete one of the L{CssParameter} nodes from the list.

        @type  key: integer
        @param key: The index of the child node.
        """
        self._nodes.remove(self._nodes[key])

class StyleItem(SLDNode):
    """
    Abstract base class for all nodes that contain a list of L{CssParameter} nodes.
    """
    def __init__(self, parent, name, descendant=True):
        """
        Create a new StyleItem.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type    name: string
        @param   name: The name of the node.
        @type  descendant: boolean
        @param descendant: Does this element descend from the parent, or is it a sibling?
        """
        super(StyleItem, self).__init__(parent, descendant=descendant)
        xpath = self._parent.xpath('sld:' + name, namespaces=SLDNode._nsmap)
        if len(xpath) < 1:
            self._node = self._parent.makeelement('{%s}%s' % (SLDNode._nsmap['sld'], name), nsmap=SLDNode._nsmap)
            self._parent.append(self._node)
        else:
            self._node = xpath[0]

    @property
    def CssParameters(self):
        """
        Get the list of L{CssParameter} nodes in a friendly L{CssParameters} helper list.

        @rtype: L{CssParameters}
        @return: A pythonic list of L{CssParameter} children.
        """
        return CssParameters(self)

    def create_cssparameter(self, name=None, value=None):
        """
        Create a new L{CssParameter} node as a child of this element, and attach it to the DOM.
        Optionally set the name and value of the parameter, if they are both provided.

        @type   name: string
        @param  name: Optional. The name of the L{CssParameter}
        @type  value: string
        @param value: Optional. The value of the L{CssParameter}
        @rtype: L{CssParameter}
        @return: A new style parameter, set to the name and value.
        """
        elem = self._node.makeelement('{%s}CssParameter' % SLDNode._nsmap['sld'], nsmap=SLDNode._nsmap)
        self._node.append(elem)

        if not (name is None or value is None):
            elem.attrib['name'] = name
            elem.text = value

        return CssParameter(self, len(self._node) - 1)
    
class VendorOption(StyleItem):
    """
    Using these options gives more control over how the map looks.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Fill node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(VendorOption, self).__init__(parent, 'VendorOption', descendant=descendant)

    def get_name(self):
        """
        Get the name attribute.

        @rtype: string
        @return: The value of the 'name' attribute.
        """
        return self._node.attrib['name']

    def set_name(self, value):
        """
        Set the name attribute.

        @type  value: string
        @param value: The value of the 'name' attribute.
        """
        self._node.attrib['name'] = value

    def del_name(self):
        """
        Delete the name attribute.
        """
        del self._node.attrib['name']

    Name = property(get_name, set_name, del_name, "The value of the 'name' attribute.")
    """The value of the 'name' attribute."""

    def get_value(self):
        """
        Get the text content.

        @rtype: string
        @return: The text content.
        """
        return self._node.text

    def set_value(self, value):
        """
        Set the text content.

        @type  value: string
        @param value: The text content.
        """
        self._node.text = value

    def del_value(self):
        """
        Delete the text content.
        """
        self._node.clear()

    Value = property(get_value, set_value, del_value, "The value of the parameter.")
    """The value of the parameter."""
    
class VendorOptions(SLDNode):
    """
    A collection of L{VendorOption} nodes. This is a pythonic helper (list of
    nodes) that does not correspond to a true element in the SLD spec.
    """
    def __init__(self, parent):
        """
        Create a new list of VendorOption from the specified parent node.

        @type  parent: L{StyleItem}
        @param parent: The parent class item.
        """
        super(VendorOptions, self).__init__(parent)
        self._node = None
        self._nodes = self._parent.xpath('sld:VendorOption', namespaces=SLDNode._nsmap)

    def __len__(self):
        """
        Get the number of L{VendorOption} nodes in this list.

        @rtype: integer
        @return: The number of L{VendorOption} nodes.
        """
        return len(self._nodes)

    def __getitem__(self, key):
        """
        Get one of the L{VendorOption} nodes in the list.

        @type  key: integer
        @param key: The index of the child node.
        @rtype: L{VendorOption}
        @return: The specific L{VendorOption} node.
        """
        return VendorOption(self, key, descendant=False)

    def __setitem__(self, key, value):
        """
        Set one of the L{VendorOption} nodes in the list with a new value.

        @type    key: integer
        @param   key: The index of the child node.
        @type  value: L{VendorOption}, etree.Element
        @param value: The new value of the specific child node.
        """
        if isinstance(value, VendorOption):
            self._nodes.replace(self._nodes[key], value._node)
        elif isinstance(value, Element):
            self._nodes.replace(self._nodes[key], value)

    def __delitem__(self, key):
        """
        Delete one of the L{VendorOption} nodes from the list.

        @type  key: integer
        @param key: The index of the child node.
        """
        self._nodes.remove(self._nodes[key])


class Fill(StyleItem):
    """
    A style specification for fill types. This class contains a
    L{CssParameters} list, which can include:

        - fill
        - fill-opacity

    This class is a property of any L{Symbolizer}.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Fill node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Fill, self).__init__(parent, 'Fill', descendant=descendant)


class Font(StyleItem):
    """
    A style specification for font types. This class contains a
    L{CssParameters} list, which can include:

        - font-family
        - font-size
        - font-style
        - font-weight

    This class is a property of any L{Symbolizer}.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Font node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Font, self).__init__(parent, 'Font', descendant=descendant)


class LabelPlacement(StyleItem):
    """
    @prop: PropertyName

        I{Type}: string
        
    This class is a property of any L{Symbolizer}.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Font node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(LabelPlacement, self).__init__(parent, 'LabelPlacement', descendant=descendant)


class PointPlacement(StyleItem):
    """
    @prop: PropertyName

        I{Type}: string
        
    This class is a property of any L{Symbolizer}.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Font node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(PointPlacement, self).__init__(parent, 'PointPlacement', descendant=descendant)
        
        
class AnchorPoint(StyleItem):
    """
    @prop: PropertyName

        I{Type}: string
        
    This class is a property of any L{Symbolizer}.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Font node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(AnchorPoint, self).__init__(parent, 'AnchorPoint', descendant=descendant)
        setattr(self.__class__, 'AnchorPointX', SLDNode.makeproperty('sld', name='AnchorPointX',
                docstring="The anchor point x, in pixels."))
        setattr(self.__class__, 'AnchorPointY', SLDNode.makeproperty('sld', name='AnchorPointY',
                docstring="The anchor point y, in pixels."))
        
        
class LinePlacement(StyleItem):
    """
    @prop: PropertyName

        I{Type}: string
        
    This class is a property of any L{Symbolizer}.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Font node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(LinePlacement, self).__init__(parent, 'LinePlacement', descendant=descendant)        
        setattr(self.__class__, 'PerpendicularOffset', SLDNode.makeproperty('sld', name='PerpendicularOffset',
                docstring="Line offset, in pixels."))

class Geometry(StyleItem):
    """
    @prop: PropertyName

        I{Type}: string
        
    This class is a property of any L{Symbolizer}.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Font node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Geometry, self).__init__(parent, 'Geometry', descendant=descendant)


class Function(StyleItem):
    """
    @prop: PropertyName

        I{Type}: string
        
    This class is a property of any L{Symbolizer}.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Font node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Function, self).__init__(parent, 'Function', descendant=descendant)
        setattr(self.__class__, 'PropertyName', SLDNode.makeproperty('ogc', name='PropertyName',
                docstring="The name of the property."))
    
    def create_functionname(self, name=None, value=None):
        """
        Create a new L{VendorOption} node as a child of this element, and attach it to the DOM.
        Optionally set the name and value of the parameter, if they are both provided.

        @type   name: string
        @param  name: Optional. The name of the L{Function}
        @type  value: string
        @param value: Optional. The value of the L{Function}
        @rtype: L{Function}
        @return: A new style parameter, set to the name and value.
        """
        elem = self._node.makeelement('{%s}Function' % SLDNode._nsmap['sld'], nsmap=SLDNode._nsmap)
        self._node.append(elem)

        if not (name is None or value is None):
            elem.attrib['name'] = name
            elem.text = value

        return Function(self, len(self._node) - 1)

       
    def get_name(self):
        """
        Get the name attribute.

        @rtype: string
        @return: The value of the 'name' attribute.
        """
        return self._node.attrib['name']

    def set_name(self, value):
        """
        Set the name attribute.

        @type  value: string
        @param value: The value of the 'name' attribute.
        """
        self._node.attrib['name'] = value

    def del_name(self):
        """
        Delete the name attribute.
        """
        del self._node.attrib['name']

    Name = property(get_name, set_name, del_name, "The value of the 'name' attribute.")
   

class Label(StyleItem):
    """
    @prop: PropertyName

        I{Type}: string
        
    This class is a property of any L{Symbolizer}.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Font node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Label, self).__init__(parent, 'Label', descendant=descendant)
        setattr(self.__class__, 'PropertyName', SLDNode.makeproperty('ogc', name='PropertyName',
                docstring="The name of the property."))
        
class Halo(StyleItem):
    """
    @prop: Radius

        I{Type}: string
        
    This class is a property of any L{Symbolizer}.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Font node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Halo, self).__init__(parent, 'Halo', descendant=descendant)
        setattr(self.__class__, 'Radius', SLDNode.makeproperty('sld', name='Radius',
                docstring="The halo radius, in pixels."))


class Stroke(StyleItem):
    """
    A style specification for stroke types. This class contains a
    L{CssParameters} list, which can include:

        - stroke
        - stroke-dasharray
        - stroke-dashoffset
        - stroke-linecap
        - stroke-linejoin
        - stroke-opacity
        - stroke-width

    This class is a property of any L{Symbolizer}.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Stroke node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Stroke, self).__init__(parent, 'Stroke', descendant=descendant)


class Symbolizer(SLDNode):
    """
    Abstract base class for all symbolizer nodes. Symbolizer nodes are those
    that contain L{Fill}, L{Font}, or L{Stroke} children.

    All derived Symbolizer classes have access to the Fill, Font, and Stroke properties.

    @prop: B{Fill}

        The element that contains the L{CssParameter} nodes for describing the polygon fill styles.

        I{Type}: L{Fill}

    @prop: B{Font}

        The element that contains the L{CssParameter} nodes for describing the font styles.

        I{Type}: L{Font}

    @prop: B{Stroke}

        The element that contains the L{CssParameter} nodes for describing the line styles.

        I{Type}: L{Stroke}
    """
    def __init__(self, parent, name, descendant=True):
        """
        Create a new Symbolizer node. If the specified node is not found in the
        DOM, the node will be created and attached to the parent.

        @type  parent: L{Rule}
        @param parent: The parent class object.
        @type    name: string
        @param   name: The type of symbolizer node. If this parameter ends with
            the character '*', the '*' will get expanded into 'Symbolizer'.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Symbolizer, self).__init__(parent, descendant=descendant)

        if name[len(name) - 1] == '*':
            name = name[0:-1] + 'Symbolizer'

        xpath = self._parent.xpath('sld:%s' % name, namespaces=SLDNode._nsmap)
        if len(xpath) < 1:
            self._node = self._parent.makeelement('{%s}%s' % (SLDNode._nsmap['sld'], name), nsmap=SLDNode._nsmap)
            self._parent.append(self._node)
        else:
            self._node = xpath[0]

        setattr(self.__class__, 'Fill', SLDNode.makeproperty('sld', cls=Fill,
                docstring="The parameters for describing the fill styling."))
        setattr(self.__class__, 'Font', SLDNode.makeproperty('sld', cls=Font,
                docstring="The parameters for describing the font styling."))
        setattr(self.__class__, 'Stroke', SLDNode.makeproperty('sld', cls=Stroke,
                docstring="The parameters for describing the stroke styling."))

    def create_fill(self):
        """
        Create a new L{Fill} element on this Symbolizer.

        @rtype: L{Fill}
        @return: A new fill element, attached to this symbolizer.
        """
        return self.create_element('sld', 'Fill')

    def create_font(self):
        """
        Create a new L{Font} element on this Symbolizer.

        @rtype: L{Font}
        @return: A new font element, attached to this symbolizer.
        """
        return self.create_element('sld', 'Font')

    def create_stroke(self):
        """
        Create a new L{Stroke} element on this Symbolizer.

        @rtype: L{Stroke}
        @return: A new stroke element, attached to this symbolizer.
        """
        return self.create_element('sld', 'Stroke')


class PolygonSymbolizer(Symbolizer):
    """
    A symbolizer for polygon geometries. A PolygonSymbolizer is a child of a
    L{Rule} element.

    @prop: Fill

        The element that contains the L{CssParameter} nodes for describing the
        polygon fill styles.

        I{Type}: L{Fill}

    @prop: Stroke

        The element that contains the L{CssParameter} nodes for describing the line
        styles.

        I{Type}: L{Stroke}
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new PolygonSymbolizer node, as a child of the specified parent.

        @type  parent: L{Rule}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(PolygonSymbolizer, self).__init__(parent, 'Polygon*', descendant)


class LineSymbolizer(Symbolizer):
    """
    A symbolizer for line geometries. A LineSymbolizer is a child of a
    L{Rule} element.

    @prop: Stroke

        The element that contains the L{CssParameter} nodes for describing the line
        styles.

        I{Type}: L{Stroke}
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new LineSymbolizer node, as a child of the specified parent.

        @type  parent: L{Rule}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(LineSymbolizer, self).__init__(parent, 'Line*', descendant)
    
        self._node = self._parent.makeelement('{%s}LineSymbolizer' % SLDNode._nsmap['sld'], nsmap=SLDNode._nsmap)
        self._parent.append(self._node)


class TextSymbolizer(Symbolizer):
    """
    A symbolizer for text labels. A TextSymbolizer is a child of a L{Rule}
    element.

    @prop: Fill

        The element that contains the L{CssParameter} nodes for describing the
        character fill styles.

        I{Type}: L{Fill}
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new TextSymbolizer node, as a child of the specified parent.

        @type  parent: L{Rule}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(TextSymbolizer, self).__init__(parent, 'Text*', descendant=descendant)
        
    @property
    def VendorOptions(self):
        """
        Get the list of L{VendorOption} nodes in a friendly L{VendorOptions} helper list.

        @rtype: L{VendorOptions}
        @return: A pythonic list of L{VendorOption} children.
        """
        return VendorOptions(self)
        
    def create_vendoroption(self, name=None, value=None):
        """
        Create a new L{VendorOption} node as a child of this element, and attach it to the DOM.
        Optionally set the name and value of the parameter, if they are both provided.

        @type   name: string
        @param  name: Optional. The name of the L{VendorOption}
        @type  value: string
        @param value: Optional. The value of the L{VendorOption}
        @rtype: L{VendorOption}
        @return: A new style parameter, set to the name and value.
        """
        elem = self._node.makeelement('{%s}VendorOption' % SLDNode._nsmap['sld'], nsmap=SLDNode._nsmap)
        self._node.append(elem)

        if not (name is None or value is None):
            elem.attrib['name'] = name
            elem.text = value

        return VendorOption(self, len(self._node) - 1)
    
class OnlineResource(StyleItem):
    def __init__(self, parent, descendant=True):
        """
        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(OnlineResource, self).__init__(parent, 'OnlineResource', descendant=descendant)

class ExternalGraphic(Symbolizer):
    """
    @prop: OnlineResource
        I{Type}: OnlineResource

    @prop: Format

        A string describing the format of the image, which may be one of:
            - image/png

        I{Type}: string
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new ExternalGraphic node, as a child of the specified parent.

        @type  parent: L{Graphic}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(ExternalGraphic, self).__init__(parent, 'ExternalGraphic', descendant=descendant)

        setattr(self.__class__, 'Format', SLDNode.makeproperty('sld', name='Format',
                docstring="Format of the image."))
        
    def create_onlineresource(self, url=None):
        """
        Create a new L{ColorMapEntry} node as a child of this element, and attach it to the DOM.
        Optionally set the name and value of the parameter, if they are both provided.

        @type   url: string
        @param  url
        @rtype: L{OnlineResource}
        @return: A new OnlineResource.
        """
        elem = self._node.makeelement('{%s}OnlineResource' % SLDNode._nsmap['sld'], nsmap=SLDNode._nsmap)
        self._node.append(elem)

        elem.attrib['type'] = 'simple'
        elem.attrib['href'] = url

        return OnlineResource(self, len(self._node) - 1)
    
class Mark(Symbolizer):
    """
    A graphic mark for describing points. A Mark is a child of a L{Graphic}
    element.

    @prop: Fill

        The element that contains the L{CssParameter} nodes for describing the
        fill styles.

        I{Type}: L{Fill}

    @prop: Stroke

        The element that contains the L{CssParameter} nodes for describing the
        line styles.

        I{Type}: L{Stroke}

    @prop: WellKnownName

        A string describing the Mark, which may be one of:
            - circle
            - cross
            - square
            - star
            - triangle
            - x

        I{Type}: string
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Mark node, as a child of the specified parent.

        @type  parent: L{Graphic}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Mark, self).__init__(parent, 'Mark', descendant=descendant)

        setattr(self.__class__, 'WellKnownName', SLDNode.makeproperty('sld', name='WellKnownName',
                docstring="The well known name for the mark."))


class Graphic(SLDNode):
    """
    A Graphic node represents a graphical mark for representing points. A
    Graphic is a child of a L{PointSymbolizer} element.

    @prop: Mark

        The element that contains the L{CssParameter} nodes for describing the point styles.

        I{Type}: L{Mark}

    @prop: Opacity

        Bewteen 0 (completely transparent) and 1 (completely opaque)

        I{Type}: float

    @prop: Size

        The size of the graphic, in pixels.

        I{Type}: integer

    @prop: Rotation

        Clockwise degrees of rotation.

        I{Type}: float
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Graphic node, as a child of the specified parent.

        @type  parent: L{PointSymbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Graphic, self).__init__(parent, descendant=descendant)
        xpath = self._parent.xpath('sld:Graphic', namespaces=SLDNode._nsmap)
        if len(xpath) < 1:
            self._node = self._parent.makeelement('{%s}Graphic' % SLDNode._nsmap['sld'], nsmap=SLDNode._nsmap)
            self._parent.append(self._node)
        else:
            self._node = xpath[0]

        setattr(self.__class__, 'Mark', SLDNode.makeproperty('sld', cls=Mark,
                docstring="The graphic's mark styling."))
        setattr(self.__class__, 'Opacity', SLDNode.makeproperty('sld', name='Opacity',
                docstring="The opacity of the graphic."))
        setattr(self.__class__, 'Size', SLDNode.makeproperty('sld', name='Size',
                docstring="The size of the graphic, in pixels."))
        setattr(self.__class__, 'Rotation', SLDNode.makeproperty('sld', name='Rotation',
                docstring="The rotation of the graphic, in degrees clockwise."))


class PointSymbolizer(SLDNode):
    """
    A symbolizer for point geometries. A PointSymbolizer is a child of a
    L{Rule} element.

    @prop: Graphic

        The configuration of the point graphic.

        I{Type}: L{Graphic}
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new PointSymbolizer node, as a child of the specified parent.

        @type  parent: L{Rule}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(PointSymbolizer, self).__init__(parent, descendant=descendant)
        '''
        xpath = self._parent.xpath('sld:PointSymbolizer', namespaces=SLDNode._nsmap)     
        if len(xpath) < 1:
            self._node = self._parent.makeelement('{%s}PointSymbolizer' % SLDNode._nsmap['sld'], nsmap=SLDNode._nsmap)
            self._parent.append(self._node)
        else:
            self._node = xpath[0]
        '''    
        self._node = self._parent.makeelement('{%s}PointSymbolizer' % SLDNode._nsmap['sld'], nsmap=SLDNode._nsmap)
        self._parent.append(self._node)

        setattr(self.__class__, 'Graphic', SLDNode.makeproperty('sld', cls=Graphic,
                docstring="The graphic settings for this point geometry."))
        
class PointSymbolizers(SLDNode):
    """
    A collection of L{PointSymbolizer} nodes. This is a pythonic helper (list of
    nodes) that does not correspond to a true element in the SLD spec.
    """
    def __init__(self, parent):
        """
        Create a new list of PointSymbolizer from the specified parent node.

        @type  parent: L{StyleItem}
        @param parent: The parent class item.
        """
        super(PointSymbolizers, self).__init__(parent)
        self._node = None
        self._nodes = self._parent.xpath('sld:PointSymbolizer', namespaces=SLDNode._nsmap)

    def __len__(self):
        """
        Get the number of L{PointSymbolizer} nodes in this list.

        @rtype: integer
        @return: The number of L{PointSymbolizer} nodes.
        """
        return len(self._nodes)

    def __getitem__(self, key):
        """
        Get one of the L{PointSymbolizer} nodes in the list.

        @type  key: integer
        @param key: The index of the child node.
        @rtype: L{VendorOption}
        @return: The specific L{PointSymbolizer} node.
        """
        return PointSymbolizer(self, key, descendant=False)

    def __setitem__(self, key, value):
        """
        Set one of the L{PointSymbolizer} nodes in the list with a new value.

        @type    key: integer
        @param   key: The index of the child node.
        @type  value: L{PointSymbolizer}, etree.Element
        @param value: The new value of the specific child node.
        """
        if isinstance(value, PointSymbolizer):
            self._nodes.replace(self._nodes[key], value._node)
        elif isinstance(value, Element):
            self._nodes.replace(self._nodes[key], value)

    def __delitem__(self, key):
        """
        Delete one of the L{PointSymbolizer} nodes from the list.

        @type  key: integer
        @param key: The index of the child node.
        """
        self._nodes.remove(self._nodes[key])
        
class ColorMapEntry(StyleItem):
    """
    Using these options gives more control over how the map looks.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Fill node from the specified parent.

        @type  parent: L{Symbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(ColorMapEntry, self).__init__(parent, 'ColorMapEntry', descendant=descendant)
    
class ColorMapEntries(SLDNode):
    """
    A collection of L{ColorMapEntry} nodes. This is a pythonic helper (list of
    nodes) that does not correspond to a true element in the SLD spec.
    """
    def __init__(self, parent):
        """
        Create a new list of ColorMapEntry from the specified parent node.

        @type  parent: L{StyleItem}
        @param parent: The parent class item.
        """
        super(VendorOptions, self).__init__(parent)
        self._node = None
        self._nodes = self._parent.xpath('sld:ColorMapEntry', namespaces=SLDNode._nsmap)

    def __len__(self):
        """
        Get the number of L{ColorMapEntry} nodes in this list.

        @rtype: integer
        @return: The number of L{ColorMapEntry} nodes.
        """
        return len(self._nodes)

    def __getitem__(self, key):
        """
        Get one of the L{ColorMapEntry} nodes in the list.

        @type  key: integer
        @param key: The index of the child node.
        @rtype: L{ColorMapEntry}
        @return: The specific L{ColorMapEntry} node.
        """
        return VendorOption(self, key, descendant=False)

    def __setitem__(self, key, value):
        """
        Set one of the L{ColorMapEntry} nodes in the list with a new value.

        @type    key: integer
        @param   key: The index of the child node.
        @type  value: L{ColorMapEntry}, etree.Element
        @param value: The new value of the specific child node.
        """
        if isinstance(value, ColorMapEntry):
            self._nodes.replace(self._nodes[key], value._node)
        elif isinstance(value, Element):
            self._nodes.replace(self._nodes[key], value)

    def __delitem__(self, key):
        """
        Delete one of the L{ColorMapEntry} nodes from the list.

        @type  key: integer
        @param key: The index of the child node.
        """
        self._nodes.remove(self._nodes[key])


class ColorMap(SLDNode):
    def __init__(self, parent, descendant=True):
        """
        @type  parent: L{RasterSymbolizer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(ColorMap, self).__init__(parent, descendant=descendant) 
        xpath = self._parent.xpath('sld:ColorMap', namespaces=SLDNode._nsmap)
        if len(xpath) < 1:
            self._node = self._parent.makeelement('{%s}ColorMap' % SLDNode._nsmap['sld'], nsmap=SLDNode._nsmap)
            self._parent.append(self._node)
        else:
            self._node = xpath[0]

    @property
    def ColorMapEntries(self):
        """
        Get the list of L{ColorMapEntry} nodes in a friendly L{ColorMapEntries} helper list.

        @rtype: L{ColorMapEntries}
        @return: A pythonic list of L{ColorMapEntry} children.
        """
        return ColorMapEntries(self)
        
    def create_colormapentry(self, color=None, quantity=None, label=None, opacity=None):
        """
        Create a new L{ColorMapEntry} node as a child of this element, and attach it to the DOM.
        Optionally set the name and value of the parameter, if they are both provided.

        @type   color: string
        @param  color: Optional. The color of the L{ColorMapEntry}
        @type  quantity: string
        @param quantity: Optional. The quantity of the L{ColorMapEntry}
        @type  label: string
        @param label: Optional. The label of the L{ColorMapEntry}
        @type  opacity: string
        @param opacity: Optional. The opacity of the L{ColorMapEntry}
        @rtype: L{ColorMapEntry}
        @return: A new style parameter, set to the name and value.
        """
        elem = self._node.makeelement('{%s}ColorMapEntry' % SLDNode._nsmap['sld'], nsmap=SLDNode._nsmap)
        self._node.append(elem)

        elem.attrib['color'] = color
        elem.attrib['quantity'] = quantity
        elem.attrib['label'] = label
        elem.attrib['opacity'] = opacity

        return ColorMapEntry(self, len(self._node) - 1)
        
class RasterSymbolizer(SLDNode):
    """
    A symbolizer for raster. A RasterSymbolizer is a child of a
    L{Rule} element.
    
    @prop: Opacity

        Bewteen 0 (completely transparent) and 1 (completely opaque)

        I{Type}: float

    @prop: ColorMap

        I{Type}: L{ColorMap}
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new PointSymbolizer node, as a child of the specified parent.

        @type  parent: L{Rule}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(RasterSymbolizer, self).__init__(parent, descendant=descendant)
        xpath = self._parent.xpath('sld:RasterSymbolizer', namespaces=SLDNode._nsmap)
        if len(xpath) < 1:
            self._node = self._parent.makeelement('{%s}RasterSymbolizer' % SLDNode._nsmap['sld'], nsmap=SLDNode._nsmap)
            self._parent.append(self._node)
        else:
            self._node = xpath[0]
            
        setattr(self.__class__, 'Opacity', SLDNode.makeproperty('sld', name='Opacity',
                docstring="The opacity of the symbolizer."))
        setattr(self.__class__, 'ColorMap', SLDNode.makeproperty('sld', cls=ColorMap,
                docstring="Color map."))


class PropertyCriterion(SLDNode):
    """
    General property criterion class for all property comparitors.
    A PropertyCriterion is a child of a L{Filter} element.

    Valid property comparitors that are represented by this class are:

        - PropertyIsNotEqual
        - PropertyIsLessThan
        - PropertyIsLessThanOrEqual
        - PropertyIsEqual
        - PropertyIsGreaterThan
        - PropertyIsGreaterThanOrEqual
        - PropertyIsLike

    @prop: PropertyName

        The name of the property to use in the comparison.

        I{Type}: string

    @prop: Literal

        The value of the property.

        I{Type}: string
    """
    def __init__(self, parent, name, descendant=True):
        """
        Create a new PropertyCriterion node, as a child of the specified parent.
        A PropertyCriterion is not represented in the SLD Spec. This class
        is a generalization of many of the PropertyIs... elements present in
        the OGC Filter spec.

        @type  parent: L{Filter}
        @param parent: The parent class object.
        """
        super(PropertyCriterion, self).__init__(parent, descendant=descendant)
        xpath = self._parent.xpath('ogc:' + name, namespaces=SLDNode._nsmap)
        if len(xpath) < 1:
            self._node = self._parent.makeelement('{%s}%s' % (SLDNode._nsmap['ogc'], name), nsmap=SLDNode._nsmap)
            self._parent.append(self._node)
        else:
            self._node = xpath[0]

        setattr(self.__class__, 'PropertyName', SLDNode.makeproperty('ogc', name='PropertyName',
                docstring="The name of the property to compare."))
        setattr(self.__class__, 'Literal', SLDNode.makeproperty('ogc', name='Literal',
                docstring="The literal value of the property to compare against."))


class Filter(SLDNode):
    """
    A filter object that stores the property comparitors. A Filter is a child
    of a L{Rule} element. Filter nodes are pythonic, and have some syntactic
    sugar that allows the creation of simple logical combinations.

    To create an AND logical filter, use the '+' operator:

        >>> rule.Filter = filter1 + filter2

    To create an OR logical filter, use the '|' operator:

        >>> rule.Filter = filter1 | filter2

    Complex combinations can be created by chaining these operations together:

        >>> rule.Filter = filter1 | (filter2 + filter3)

    @prop: PropertyIsEqualTo

        A specification of property (=) equality.

        I{Type}: L{PropertyCriterion}

    @prop: PropertyIsNotEqualTo

        A specification of property (!=) inequality.

        I{Type}: L{PropertyCriterion}

    @prop: PropertyIsLessThan

        A specification of property less-than (<) comparison.

        I{Type}: L{PropertyCriterion}

    @prop: PropertyIsLessThanOrEqualTo

        A specification of property less-than-or-equal-to (<=) comparison.

        I{Type}: L{PropertyCriterion}

    @prop: PropertyIsGreaterThan

        A specification of property greater-than (>) comparison,

        I{Type}: L{PropertyCriterion}

    @prop: PropertyIsGreaterThanOrEqualTo

        A specification of property greater-than-or-equal-to (>=) comparison.

        I{Type}: L{PropertyCriterion}
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new Filter node.

        @type  parent: L{Rule}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Filter, self).__init__(parent, descendant=descendant)
        xpath = self._parent.xpath('ogc:Filter', namespaces=SLDNode._nsmap)
        if len(xpath) == 1:
            self._node = xpath[0]
        else:
            self._node = self._parent.makeelement('{%s}Filter' % SLDNode._nsmap['ogc'], nsmap=SLDNode._nsmap)

    def __add__(self, other):
        """
        Add two filters together to create one AND logical filter.

        @type  other: L{Filter}
        @param other: A filter to AND with this one.
        @rtype: L{Filter}
        @return: A new filter with an ogc:And element as its child.
        """
        if not self._node.getparent() is None:
            self._node.getparent().remove(self._node)
        elem = self._node.makeelement('{%s}And' % SLDNode._nsmap['ogc'])
        elem.append(copy.copy(self._node[0]))
        elem.append(copy.copy(other._node[0]))

        f = Filter(self)
        f._node.append(elem)

        return f

    def __or__(self, other):
        """
        Or two filters together to create on OR logical filter.

        @type  other: L{Filter}
        @param other: A filter to OR with this one.
        @rtype: L{Filter}
        @return: A new filter with an ogc:Or element as its child.
        """
        elem = self._node.makeelement('{%s}Or' % SLDNode._nsmap['ogc'])
        elem.append(copy.copy(self._node[0]))
        elem.append(copy.copy(other._node[0]))

        f = Filter(self)
        f._node.append(elem)

        return f

    def __getattr__(self, name):
        """
        Get a named attribute from this Filter instance. This method allows
        properties with the prefix of 'PropertyIs' to be set, and raises
        an AttributeError for all other property names.

        @type  name: string
        @param name: The name of the property.
        @rtype: L{PropertyCriterion}
        @return: The property comparitor.
        """
        if not name.startswith('PropertyIs'):
            raise AttributeError('Property name must be one of: PropertyIsEqualTo, PropertyIsNotEqualTo, PropertyIsLessThan, PropertyIsLessThanOrEqualTo, PropertyIsGreaterThan, PropertyIsGreaterThanOrEqualTo, PropertyIsLike.')
        xpath = self._node.xpath('ogc:' + name, namespaces=SLDNode._nsmap)
        if len(xpath) == 0:
            return None

        return PropertyCriterion(self, name)

    def __setattr__(self, name, value):
        """
        Set a named attribute on this Filter instance. If the property name
        begins with 'PropertyIs', the node value will be appended to the filter.

        @type   name: string
        @param  name: The name of the property.
        @type  value: L{PropertyCriterion}
        @param value: The new property comparitor.
        """
        if not name.startswith('PropertyIs'):
            object.__setattr__(self, name, value)
            return

        xpath = self._node.xpath('ogc:' + name, namespaces=SLDNode._nsmap)
        if len(xpath) > 0:
            xpath[0] = value
        else:
            elem = self._node.makeelement('{%s}%s' % (SLDNode._nsmap['ogc'], name), nsmap=SLDNode._nsmap)
            self._node.append(elem)

    def __delattr__(self, name):
        """
        Delete the property from the Filter. This removes the child node
        of this name from the Filter.

        @type  name: string
        @param name: The name of the property.
        """
        xpath = self._node.xpath('ogc:' + name, namespaces=SLDNode._nsmap)
        if len(xpath) > 0:
            self._node.remove(xpath[0])


class Rule(SLDNode):
    """
    A rule object contains a title, an optional L{Filter}, and one or more
    L{Symbolizer}s. A Rule is a child of a L{FeatureTypeStyle}.

    @prop: Title

        The title of this rule. This is required for a valid SLD.

        I{Type}: string

    @prop: Filter

        Optional. A filter defines logical comparisons against properties.

        I{Type}: L{Filter}

    @prop: PolygonSymbolizer

        A symbolizer that defines how polygons should be rendered.

        I{Type}: L{PolygonSymbolizer}

    @prop: LineSymbolizer

        A symbolizer that defines how lines should be rendered.

        I{Type}: L{LineSymbolizer}

    @prop: TextSymbolizer

        A symbolizer that defines how text should be rendered.

        I{Type}: L{TextSymbolizer}

    @prop: PointSymbolizer

        A symbolizer that defines how points should be rendered.

        I{Type}: L{PointSymbolizer}
    """
    def __init__(self, parent, index, descendant=True):
        """
        Create a new Rule node.

        @type  parent: L{FeatureTypeStyle}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Rule, self).__init__(parent, descendant=descendant)
        self._node = self._parent.xpath('sld:Rule', namespaces=SLDNode._nsmap)[index]

        setattr(self.__class__, 'Title', SLDNode.makeproperty('sld', name='Title',
                docstring="The title of the Rule."))
        setattr(self.__class__, 'Filter', SLDNode.makeproperty('ogc', cls=Filter,
                docstring="The optional filter object, with property comparitors."))
        '''
        setattr(self.__class__, 'PolygonSymbolizer', SLDNode.makeproperty('sld', cls=PolygonSymbolizer,
                docstring="The optional polygon symbolizer for this rule."))
        setattr(self.__class__, 'LineSymbolizer', SLDNode.makeproperty('sld', cls=LineSymbolizer,
                docstring="The optional line symbolizer for this rule."))
        setattr(self.__class__, 'TextSymbolizer', SLDNode.makeproperty('sld', cls=TextSymbolizer,
                docstring="The optional text symbolizer for this rule."))
        setattr(self.__class__, 'PointSymbolizer', SLDNode.makeproperty('sld', cls=PointSymbolizer,
                docstring="The optional point symbolizer for this rule."))
        '''
        setattr(self.__class__, 'MinScaleDenominator', SLDNode.makeproperty('sld', name='MinScaleDenominator',
                docstring="The minimum scale denominator for this rule."))
        setattr(self.__class__, 'MaxScaleDenominator', SLDNode.makeproperty('sld', name='MaxScaleDenominator',
                docstring="The maximum scale denominator for this rule."))

    def normalize(self):
        """
        Normalize this node prior to validation. This is required, as the
        ogc:Filter node must come before any symbolizer nodes. The SLD
        is modified in place.
        """
        order = [
            'sld:Title', 'ogc:Filter', 'sld:MinScaleDenominator',
            'sld:MaxScaleDenominator', 'sld:PolygonSymbolizer',
            'sld:LineSymbolizer', 'sld:TextSymbolizer', 'sld:PointSymbolizer']
        for item in order:
            xpath = self._node.xpath(item, namespaces=SLDNode._nsmap)
            for xitem in xpath:
                # move this to the end
                self._node.remove(xitem)
                self._node.append(xitem)

        # no need to normalize children

    def create_filter(self, propname=None, comparitor=None, value=None):
        """
        Create a L{Filter} for this rule. The property name, comparitor, and value
        are required to create a valid Filter.

        @type    propname: string
        @param   propname: The name of the property to filter.
        @type  comparitor: string
        @param comparitor: The comparison to perform on the property. One of
            "!=", "<", "<=", "=", ">=", ">", and "%" is required.
        @type       value: string
        @param      value: The value of the property to compare against.
        @rtype: L{Filter}
        @return: A new filter attached to this Rule.
        """
        if propname is None or comparitor is None or value is None:
            return None

        rfilter = self.create_element('ogc', 'Filter')
        ftype = None
        if comparitor == '==':
            ftype = 'PropertyIsEqualTo'
        elif comparitor == '<=':
            ftype = 'PropertyIsLessThanOrEqualTo'
        elif comparitor == '<':
            ftype = 'PropertyIsLessThan'
        elif comparitor == '>=':
            ftype = 'PropertyIsGreaterThanOrEqualTo'
        elif comparitor == '>':
            ftype = 'PropertyIsGreaterThan'
        elif comparitor == '!=':
            ftype = 'PropertyIsNotEqualTo'
        elif comparitor == '%':
            ftype = 'PropertyIsLike'

        if not ftype is None:
            prop = PropertyCriterion(rfilter, ftype)
            prop.PropertyName = propname
            if not value is None:
                prop.Literal = value
            setattr(rfilter, ftype, prop)

        return rfilter

    def create_symbolizer(self, stype):
        """
        Create a L{Symbolizer} of the specified type on this rule.

        @type  stype: string
        @param stype: The type of symbolizer. Allowed types are "Point",
            "Line", "Polygon", or "Text".
        @rtype: L{Symbolizer}
        @return: A newly created symbolizer, attached to this Rule.
        """
        if stype is None:
            return None

        return self.create_element('sld', stype + 'Symbolizer')
        
    def create_pointsymbolizer(self):
        """
        Create a new L{PointSymbolizer} node as a child of this element, and attach it to the DOM.

        @rtype: L{PointSymbolizer}
        @return: A new style parameter, set to the name and value.
        """
        symbolizer = PointSymbolizer(self)


class Rules(SLDNode):
    """
    A collection of L{Rule} nodes. This is a pythonic helper (list of
    nodes) that does not correspond to a true element in the SLD spec.
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new list of Rules from the specified parent node.

        @type  parent: L{FeatureTypeStyle}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Rules, self).__init__(parent, descendant=descendant)
        self._node = None
        self._nodes = self._parent.xpath('sld:Rule', namespaces=SLDNode._nsmap)

    def normalize(self):
        """
        Normalize this node and all rules contained within. The SLD model is
        modified in place.
        """
        for i, rnode in enumerate(self._nodes):
            rule = Rule(self, i - 1, descendant=False)
            rule.normalize()

    def __len__(self):
        """
        Get the number of L{CssParameter} nodes in this list.

        @rtype: integer
        @return: The number of L{CssParameter} nodes.
        """
        return len(self._nodes)

    def __getitem__(self, key):
        """
        Get one of the L{Rule} nodes in the list.

        @type  key: integer
        @param key: The index of the child node.
        @rtype: L{Rule}
        @return: The specific L{Rule} node.
        """
        rule = Rule(self, key, descendant=False)
        return rule

    def __setitem__(self, key, value):
        """
        Set one of the L{Rule} nodes in the list with a new value.

        @type    key: integer
        @param   key: The index of the child node.
        @type  value: L{Rule}, etree.Element
        @param value: The new value of the specific child node.
        """
        if isinstance(value, Rule):
            self._nodes.replace(self._nodes[key], value._node)
        elif isinstance(value, Element):
            self._nodes.replace(self._nodes[key], value)

    def __delitem__(self, key):
        """
        Delete one of the L{Rule} nodes from the list.

        @type  key: integer
        @param key: The index of the child node.
        """
        self._nodes.remove(self._nodes[key])


class Transformation(SLDNode):
    """
    @prop: PropertyName

        I{Type}: string
        
    This class is a property of any L{Symbolizer}.
    """
    def __init__(self, parent, descendant=False):
        """
        Create a new Font node from the specified parent.

        @type  parent: L{FeatureTypeStyle}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(Transformation, self).__init__(parent, 'Transformation', descendant=descendant)
        
        setattr(self.__class__, 'Function', SLDNode.makeproperty('ogc', name='Function',
                docstring="The Function of the property."))


class FeatureTypeStyle(SLDNode):
    """
    A FeatureTypeStyle node contains all L{Rule} objects applicable to a
    specific layer. A FeatureTypeStyle is a child of a L{UserStyle} element.
    @prop: Transformation

        The name of the Transformation.

        I{Type}: string

    @prop: Rules

        The custom styling for this named layer.

        I{Type}: L{UserStyle}
    
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new FeatureTypeNode node, as a child of the specified parent.

        @type  parent: L{UserStyle}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(FeatureTypeStyle, self).__init__(parent, descendant=descendant)
        self._node = self._parent.xpath('sld:FeatureTypeStyle', namespaces=SLDNode._nsmap)[0]
        
        setattr(self.__class__, 'Transformation', SLDNode.makeproperty('sld', cls=Transformation,
                docstring="The transformation of the FeatureTypeStyle."))

    

    def normalize(self):
        """
        Normalize this element and all child L{Rule}s. The SLD model is
        modified in place.
        """
        if not self.Transformation is None:
            self.Transformation.normalize()
        if not self.Rules is None:
            self.Rules.normalize()
          
            
    def create_transformation(self):
        """
        Create a L{Transformation} for this named layer.

        @rtype: L{Transformation}
        @return: A newly created user style, attached to this node.
        """
        return self.get_or_create_element('sld', 'Transformation')

    @property
    def Rules(self):
        """
        Get the L{sld.Rules} pythonic list helper for all L{Rule} objects in this
        style.

        @rtype: L{sld.Rules}
        @return: A list of all rules applied to this style.
        """
        return Rules(self)

    def create_rule(self, title, MinScaleDenominator=None, MaxScaleDenominator=None):
        """
        Create a L{Rule} object on this style. A rule requires a title and
        symbolizer. If no symbolizer is specified, a PointSymbolizer will be
        assigned to the rule.

        @type       title: string
        @param      title: The name of the new L{Rule}.
        @type  symbolizer: L{Symbolizer} I{class}
        @param symbolizer: The symbolizer type. This is the class object (as
            opposed to a class instance) of the symbolizer to use.
        @rtype: L{Rule}
        @return: A newly created rule, attached to this FeatureTypeStyle.
        """
        elem = self._node.makeelement('{%s}Rule' % SLDNode._nsmap['sld'], nsmap=SLDNode._nsmap)
        self._node.append(elem)

        rule = Rule(self, len(self._node) - 1)
        rule.Title = title

        if MinScaleDenominator is not None:
            rule.MinScaleDenominator = str(MinScaleDenominator)
        if MaxScaleDenominator is not None:
            rule.MaxScaleDenominator = str(MaxScaleDenominator)
        
        return rule


class UserStyle(SLDNode):
    """
    A UserStyle object. A UserStyle is a child of a L{StyledLayerDescriptor}.

    @prop: Name

        The name of the UserStyle.

        I{Type}: string
        
    @prop: Title

        The title of the UserStyle.

        I{Type}: string

    @prop: Abstract

        The abstract describing this UserStyle.

        I{Type}: string

    @prop: FeatureTypeStyle

        The styling for the feature type.

        I{Type}: L{FeatureTypeStyle}
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new UserStyle node.

        @type  parent: L{NamedLayer}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(UserStyle, self).__init__(parent, descendant=descendant)
        self._node = self._parent.xpath('sld:UserStyle', namespaces=SLDNode._nsmap)[0]

        setattr(self.__class__, 'Name', SLDNode.makeproperty('sld', name='Name',
                docstring="The name of the UserStyle."))
        setattr(self.__class__, 'Title', SLDNode.makeproperty('sld', name='Title',
                docstring="The title of the UserStyle."))
        setattr(self.__class__, 'Abstract', SLDNode.makeproperty('sld', name='Abstract',
                docstring="The abstract of the UserStyle."))
        setattr(self.__class__, 'FeatureTypeStyle', SLDNode.makeproperty('sld', cls=FeatureTypeStyle,
                docstring="The feature type style of the UserStyle."))

    def normalize(self):
        """
        Normalize this node and all child nodes prior to validation. The SLD
        is modified in place.
        """
        if not self.FeatureTypeStyle is None:
            self.FeatureTypeStyle.normalize()

    def create_featuretypestyle(self):
        """
        Create a L{FeatureTypeStyle} object, and attach it to this UserStyle.

        @rtype: L{FeatureTypeStyle}
        @return: A newly created feature type style, attached to this node.
        """
        return self.get_or_create_element('sld', 'FeatureTypeStyle')


class NamedLayer(SLDNode):
    """
    A named layer contains a name and a user style. A NamedLayer is a child of
    a L{StyledLayerDescriptor}.

   
    @prop: Name

        The name of the UserStyle.

        I{Type}: string
        
    @prop: UserStyle

        The custom styling for this named layer.

        I{Type}: L{UserStyle}
    """
    def __init__(self, parent, descendant=True):
        """
        Create a new NamedLayer node.

        @type  parent: L{StyledLayerDescriptor}
        @param parent: The parent class object.
        @type  descendant: boolean
        @param descendant: A flag indicating if this is a descendant node of the parent.
        """
        super(NamedLayer, self).__init__(parent, descendant=descendant)
        self._node = self._parent.xpath('sld:NamedLayer', namespaces=SLDNode._nsmap)[0]

        setattr(self.__class__, 'UserStyle', SLDNode.makeproperty('sld', cls=UserStyle,
                docstring="The UserStyle of the NamedLayer."))
        setattr(self.__class__, 'Name', SLDNode.makeproperty('sld', name='Name',
                docstring="The name of the layer."))

    def normalize(self):
        """
        Normalize this node and all child nodes prior to validation. The SLD
        is modified in place.
        """
        if not self.UserStyle is None:
            self.UserStyle.normalize()

    def create_userstyle(self, name, title):
        """
        Create a L{UserStyle} for this named layer.

        @type  name: string
        @param name: The name of the user style.
        @type  title: string
        @param title: The title of the user style.
        @rtype: L{UserStyle}
        @return: A newly created user style, attached to this node.
        """
        userstyle =  self.get_or_create_element('sld', 'UserStyle')
        userstyle.Name = name
        if not title or title == '':
            title = name
        userstyle.Title = title
        return userstyle
    
class StyledLayerDescriptor(SLDNode):
    """
    An object representation of an SLD document.

    @prop: NamedLayer

        The named layer that this styling applies to.

        I{Type}: L{NamedLayer}
    """

    _cached_schema = None
    """A cached schema document, to prevent repeated web requests for the schema document."""

    def __init__(self, sld_file=None):
        """
        Create a new SLD document. If an sld file is provided, this constructor
        will fetch the SLD schema from the internet and validate the file
        against that schema.

        @type  sld_file: string
        @param sld_file: The name of a pre-existing SLD file.
        """
        super(StyledLayerDescriptor, self).__init__(None)

        if StyledLayerDescriptor._cached_schema is None:
            logging.debug('Storing new schema into cache.')

            localschema = NamedTemporaryFile(delete=False)
            '''
            localschema_backup_path = './StyledLayerDescriptor-backup.xsd'
            try:
                #logging.debug('Cache hit for backup schema document.')
                #localschema_backup = open(localschema_backup_path, 'rb')
                logging.debug('Cache miss for backup schema document.')
                localschema_backup = open(localschema_backup_path, 'wb')

                schema_url = 'http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd'
                resp = urlopen(schema_url)
                localschema_backup.write(resp.read())
                resp.close()
                localschema_backup.close()
                localschema_backup = open(localschema_backup_path, 'rb')
                
            except IOError:
                logging.debug('Cache miss for backup schema document.')
                localschema_backup = open(localschema_backup_path, 'wb')

                schema_url = 'http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd'
                resp = urlopen(schema_url)
                localschema_backup.write(resp.read())
                resp.close()
                localschema_backup.close()
                localschema_backup = open(localschema_backup_path, 'rb')
            '''
            curr_path = os.path.abspath(os.path.dirname(__file__))
            xsd_path = os.path.join(curr_path, 'StyledLayerDescriptor.xsd')
            localschema_backup = open(xsd_path, 'rb')
            
            localschema.write(localschema_backup.read())
            localschema.close()
            localschema_backup.close()

            localschema = open(localschema.name, 'rt')
            self._schemadoc = parse(localschema)
            localschema.close()

            StyledLayerDescriptor._cached_schema = localschema.name
        else:
            logging.debug('Fetching schema from cache.')

            localschema = open(StyledLayerDescriptor._cached_schema, 'rt')
            self._schemadoc = parse(localschema)
            localschema.close()

        if not sld_file is None:
            self._node = parse(sld_file)
            self._schema = XMLSchema(self._schemadoc)
            if not self._schema.validate(self._node):
                logging.warn('SLD File "%s" does not validate against the SLD schema.', sld_file)
        else:
            self._node = Element("{%s}StyledLayerDescriptor" % SLDNode._nsmap['sld'], version="1.0.0", nsmap=SLDNode._nsmap)
            self._schema = None

        setattr(self.__class__, 'NamedLayer', SLDNode.makeproperty('sld', cls=NamedLayer,
                docstring="The named layer of the SLD."))

    def __del__(self):
        """
        Destroy the StyledLayerDescriptor object, and clear its cache.
        """
        if not StyledLayerDescriptor._cached_schema is None:
            logging.debug('Clearing cached schema.')

            os.remove(StyledLayerDescriptor._cached_schema)
            StyledLayerDescriptor._cached_schema = None

    def __deepcopy__(self, memo):
        """
        Perform a deep copy. Instead of copying references to the schema
        object, create a new SLD, and deepcopy the SLD node.
        """
        sld = StyledLayerDescriptor()
        sld._node = copy.deepcopy(self._node)
        return sld

    def normalize(self):
        """
        Normalize this node and all child nodes prior to validation. The SLD
        is modified in place.
        """
        if not self.NamedLayer is None:
            self.NamedLayer.normalize()

    def validate(self):
        """
        Validate the current file against the SLD schema. This first normalizes
        the SLD document, then validates it. Any schema validation error messages
        are logged at the INFO level.

        @rtype: boolean
        @return: A flag indicating if the SLD is valid.
        """
        self.normalize()

        if self._node is None:
            logging.debug('The node is empty, and cannot be validated.')
            return False

        if self._schema is None:
            self._schema = XMLSchema(self._schemadoc)

        is_valid = self._schema.validate(self._node)

        for msg in self._schema.error_log:
            logging.info('Line:%d, Column:%d -- %s', msg.line, msg.column, msg.message)

        return is_valid

    @property
    def version(self):
        """
        Get the SLD version.
        """
        return self._node.getroot().get('version')

    @property
    def xmlns(self):
        """
        Get the XML Namespace.
        """
        return self._node.getroot().nsmap[None]

    def create_namedlayer(self, name):
        """
        Create a L{NamedLayer} in this SLD.

        @type  name: string
        @param name: The name of the layer.
        @rtype: L{NamedLayer}
        @return: The named layer, attached to this SLD.
        """
        namedlayer = self.get_or_create_element('sld', 'NamedLayer')
        namedlayer.Name = name
        return namedlayer

    def as_sld(self, pretty_print=False):
        """
        Serialize this SLD model into a string.

        @rtype: string
        @returns: The content of the SLD.
        """
        return tostring(self._node, pretty_print=pretty_print)