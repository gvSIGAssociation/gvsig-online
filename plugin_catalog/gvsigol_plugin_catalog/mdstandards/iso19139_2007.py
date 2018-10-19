# -*- coding: utf-8 -*-
from lxml import etree as ET
from builtins import str as text

def update_extent(geo_bb_elem, extent_tuple):
    minx, miny, maxx, maxy = extent_tuple
    for bound in geo_bb_elem:
        if bound.tag == '{http://www.isotc211.org/2005/gmd}westBoundLongitude':
            bound[0].text = "{:f}".format(minx)
        elif bound.tag == '{http://www.isotc211.org/2005/gmd}eastBoundLongitude':
            bound[0].text = "{:f}".format(maxx)
        elif bound.tag == '{http://www.isotc211.org/2005/gmd}southBoundLatitude':
            bound[0].text = "{:f}".format(miny)
        elif bound.tag == '{http://www.isotc211.org/2005/gmd}northBoundLatitude':
            bound[0].text = "{:f}".format(maxy)

def update_thumbnail(browse_graphic_elem, thumbnail_url):
    ns = {'gmd': 'http://www.isotc211.org/2005/gmd', 'gco': 'http://www.isotc211.org/2005/gco'}
    desc = browse_graphic_elem.findall('./gmd:fileDescription/gco:CharacterString', ns)
    print desc
    print browse_graphic_elem[0]
    if len(desc) > 0 and desc[0].text == u'gvsigol thumbnail':
        file_names = browse_graphic_elem.findall('./gmd:fileName/gco:CharacterString', ns)
        if len(file_names) > 0:
            file_names[0].text = thumbnail_url

def update_metadata(xml_str, extent_tuple, thumbnail_url):
    tree = ET.fromstring(xml_str)
    ns = {'gmd': 'http://www.isotc211.org/2005/gmd'}
    for geog_bounding_box_element in tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox', ns):
        update_extent(geog_bounding_box_element, extent_tuple)
    for thumbnail_element in tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:graphicOverview/gmd:MD_BrowseGraphic', ns):
        update_thumbnail(thumbnail_element, thumbnail_url)
    return ET.tostring(tree, encoding='UTF-8')

