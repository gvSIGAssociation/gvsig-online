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
@author: Cesar Martinez Izquierdo
'''
from lxml import etree

def getTextFromXMLNode(tree, xpath_filter, ns={}):
    if tree is not None:
        for item in tree.findall(xpath_filter, ns):
            if item.text:
                return item.text
    return ''

def getXMLNode(tree, xpath_filter, ns):
    if tree:
        aux = tree.findall(xpath_filter, ns={})
        if len(aux) > 0:
            return aux[0]
    
    return None

def getXMLCodeText(node, attribName='codeListValue', ns={}):
    if node is not None:
        if node.text:
            return node.text
        return node.get(attribName, '')
    return ''

def getLocalizedText(node, lang=None, childNodeName='value'):
    if node is not None:
        if lang:
            xpath_filter = './' + childNodeName + '/[@lang="' + lang + '"]'
        else:
            xpath_filter = './' + childNodeName + '/' 
        aux = node.findall(xpath_filter)
        if len(aux) > 0:
            return aux[0]
    return ''

def sanitizeXmlText(text):
    """
    Escapes the provided text to ensure that no XML elements are injected
    in a XML fragment.
    """
    placeHolder = etree.Element('ph')
    placeHolder.text = text
    serialized = etree.tostring(placeHolder, encoding='unicode')
    serialized = serialized.replace('"', '&#x22;');
    serialized = serialized.replace("'", "&#x27;");
    serialized = serialized.replace("`", "&#x60;")
    return serialized[4:-5]


def getLastExistingSibling(parent, previousSiblingNames, namespaces={}):
    """
    Since most 19115 elements are sequences, the children must follow a specific order. This method
    finds the last existing sibling or returns None.
    """
    for sibling in reversed(previousSiblingNames):
        children = parent.findall(sibling, namespaces)
        if len(children) > 0:
            return children[-1] # return last child

def insertAfter(parent, child, previousSiblingNames, namespaces={}):
    """
    Since most 19115 elements are sequences, the children must follow a specific order. This method
    inserts a child in the right order, i.e, after the last existing sibling
    """
    prevSibling = getLastExistingSibling(parent, previousSiblingNames, namespaces)
    if prevSibling is not None:
        prevSibling.addnext(child)
    else:
        parent.insert(0, child)