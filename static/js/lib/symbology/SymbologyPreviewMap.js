/**
 * gvSIG Online.
 * Copyright (C) 2007-2015 gvSIG Association.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/**
 * @author: José Badía <jbadia@scolab.es>
 */

var map = null;

var SymbologyPreviewMap = function(type, stl) {	
	this.style = stl;
	this.type = type;
};

SymbologyPreviewMap.prototype.createMap = function() {
	var mapDiv = $("<div>", {id: "map-"+this.type, class: "symbology-preview-map"});
	
	return mapDiv;
};


SymbologyPreviewMap.prototype.loadMap = function(workspace, layer, username, password) {
	this.workspace = workspace;
	this.layer = layer;
	this.username = username;
	this.password = password;
	
	this.map = new ol.Map({
		layers: [
		    new ol.layer.Tile({
            	source: new ol.source.MapQuest({layer: 'osm'})
          	})
		],
		target: "map-"+this.type,
		view: new ol.View({
		    center:[0,0],
		    zoom: '1'
		})
	});
	this.addLayer();
};

SymbologyPreviewMap.prototype.addLayer = function(sldCode) {
	var workspace_fields = this.workspace[0]["workspace"][0].fields;
	var layer_fields = this.layer[0]["layer"][0].fields;
	var namespace = workspace_fields.uri;
	
	var uri = namespace.split('/');
	var ws = uri[uri.length - 1];
		
	var prms = {'LAYERS': ws + ':' + layer_fields.name, 
			'FORMAT': 'image/png', 
			'VERSION': '1.1.1'}
	if(sldCode){
		prms = {'LAYERS': ws + ':' + layer_fields.name, 
			'FORMAT': 'image/png', 
			'VERSION': '1.1.1',
			STYLES: undefined, 
			SLD_BODY: sldCode}
	}
	if(this.type == "CH"){
		var wmsSource = new ol.source.ImageWMS({
			url: this.createAuthUrl(workspace_fields.wms_endpoint),
			visible: true,
			params: prms,
			serverType: 'geoserver'
		});
		var wmsLayer = new ol.layer.Image({
			source: wmsSource,
			visible: true
		});
	}else{
		var wmsSource = new ol.source.TileWMS({
			url: this.createAuthUrl(workspace_fields.wms_endpoint),
			visible: true,
			params: prms,
			serverType: 'geoserver'
		});
		var wmsLayer = new ol.layer.Tile({
			source: wmsSource,
			visible: true
		});
	
	}
	
	wmsLayer.baselayer = false;
	wmsLayer.layer_name = layer_fields.name;
	wmsLayer.wms_url = this.createAuthUrl(workspace_fields.wms_endpoint);
	wmsLayer.wfs_url = this.createAuthUrl(workspace_fields.wfs_endpoint);
	wmsLayer.cache_url = this.createAuthUrl(workspace_fields.cache_endpoint);
	wmsLayer.title = layer_fields.title;
	wmsLayer.queryable = true;
	wmsLayer.is_vector = true;
	wmsLayer.write_roles = false;
	wmsLayer.namespace = namespace;
	wmsLayer.isTimeLayer = false;
	
	this.layerMap = wmsLayer;
	this.map.addLayer(this.layerMap);
	
	var that = this;	
	$.ajax({
		type: 'GET',
		async: true,
	  	url: wmsLayer.wfs_url,							
	  	data: {
	  		'service': 'WFS',
			'version': '1.1.0',
			'request': 'GetFeature',
			'typename': ws + ':' + layer_fields.name, 
			'outputFormat': 'application/json',
			'maxFeatures': 1
	  	},
	  	success	:function(response){
	  		if(response.features && response.features.length > 0){
		  		var newFeature = new ol.Feature();
		  		var sourceCRS = 'EPSG:' + response.crs.properties.name.split('::')[1];
		  		var projection = new ol.proj.Projection({
		    		code: sourceCRS,
		    	});
		    		
		    	if (response.features[0].geometry.type == 'Point') {
		    		newFeature.setGeometry(new ol.geom.Point(response.features[0].geometry.coordinates));				
		    	} else if (response.features[0].geometry.type == 'MultiPoint') {
		    		newFeature.setGeometry(new ol.geom.Point(response.features[0].geometry.coordinates[0]));				
		    	} else if (response.features[0].geometry.type == 'LineString' || response.features[0].geometry.type == 'MultiLineString') {
		    		newFeature.setGeometry(new ol.geom.MultiLineString([response.features[0].geometry.coordinates[0]]));
		    	} else if (response.features[0].geometry.type == 'Polygon' || response.features[0].geometry.type == 'MultiPolygon') {
		    		newFeature.setGeometry(new ol.geom.MultiPolygon(response.features[0].geometry.coordinates));
		    	}
		    	newFeature.setProperties(response.features[0].properties);
				newFeature.setId(response.features[0].id);
		    	var geom1 = newFeature.getGeometry().getFirstCoordinate();
		    	var geom2 = ol.proj.transform(geom1, sourceCRS, 'EPSG:3857');
							
		  		var view = that.map.getView();			
				if (response.features[0].geometry.type == 'Point' || response.features[0].geometry.type == 'MultiPoint') {
					view.setCenter(geom2);
					view.setZoom(7);
				} else {
					view.setCenter(geom2);
					view.setZoom(7);
				}
				
			}else{
				console.log("ERROR no features to center map preview");
			}
			
			var event = new CustomEvent("preview-map-painting-finished", { "detail": "Example of an event" });
			document.dispatchEvent(event);
	  	},
	  	error: function(e){
	  		console.log("ERROR centering map preview");
	  		var event = new CustomEvent("preview-map-painting-finished", { "detail": "Example of an event" });
			document.dispatchEvent(event);
	  	}
	});
};

SymbologyPreviewMap.prototype.createAuthUrl = function(url){
	var aux = url.match(/(http[s]?:\/\/)(.*)/);
	
	var new_url = url;
	if(aux.length > 1){
		new_url = aux[1];
		if(this.username != null && this.username != "" && this.password != null && this.password != ""){
			new_url = new_url + this.username + ":" + this.password + "@";
		}
		new_url = new_url + aux[2];
	}
	
	return new_url;
}

SymbologyPreviewMap.prototype.generateSLDCode = function(currentData){
	var workspace_fields = this.workspace[0]["workspace"][0].fields;
	var namespace = workspace_fields.uri;
	var uri = namespace.split('/');
	var ws = uri[uri.length - 1];

	var data = "";
	data = data + "<?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>";
    data = data + "<StyledLayerDescriptor version=\"1.0.0\" xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">"; 
    data = data +     "<NamedLayer>" ;
    data = data +         "<Name>" + ws + ":" + this.layer[0]["layer"][0].fields.name + "</Name>";
    data = data +         "<UserStyle>";
    data = data +             "<Name>" + ws + ":" + this.layer[0]["layer"][0].fields.name + "</Name>";
    data = data +             "<Title>" + this.layer[0]["layer"][0].fields.name + "</Title>"; 
    data = data +             "<FeatureTypeStyle>" ;
    
    
    
    data = data +                 "<Rule>";
    data = data +             "<Name>" + "Rule-1" + "</Name>";        
    data = data +   "<LineSymbolizer>";
    data = data +       "<Stroke>" ;
    data = data +           "<CssParameter name=\"stroke\">#FF0000</CssParameter>"; 
    data = data +           "<CssParameter name=\"stroke-width\">1</CssParameter>";
    data = data +       "</Stroke>";
    data = data +   "</LineSymbolizer>";
    data = data +                 "</Rule>"; 
    
    
    
    
    data = data +             "</FeatureTypeStyle>"; 
    data = data +         "</UserStyle>";
    data = data +     "</NamedLayer>";
    
    data = data + "</StyledLayerDescriptor>";
	
	return data;
};

SymbologyPreviewMap.prototype.reloadLayer = function(data){
	if(this.layerMap != null){
		var that = this;
		var layer_id = this.layer[0]["layer"][0].pk;
		ajaxPost(
			"/gvsigonline/symbology/get_sld_style2/"+layer_id+"/"+this.style+"/", 
			{
				'data': JSON.stringify(data),
			}, 
			function(content){
	            //onSuccess
	           	var sldCode = content["sld_code"];
				that.updateSLDLayer(sldCode); 
	        })
	
		
	}
}

SymbologyPreviewMap.prototype.updateSLDLayer = function(sldCode){
	this.layerMap.getSource().updateParams({'SLD_BODY': sldCode, 'STYLES': undefined}); 
	this.map.render();
};

SymbologyPreviewMap.prototype.createMapInContainer = function(container) {
	container.append(this.createMap());
};


SymbologyPreviewMap.prototype.updateSLD = function(sld_code) {

};
