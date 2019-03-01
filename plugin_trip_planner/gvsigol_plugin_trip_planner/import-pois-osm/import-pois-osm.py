import ogr
import osr
import shapely
from shapely.geometry import Point
import geopandas as gpd
import sys
import os

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
def extract_points(pbfFile):
    driver=ogr.GetDriverByName('OSM') # able to read .osm or .pbf files
    data = driver.Open(pbfFile)
    layer = data.GetLayer('points')

    amenityTags = ('hospital', 'taxi', 'parking', 'cine', 'police', 'post office', 'theatre', 'university', 'school/college')
    variousTags = ('marketplace',)
    tourismTags = ('attraction', 'historic', 'information', 'monument', 'museum', 'artcentre', 'shops', 'shopping centre', 'department store')

    layerDefinition = layer.GetLayerDefn()


    for i in range(layerDefinition.GetFieldCount()):
        print layerDefinition.GetFieldDefn(i).GetName()

    features=[x for x in layer]

    data_list=[]
    i = 0
    numFeatures = len(features)
    for f in features:
        if i % 10 == 0:
                print 'Processing {0} of {1}'.format(i, numFeatures)
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
        highway=data['properties']['highway']
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

        if subcat:
                data_list.append([name,highway,category,subcat,shapely_geo])

    print(len(data_list))
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
        field_2 = ogr.FieldDefn("Highway", ogr.OFTString)
        field_2.SetWidth(24)
        layer.CreateField(field_2)
        field_3 = ogr.FieldDefn("Category", ogr.OFTString)
        field_3.SetWidth(50)
        layer.CreateField(field_3)
        field_4 = ogr.FieldDefn("Subcat", ogr.OFTString)
        field_4.SetWidth(50)
        layer.CreateField(field_4)

        # Process the text file and add the attributes and features to the shapefile
        for row in data_list:
                # create the feature
                feature = ogr.Feature(layer.GetLayerDefn())
                # Set the attributes using the values from the delimited text file
                
                strDecoded = row[0].decode('utf-8')
                strUTF8 = strDecoded.encode('utf-8')
                # print(strUTF8)
                feature.SetField("Name", strUTF8)
                # feature.SetField("Name", row[0])
                feature.SetField("Highway", row[1])
                feature.SetField("Category", row[2])
                feature.SetField("Subcat", row[3])

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
        


reload(sys)
sys.setdefaultencoding('latin1')

extract_points('D:/otp/graphs/vlc/osm_area_metropolitana_01.pbf')