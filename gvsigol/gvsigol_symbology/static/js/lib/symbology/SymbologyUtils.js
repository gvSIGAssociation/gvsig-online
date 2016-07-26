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
 * @author: Javi Rodrigo <jrodrigo@scolab.es>
 */

var SymbologyUtils = function(map, layer, featureType, previewUrl, fonts, alphanumericFields) {
	this.map = map;
	this.layer = layer;
	this.fonts = fonts;
	this.alphanumericFields = alphanumericFields;
	this.previewUrl = previewUrl;
	this.featureType = featureType;
};

SymbologyUtils.prototype.fontStyles = [
	{value: 'normal', title: gettext('Normal')},
	{value: 'cursive', title: gettext('Cursive')},
	{value: 'oblique',title: gettext('Oblique')}
];

SymbologyUtils.prototype.fontWeights = [
	{value: 'normal', title: gettext('Normal')},
	{value: 'bold', title: gettext('Bold')}
];

SymbologyUtils.prototype.shapes = [
	{value: 'circle', title: gettext('Circle')},
	{value: 'square', title: gettext('Square')},
	{value: 'triangle', title: gettext('Triangle')},
	{value: 'star', title: gettext('Star')},
	{value: 'cross', title: gettext('Cross')},
	{value: 'x', title: 'X'}
];

SymbologyUtils.prototype.external_graphic_formats = [
	{value: 'image/png', title: 'image/png'},
	{value: 'image/jpeg', title: 'image/jpeg'},
	{value: 'image/gif', title: 'image/gif'}
];

SymbologyUtils.prototype.getFonts = function(element){
	return this.fonts;
};

SymbologyUtils.prototype.getFontStyles = function(element){
	return this.fontStyles;
};

SymbologyUtils.prototype.getFontWeights = function(element){
	return this.fontWeights;
};

SymbologyUtils.prototype.getShapes = function(element){
	return this.shapes;
};

SymbologyUtils.prototype.getAlphanumericFields = function(element){
	return this.alphanumericFields;
};

SymbologyUtils.prototype.centerMap = function(layerName, wfsUrl) {
	var self = this;
	$.ajax({
		type: 'GET',
		async: true,
	  	url: wfsUrl,							
	  	data: {
	  		'service': 'WFS',
			'version': '1.1.0',
			'request': 'GetFeature',
			'typename': layerName, 
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
							
		  		var view = self.map.getView();			
				if (response.features[0].geometry.type == 'Point' || response.features[0].geometry.type == 'MultiPoint') {
					view.setCenter(geom2);
					view.setZoom(7);
				} else {
					view.setCenter(geom2);
					view.setZoom(7);
				}
				
			} else {
				console.log("ERROR no features to center map preview");
			}
	  	},
	  	error: function(e){
	  		console.log("ERROR centering map preview");
	  	}
	});
};

SymbologyUtils.prototype.updateMap = function(style, name) {
	
	var sld = '';
	sld += '<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" ';
	sld +=  'xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" ';
	sld +=  'xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">';
	sld += 	'<NamedLayer>';  
	sld +=  	'<Name>' + name + '</Name>';  
	sld +=      '<UserStyle>';
	sld +=          '<Name>' + name + '</Name>';
	sld +=          '<Title>' + name + '</Title>';
	sld +=          '<FeatureTypeStyle>';
	
	if (style.rule) {
		var symbolizers = style.rule.getSymbolizers().slice(0);
		if (style.label) {
			symbolizers.push(style.label);
		}
		sld +=          	'<Rule>';
		sld +=          		'<Name>' + name + '</Name>';
		sld +=          		'<Title>' + name + '</Title>';
		for (var i=0; i < symbolizers.length; i++) {
			sld += symbolizers[i].toXML()
		}
		sld +=          	'</Rule>';
	}
	
	if (style.rules) {
		for (var i=0; i<style.rules.length; i++) {
			var symbolizers = style.rules[i].getSymbolizers().slice(0);
			if (style.label) {
				symbolizers.push(style.label);
			}
			sld +=          	'<Rule>';
			sld +=          		'<Name>' + name + '</Name>';
			sld +=          		'<Title>' + name + '</Title>';
			for (var j=0; j < symbolizers.length; j++) {
				sld += symbolizers[j].toXML()
			}
			sld +=          	'</Rule>';
		}
		
	}
	
	sld +=          '</FeatureTypeStyle>';
	sld +=      '</UserStyle>';
	sld += 	'</NamedLayer>';
	sld += '</StyledLayerDescriptor>';
	
	this.reloadLayerPreview(sld);
	
};

SymbologyUtils.prototype.getSLDBody = function(symbolizers, name, title) {
	
	var sld = '';
	sld += '<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" ';
	sld +=  'xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" ';
	sld +=  'xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">';
	sld += 	'<NamedLayer>';  
	sld +=  	'<Name>' + name + '</Name>';  
	sld +=      '<UserStyle>';
	sld +=          '<Name>' + name + '</Name>';
	sld +=          '<Title>' + title + '</Title>';
	sld +=          '<FeatureTypeStyle>';
	sld +=          	'<Rule>';
	sld +=          		'<Name>' + name + '</Name>';
	sld +=          		'<Title>' + title + '</Title>';
	for (var i=0; i < symbolizers.length; i++) {
		sld += symbolizers[i].toXML()
	}
	sld +=          	'</Rule>';
	sld +=          '</FeatureTypeStyle>';
	sld +=      '</UserStyle>';
	sld += 	'</NamedLayer>';
	sld += '</StyledLayerDescriptor>';
	
	return sld;
};

SymbologyUtils.prototype.reloadLayerPreview = function(sld_body){
	var layers = this.map.getLayers();
	var self = this;
	layers.forEach(function(layer){
		if (!layer.baselayer) {
			if (layer.get("id") === 'preview-layer') {
				layer.getSource().updateParams({'SLD_BODY': sld_body, time_: (new Date()).getTime()});
				self.map.render();
			}
		};
	}, this);
};

SymbologyUtils.prototype.generateUUID = function() {
    var S4 = function() {
       return (((1+Math.random())*0x10000)|0).toString(16).substring(1);
    };
    return (S4()+S4()+"-"+S4()+"-"+S4()+"-"+S4()+"-"+S4()+S4()+S4());
};

SymbologyUtils.prototype.getPreviewUrl = function() {
    return this.previewUrl;
};

SymbologyUtils.prototype.getFeatureType = function() {
    return this.featureType;
};

SymbologyUtils.prototype.createColorRange = function(type, num_colors, init_color, end_color){
	var colors = [];
	for(var i=0; i<num_colors; i++){
		if(type == "default"){
			colors.push("#000000");
		}
		if(type == "random"){
			colors.push(this.getRandomColor());
		}
		if(type == "intervals"){
			if(!init_color || !end_color){
				init_color = "#FF0000";
				end_color = "#0000FF"
			}
			colors.push(this.getIntervalColor(init_color, end_color, num_colors, i));
		}
	}
	return colors;
};

SymbologyUtils.prototype.rgb2hex = function(rgb){
	 var rgb = rgb.match(/^rgba?[\s+]?\([\s+]?(\d+)[\s+]?,[\s+]?(\d+)[\s+]?,[\s+]?(\d+)[\s+]?/i);
	 return (rgb && rgb.length === 4) ? "#" +
	  ("0" + parseInt(rgb[1],10).toString(16)).slice(-2) +
	  ("0" + parseInt(rgb[2],10).toString(16)).slice(-2) +
	  ("0" + parseInt(rgb[3],10).toString(16)).slice(-2) : '';
};

SymbologyUtils.prototype.convertHex = function(hex){
    hex = hex.replace('#','');
    r = parseInt(hex.substring(0,2), 16);
    g = parseInt(hex.substring(2,4), 16);
    b = parseInt(hex.substring(4,6), 16);

    return {'red': r, 'green': g, 'blue': b};
};

SymbologyUtils.prototype.getIntervalColor = function(init_color, end_color, num_colors, it) {
    var rgbinit = this.convertHex(init_color);
    var rgbend = this.convertHex(end_color);
    
    if(it == 0){
    	return init_color;
    }
    
    if(it == num_colors-1){
    	return end_color;
    }
    
    var gapred = (rgbend.red - rgbinit.red)/num_colors;
    var red = Math.round(rgbinit.red + (gapred*it));
    
    var gapgreen = (rgbend.green - rgbinit.green)/num_colors;
    var green = Math.round(rgbinit.green + (gapgreen*it));
    
    var gapblue = (rgbend.blue - rgbinit.blue)/num_colors;
    var blue = Math.round(rgbinit.blue + (gapblue*it));
    
    return this.rgb2hex("rgb("+red+","+green+","+blue+")");
};

SymbologyUtils.prototype.getRandomColor = function() {
    var letters = '0123456789ABCDEF'.split('');
    var color = '#';
    for (var i = 0; i < 6; i++ ) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
};