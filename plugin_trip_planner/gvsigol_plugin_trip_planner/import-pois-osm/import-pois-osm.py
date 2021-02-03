import ogr
import osr
import shapely
from shapely.geometry import Point
import geopandas as gpd
import requests
import sys
import os
import imp

# Amenity:
#         Hospital
#         Taxi
#         Parking
#         Cine
#         Police
#         Post Office
#         Theatre
#         University
#         School/college

# Various:
#         Marketplace (son los mercados municipales)

# Tourism:
#         Attraction
#         Historic
#         Information
#         Monument 
#         Museum
#         Artcentre
#         Shops  
#         Shopping centre
#         Department store


# Usage: python import-pois-osm
def extract_points(pbfFile, reverseGeocodeUrl):
    driver=ogr.GetDriverByName('OSM') # able to read .osm or .pbf files
    data = driver.Open(pbfFile)
    layer = data.GetLayer('points')

    amenityTags = ('hospital', 'taxi', 'parking', 'cine', 'police', 'post office', 'theatre', 'university', 'school/college')
    variousTags = ('marketplace',)
    tourismTags = ('attraction', 'historic', 'information', 'monument', 'museum', 'artcentre', 'shops', 'shopping centre', 'department store')
    historicTags = ('monument', 'museum')

    layerDefinition = layer.GetLayerDefn()


    for i in range(layerDefinition.GetFieldCount()):
        print(layerDefinition.GetFieldDefn(i).GetName())

    features=[x for x in layer]

    data_list=[]
    i = 0
    numFeatures = len(features)
    for f in features:
        if i % 100 == 0:
                print('Processing {0} of {1}'.format(i, numFeatures))
        i = i+1
        # if i > 1000:
        #         break
        data=f.ExportToJson(as_object=True)
        # aux = f.GetField('name')
        coords=data['geometry']['coordinates']
        shapely_geo=Point(coords[0],coords[1])
        name=data['properties']['name']
        if name==None: 
                continue
        # print aux
        # print name
        other_tags=data['properties']['other_tags']
        category = 'amenity'
        subcat = None
        if other_tags and 'amenity' in other_tags:
                feat=[x for x in other_tags.split(',') if 'amenity' in x][0]
                aux=feat[feat.rfind('>')+2:feat.rfind('"')]
                if aux in amenityTags:
                        subcat = aux                
        else:
                if other_tags and 'various' in other_tags:
                        feat=[x for x in other_tags.split(',') if 'various' in x][0]
                        category = 'various'
                        aux = feat[feat.rfind('>')+2:feat.rfind('"')]
                        if aux in variousTags:
                                subcat = aux
                else:
                        if other_tags and 'tourism' in other_tags:
                                feat=[x for x in other_tags.split(',') if 'tourism' in x][0]
                                category = 'tourism'
                                aux = feat[feat.rfind('>')+2:feat.rfind('"')]
                                if aux in tourismTags:
                                        subcat = aux
                        else:
                                if other_tags and 'historic' in other_tags:
                                        feat=[x for x in other_tags.split(',') if 'historic' in x][0]
                                        category = 'historic'
                                        aux = feat[feat.rfind('>')+2:feat.rfind('"')]
                                        print('Historic: ' + name + ' Subcat: ' + aux)
                                        if aux in historicTags:
                                                subcat = aux

        if subcat:
                payload = {'lon': coords[0], 'lat': coords[1]}
                address = ' '
                muni = ' '
                try:
                        r = requests.get(reverseGeocodeUrl, payload)
                        res = r.json()
                        portalNumber = res.get('portalNumber')
                        muni = res.get('muni')

                        if 0 != portalNumber:
                                address = '{0} {1} {2}'.format(res.get('tip_via'), res.get('address'), portalNumber, muni)
                        else:
                                address = '{0} {1}'.format(res.get('tip_via'), res.get('address'), muni)

                except requests.exceptions.RequestException as e:
                        print(e)
                except ValueError as jsonErr:
                        print(jsonErr)
                nameUni = name.decode('utf-8')

                try:
                        nameAndAddress = nameUni + ' - ' + address + ', ' + muni
                        data_list.append([nameUni,nameAndAddress,category,subcat,shapely_geo, address, muni])
                except TypeError as e2:
                        print(e2)
                        print(nameUni)
                        print(address)
                        print(muni)


    print((len(data_list)))
    # create the data source
    fileDest = pbfFile.replace('.pbf', '.shp')
    create_shapefile(data_list, fileDest)

def create_shapefile(data_list, fileDest):
        os.environ['SHAPE_ENCODING'] = "utf-8"
        driver=ogr.GetDriverByName('ESRI Shapefile')
        data_source = driver.CreateDataSource(fileDest)
        # create the spatial reference, WGS84
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)

        # create the layer
        layer = data_source.CreateLayer("pois", srs, ogr.wkbPoint)

        # Add the fields we're interested in
        field_name = ogr.FieldDefn("Name", ogr.OFTString)
        field_name.SetWidth(24)
        layer.CreateField(field_name)
        field_2 = ogr.FieldDefn("NameAndA", ogr.OFTString)
        field_2.SetWidth(240)
        layer.CreateField(field_2)
        field_3 = ogr.FieldDefn("Category", ogr.OFTString)
        field_3.SetWidth(50)
        layer.CreateField(field_3)
        field_4 = ogr.FieldDefn("Subcat", ogr.OFTString)
        field_4.SetWidth(50)
        layer.CreateField(field_4)
        field_5 = ogr.FieldDefn("Address", ogr.OFTString)
        field_5.SetWidth(140)
        layer.CreateField(field_5)
        field_6 = ogr.FieldDefn("Municipio", ogr.OFTString)
        field_6.SetWidth(80)
        layer.CreateField(field_6)


        # Process the text file and add the attributes and features to the shapefile
        for row in data_list:
                # create the feature
                feature = ogr.Feature(layer.GetLayerDefn())
                # Set the attributes using the values from the delimited text file
                
                strUTF8 = row[0].encode('utf-8')
                # print(strUTF8)
                feature.SetField("Name", strUTF8)
                # feature.SetField("Name", row[0])
                strUnicode = row[1]
                strUTF8 = strUnicode.encode('utf-8')
                feature.SetField("NameAndA", strUTF8)

                feature.SetField("Category", row[2])
                feature.SetField("Subcat", row[3])

                strUni = row[5]
                strUTF8 = strUni.encode('utf-8')

                feature.SetField("Address", strUTF8)

                strUni = row[6] # .decode('utf-8')
                strUTF8 = strUni.encode('utf-8')
                feature.SetField("Municipio", strUTF8)


                # create the WKT for the feature using Python string formatting
                wkt = "POINT(%f %f)" %  (float(row[4].x) , float(row[4].y))

                # Create the point from the Well Known Txt
                point = ogr.CreateGeometryFromWkt(wkt)

                # Set the feature geometry using the point
                feature.SetGeometry(point)
                # Create the feature in the layer (shapefile)
                layer.CreateFeature(feature)
                # Destroy the feature to free resources
                feature.Destroy()

        # Destroy the data source to free resources
        data_source.Destroy()
        


imp.reload(sys)
sys.setdefaultencoding('latin1')

reverseGeocodeUrl = 'https://trip-planner.gvsigonline.com/geocodersolr/api/geocoder/reverseGeocode' # ?lon=-0.3576982972310994&lat=39.4767836851722

extract_points('D:/otp/area_metropolitana_grande.pbf', reverseGeocodeUrl)