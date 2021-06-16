/**
 * gvSIG Online.
 * Copyright (C) 2010-2017 SCOLAB.
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

var SymbologyUtils = function(map, layer_id, layer, featureType, previewUrl, fonts, alphanumericFields) {
	this.map = map;
	this.layer = layer;
	this.layer_id = layer_id;
	this.fonts = fonts;
	this.alphanumericFields = alphanumericFields;
	this.previewUrl = previewUrl;
	this.featureType = featureType;
	this.type = 'EX';
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

SymbologyUtils.prototype.linePatterns = [
	{value: 'none', imgsrc: IMG_PATH + 'default-symbol.png'},
	{value: '5 10', imgsrc: IMG_PATH + '5_10.png'},
	{value: '10 5', imgsrc: IMG_PATH + '10_5.png'},
	{value: '5 1', imgsrc: IMG_PATH + '5_1.png'},
	{value: '1 5', imgsrc: IMG_PATH + '1_5.png'},
	{value: '15 10 5 10', imgsrc: IMG_PATH + '15_10_5_10.png'},
	{value: '5 5 1 5', imgsrc: IMG_PATH + '5_5_1_5.png'},
];

SymbologyUtils.prototype.external_graphic_formats = [
	{value: 'image/png', title: 'image/png'},
	{value: 'image/jpeg', title: 'image/jpeg'},
	{value: 'image/gif', title: 'image/gif'}
];

SymbologyUtils.prototype.filter_operations = [
 	{value: 'is_equal_to', title: gettext('Is equal to') + ' ...'},
 	{value: 'is_null', title: gettext('Is null') + ' ...'},
 	{value: 'is_like', title: gettext('Contains') + ' ...'},
 	{value: 'is_not_equal', title: gettext('Is not equal') + ' ...'},
 	{value: 'is_greater_than', title: gettext('Is greater than') + ' ...'},
 	{value: 'is_greater_than_or_equal_to', title: gettext('Is greater than or equal to') + ' ...'},
 	{value: 'is_less_than', title: gettext('Is less than') + ' ...'},
 	{value: 'is_less_than_or_equal_to', title: gettext('Is less than or equal to') + ' ...'},
 	{value: 'is_between', title: gettext('Is between') + ' ...'}
];

SymbologyUtils.prototype.getLayerId = function(){
	return this.layer_id;
};

SymbologyUtils.prototype.getFilterOperations = function(element){
	return this.filter_operations;
};

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
		    	
		  		if(response.features[0].geometry != null){
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

SymbologyUtils.prototype.centerMapToExtent = function(ext, epsg) {
	var leftBottom = ol.proj.transform([ext.minx, ext.miny], epsg, 'EPSG:3857');
	var rightTop = ol.proj.transform([ext.maxx, ext.maxy], epsg, 'EPSG:3857');
	
	var extent = $.merge(leftBottom, rightTop);
	this.map.getView().fit(extent, this.map.getSize());			
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
		if (style instanceof ColorTable) {
			sld +=	this.getColorMap(style.rule.entries);
			
		} else {
			for (var i=0; i < symbolizers.length; i++) {
				sld += symbolizers[i].toXML()
			}
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
			if (style.rules[i].filter != '') {
				sld +=	this.getFilter(style.rules[i].filter);
			}
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


SymbologyUtils.prototype.setType = function(type) {
	this.type = type;
}
	
SymbologyUtils.prototype.getFilter = function(json_filter) {
	
	var filter = '';
	
	filter += '<ogc:Filter>';
	if (json_filter.type != 'is_between') {
		var operator = '';
		if (json_filter.type == 'is_equal_to') {
			operator = 'PropertyIsEqualTo';
			
		} else if (json_filter.type == 'is_null') {
			operator = 'PropertyIsNull';
			
		} else if (json_filter.type == 'is_like') {
			operator = 'PropertyIsLike';
			
		} else if (json_filter.type == 'is_not_equal') {
			operator = 'PropertyIsNotEqualTo';
			
		} else if (json_filter.type == 'is_greater_than') {
			operator = 'PropertyIsGreaterThan';
			
		} else if (json_filter.type == 'is_greater_than_or_equal_to') {
			operator = 'PropertyIsGreaterThanOrEqualTo';
			
		} else if (json_filter.type == 'is_less_than') {
			operator = 'PropertyIsLessThan';
			
		} else if (json_filter.type == 'is_less_than_or_equal_to') {
			operator = 'PropertyIsLessThanOrEqualTo';
			
		}
		
		filter += 	'<ogc:' + operator + '>';
		filter += 		'<ogc:PropertyName>' + json_filter.property_name + '</ogc:PropertyName>';
		if (json_filter.type != 'is_null') {
			filter += 		'<ogc:Literal>' + json_filter.value + '</ogc:Literal>';
		}
		filter += 	'</ogc:' + operator + '>';
		
	} else {
		filter += 	'<ogc:PropertyIsBetween>';
		filter += 		'<ogc:PropertyName>' + json_filter.property_name + '</ogc:PropertyName>';
		filter += 		'<ogc:LowerBoundary>';
		filter += 			'<ogc:Literal>' + json_filter.value1 + '</ogc:Literal>';
		filter += 		'</ogc:LowerBoundary>';
		filter += 		'<ogc:UpperBoundary>';
		filter += 			'<ogc:Literal>' + json_filter.value2 + '</ogc:Literal>';
		filter += 		'</ogc:UpperBoundary>';
		filter += 	'</ogc:PropertyIsBetween>';
		
	}
	filter += '</ogc:Filter>';
	
	return filter;
};

SymbologyUtils.prototype.getColorMap = function(entries) {
	var colorMap = '';
	
	colorMap += '<RasterSymbolizer>';
	colorMap += '<ColorMap type="ramp" extended="false">';
	for (var i=0; i<entries.length; i++) {
		colorMap += '<ColorMapEntry color="' + entries[i].color + '" quantity="' + entries[i].quantity + '" label="' + entries[i].label + '" opacity="' + entries[i].opacity + '"/>';
	}
	colorMap += '</ColorMap>';
	colorMap += '</RasterSymbolizer>';
	
	return colorMap;
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

SymbologyUtils.prototype.reloadLayerPreview = function(name){
	var layers = this.map.getLayers();
	var self = this;
	layers.forEach(function(layer){
		if (!layer.baselayer && !layer.external) {
			if (layer.get("id") === 'preview-layer') {
				layer.getSource().updateParams({'STYLES': name+"__tmp", "_time": (new Date()).getTime()});
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

SymbologyUtils.prototype.rgba2hex = function(rgba){
	 var parts = rgba.substring(rgba.indexOf("(")).split(","),
     r = parseInt(parts[0].substring(1).trim(), 10),
     g = parseInt(parts[1].trim(), 10),
     b = parseInt(parts[2].trim(), 10),
     a = parseFloat((parts[3].substring(0, parts[3].length - 1)).trim());

	 return  {"color": '#' + ("0"+r.toString(16)).slice(-2) + ("0"+g.toString(16)).slice(-2) + ("0"+b.toString(16)).slice(-2), "alpha": a};
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

SymbologyUtils.prototype.getColorFromRamp = function(json_data, min, max, crr) {
	var current = (parseFloat(crr) - parseFloat(min))*100/(parseFloat(max) - parseFloat(min))
	var color_ini = null;
	var color_fin = null;
	for(var i = 0; i < json_data["definition"].length; i++){
		var def = json_data["definition"][i];
		if((!color_ini && (current - def["quantity"]) >= 0 ) || ((current - def["quantity"]) >= 0 && (current - color_ini["quantity"]) > (current - def["quantity"]))){
			color_ini = def;
		}
		if((!color_fin && (def["quantity"] - current) >= 0 ) || ((def["quantity"] - current) >= 0 && (color_fin["quantity"] - current) > (def["quantity"] - current))){
			color_fin = def;
		}		
	}
	if(color_ini && color_fin){
		if(color_ini["quantity"] == color_fin["quantity"]){
			var rgb_ini = this.convertHex(color_ini["color"]);
			return "rgba("+Math.round(rgb_ini.red)+","+Math.round(rgb_ini.green)+","+Math.round(rgb_ini.blue)+","+color_ini["alpha"]+")";
		}else{
			var porc_color = (current - color_ini["quantity"])/ (color_fin["quantity"] - color_ini["quantity"]);
			var rgb_ini = this.convertHex(color_ini["color"]);
		    var rgb_fin = this.convertHex(color_fin["color"]);
		    var red = ((rgb_fin.red - rgb_ini.red)*porc_color)+rgb_ini.red;
		    var green = ((rgb_fin.green - rgb_ini.green)*porc_color)+rgb_ini.green;
		    var blue = ((rgb_fin.blue - rgb_ini.blue)*porc_color)+rgb_ini.blue;
		    var alpha = ((parseFloat(color_fin["alpha"]) - parseFloat(color_ini["alpha"]))*porc_color)+parseFloat(color_ini["alpha"]);
		    return "rgba("+Math.round(red)+","+Math.round(green)+","+Math.round(blue)+","+alpha+")";
		}
	}
	
	return "rgba(0,0,0,0)";
};


SymbologyUtils.prototype.sld = function(layerId, type, symbology) {
	var self = this;
	var rules = symbology.rules;
	var label = symbology.label;
	
	var minscale = $('#symbol-minscale').val();
	if(minscale == "" || minscale < 0){
		minscale = -1;
	}

	var maxscale = $('#symbol-maxscale').val();
	if(maxscale == "" || maxscale < 0){
		maxscale = -1;
	}

	var style = {
			name: $('#style-name').val(),
			title: $('#style-title').val(),
			minscale: minscale,
			maxscale: maxscale,
			is_default: $('#style-is-default').is(":checked"),
			rules: new Array()
	};

	for (var i=0; i<rules.length; i++) {
		if(!rules[i].name.endsWith("_text")){
			var symbolizers = new Array();
			for (var j=0; j < rules[i].getSymbolizers().length; j++) {
				var symbolizer = {
						type: rules[i].getSymbolizers()[j].type,
						json: rules[i].getSymbolizers()[j].toJSON(),
						order: rules[i].getSymbolizers()[j].order
				};
				symbolizers.push(symbolizer);
			}

			symbolizers.sort(function(a, b){
				return parseInt(a.order) - parseInt(b.order);
			});

			var rule = {
					rule: rules[i].getObject(),
					symbolizers: symbolizers
			};
			style.rules.push(rule);
		}
	}

	if (label != null && label.is_activated()) {
		var ruleName = "rule_" + rules.length +"_text";
		var ruleTitle = label.title;
		var l = {
				type: label.type,
				json: label.toJSON(),
				order: label.order
		};

		var options = {
				"id" : rules.length,
				"name" : ruleName,
				"title" : ruleTitle,
				"abstract" : "",
				"filter" : label.filterCode,
				"minscale" : label.minscale,
				"maxscale" :  label.maxscale,
				"order" :  label.order
		}
		var rl = new Rule(i, ruleName, ruleTitle, options, this.utils);
		var rule = {
				rule: rl.getObject(),
				symbolizers: [l]
		};
		style.rules.push(rule);
	}

	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/create_sld/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrftoken'));
		},
		data: {
			type: self.type,
			layer_id: layerId,
			style_data: JSON.stringify(style)
		},
		success: function(response){
			if (response.success) {
				self.reloadLayerPreview(response.sld);
			} else {
				alert('Error');
			}

		},
		error: function(){}
	});
};
