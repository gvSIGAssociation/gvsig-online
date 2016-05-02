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

var preview = null;
var symbologyEditor = null;
var svgpreview = null;
var imgpreview = null;

var SymbologyPreview = function(sEditor) {	
	this.symbologyEditor = sEditor;
};

SymbologyPreview.prototype.clearPreview= function (preview) {
	this.svgpreview.clear();
};

SymbologyPreview.prototype.renderPreview= function (params, symbolType, id) {
	this.attributes = {};
	this.svgpreview = SVG(id);
	this.svgpreview.clear();
	this.graphicPaths = {
			"triangle": "M37.96299934387207 34.83204650878906L31.5 23.638047218322754C30.674999237060547 22.209047317504883 29.324999809265137 22.209047317504883 28.5 23.638047218322754L22.036999702453613 34.83204650878906C21.211999893188477 36.26104736328125 21.88699960708618 37.43004608154297 23.536999702453613 37.43004608154297H36.46299934387207C38.11300086975098 37.43004608154297 38.78800010681152 36.26104736328125 37.96299934387207 34.83204650878906z ",
			"star": "M29.998046875 37.2109375L21.114047050476074 43.665937423706055L24.51004695892334 33.22793769836426L15.627046585083008 26.76993751525879L26.606046676635742 26.771937370300293L30.00004768371582 16.3359375L33.391048431396484 26.76993751525879H44.372047424316406L35.48604774475098 33.22693634033203L38.88204765319824 43.665937423706055L29.998046875 37.2109375L29.998046875 37.2109375z ",
			"cross": "M39.998531341552734 26.665531158447266L33.3315315246582 26.665531158447266L33.3315315246582 19.998531341552734L26.666531562805176 19.998531341552734L26.666531562805176 26.665531158447266L19.998531341552734 26.665531158447266L19.998531341552734 33.3315315246582L26.666531562805176 33.3315315246582L26.666531562805176 39.998531341552734L33.3315315246582 39.998531341552734L33.3315315246582 33.3315315246582L39.998531341552734 33.3315315246582z ",
			"x": "M38.33073425292969 35.50298500061035L32.82873344421387 30.00098419189453L38.329734802246094 24.498984336853027L35.50173377990723 21.668984413146973L29.99973487854004 27.170984268188477L24.49773406982422 21.668984413146973L21.669734001159668 24.498984336853027L27.170734405517578 30.00098419189453L21.668734550476074 35.50298500061035L24.49873447418213 38.33198356628418L29.99973487854004 32.82998466491699L35.50073432922363 38.33198356628418z ",
			"square": "M20 20H40V40H20z"
	};
	
	if(!Array.isArray(params)){
		params = [params];
	}
	
	for(var i=0; i<params.length; i++){
		if (symbolType === "PointSymbolizer") {
			this.renderPoint(params[i]);
		} else if (symbolType === "LineSymbolizer") {
			this.renderLine(params[i]);
		} else if (symbolType === "PolygonSymbolizer") {
			this.renderPolygon(params[i]);
		} else if (symbolType === "TextSymbolizer") {
			this.renderText(params[i]);
		} else {
			console.log("geometryType of params is not defined");
		}
	}

	//var bbox = this.svgpreview.bbox();

	return this.preview;
};

SymbologyPreview.prototype.renderPoint= function (data) {
	// graphic paths are from this website: http://raphaeljs.com/icons/
	//parse attributes and check if the element is Mark or ExternalGraphic
	var hasWellKnownName = false;
	var imageurl = "";
	var params = this.createParams(data, "PointSymbolizer");
	this.elementSize = 20;
	this.elementRotation = 0;
	var wellknownname = null;
	for (var i=0; i < params.length; i++) {
		if (params[i].attributeName === "wellknownname") {
			hasWellKnownName = true;
			wellknownname = params[i].value
		} else if (params[i].attributeName === "size") {
			this.elementSize = params[i].value;
		} else if (params[i].attributeName === "rotation") {
			this.elementRotation = params[i].value;
		} else if (params[i].attributeName === "src-image") {
			hasWellKnownName = false;
			imageurl = params[i].value
		} else {
			var attribute = params[i].attributeName;
			var attributeValue = params[i].value;
			this.attributes[attribute] = attributeValue;
			if (params[i].attributeName === "stroke"){
				this.attributes["stroke-width"] = 1;
			}
		}
	}
	//create preview element
	this.preview = this.svgpreview;
	if (hasWellKnownName === false && imageurl != "") {
		this.renderExternalGraphics(imageurl);
	}
	if(hasWellKnownName === true){
		this.renderWellKnownName(wellknownname);
	}
	this.svgpreview.show();
};

SymbologyPreview.prototype.renderWellKnownName= function(wellknownname) {
	if (!wellknownname || wellknownname == "circle") {
		this.previewElement = this.svgpreview.circle(this.elementSize);
		this.previewElement.center(30,30);
	} else {
		if(!this.graphicPaths[wellknownname]){
			wellknowname = "square";
		}
		var path = this.graphicPaths[wellknownname];
		this.previewElement = this.svgpreview.path(path);
		this.previewElement.size(this.elementSize);
	}
	this.previewElement.attr(this.attributes);
	this.previewElement.transform({rotation: this.elementRotation});
};

SymbologyPreview.prototype.renderExternalGraphics= function (url) {
	//console.log('External graphics are not yet supported');
	if(typeof url === 'string' || url instanceof String){
		this.xlink = "/media/" + url;
		if(!url.startsWith("/media/")){
			url = "/media/" + url;
		}
	}else{
		if(url["OnlineResource"] && url["OnlineResource"]["xlink:href"]){
			var urlx = url["OnlineResource"]["xlink:href"];
			var url_parts = urlx.split("/media/")
			if(url_parts.length > 1){
				var aux = "";
				for(var i=1; i<url_parts.length; i++){
					aux = aux + "/media/" + url_parts[i];
				}
				url = aux;
				this.xlink = aux;
			}else{
				url = urlx;
			}
		}
	}
	var size = 50;
	if(this.elementSize < 50){
		size = this.elementSize;
	}
	
	/*
	this.imgpreview = $("<img>", {class: "symbol-img-preview", src: url, width:size, height:size});
	this.previewElement =  this.imgpreview;
	*/
	this.previewElement = this.preview.image(this.xlink, this.elementSize);
	this.previewElement.center(30,30);
	this.previewElement.transform({rotation: this.elementRotation});
	
};

SymbologyPreview.prototype.renderLine= function (data) {
	var params = this.createParams(data, "LineSymbolizer");
	var widthline = 8;
	var wellknownname = null;
	var hasWellKnownName = false;
	for (var i=0; i < params.length; i++) {
		var attribute = params[i].attributeName;
		var attributeValue = params[i].value;
		this.attributes[attribute] = attributeValue;
		if (attribute == "stroke-width") {
			widthline = attributeValue;
		}
		if (params[i].attributeName === "wellknownname") {
			hasWellKnownName = true;
			wellknownname = params[i].value
		}
		if(params[i].attributeName === "size") {
			this.elementSize = params[i].value;
			widthline = params[i].value;
		} 
		if(params[i].attributeName === "rotation") {
			this.elementRotation = params[i].value;
		}
	}
	if(hasWellKnownName === true){
		this.renderWellKnownName(wellknownname);
	}else{
		this.previewElement = this.svgpreview.line(5,5,55,55).stroke({width: widthline});
	}
	this.previewElement.attr(this.attributes);
};

SymbologyPreview.prototype.renderPolygon= function (data) {
	var strokeWidth = false;
	var params = this.createParams(data, "PolygonSymbolizer");
	var imageurl = "";
	var wellknownname = null;
	var hasWellKnownName = false;
	for (var i=0; i < params.length; i++) {
		var attribute = params[i].attributeName;
		var attributeValue = params[i].value;
		this.attributes[attribute] = attributeValue;
		if (params[i].attributeName === "src-image") {
			imageurl = params[i].value
		}
		if (params[i].attributeName === "size") {
			this.elementSize = params[i].value
		} 
		if (params[i].attributeName === "wellknownname") {
			hasWellKnownName = true;
			wellknownname = params[i].value
		}
	}
	this.preview = this.svgpreview;
	if(imageurl != "") {
		this.renderExternalGraphics(imageurl);
	}else{
//		if(hasWellKnownName === true){
//			this.renderWellKnownName(wellknownname);
//		}else{
			this.previewElement = this.svgpreview.polygon('5,15 60,5 40,60 5,40');
//		}
	}
	this.previewElement.attr(this.attributes);
};

SymbologyPreview.prototype.renderText= function (data) {
	var params = this.createParams(data, "TextSymbolizer");
	for (i=0; i < params.length; i++) {
		var attribute = params[i].attributeName;
		var attributeValue = params[i].value;
		if (attribute === "font-family" || attribute === "font-style" || attribute === "font-weight" || attribute === "fill" || attribute === "halo-color" || attribute === "halo-radius") {
			this.attributes[attribute] = attributeValue;
		}
	}
	this.previewElement = this.svgpreview.text("AaBb").font({size: 24});
	this.previewElement.attr(this.attributes);
	this.previewElement.center(30,30);
};

SymbologyPreview.prototype.updatePreview= function () {
	if (_.has(this.attributes, "stroke") && (this.symbolType === "pointsymbolizer" || this.symbolType === "polygonsymbolizer")) {
		this.attributes["stroke-width"] = 3;
	}
	this.previewElement.attr(this.attributes);
};


SymbologyPreview.prototype.createParamsComponent = function(params, json, definition, type) {
	var formComponent = {};
	if(definition.component == "panel-chooser-input"){
		for(var i=0; i<definition.values.length; i++){
			this.createsubParams(params, json, definition.values[i], type);
		}
	}else{
		var value = definition.defaultValue;
	
		if(json != null){
			var auxValuePath = jsonPath(json, definition.jsonPath, {resultType:"PATH"});
			if(!auxValuePath){
				//auxValuePath = jsonPath(json,  definition.jsonPath.replace("text", "Literal[0].text"), {resultType:"PATH"});
				//auxValuePath = jsonPath(json.Graphic.Mark.Fill, "$.CssParameter[?(@.name=='fill')].text", {resultType:"PATH"});
				auxValuePath = jsonPath(json,  definition.jsonPath.replace(/\[\?.*?\]/g, ""), {resultType:"PATH"});
			}
			if(auxValuePath && auxValuePath.length > 0){
				var auxValue = this.getAccessByString(json, auxValuePath[0]);
				
				if(auxValue && definition.previewAttrName){
					value = auxValue;
					if(Array.isArray(auxValue)){
						value = auxValue[0];
					}
					if(auxValue.text){
						value = auxValue.text;
					}
					
					formComponent["value"]= value;
					formComponent["attributeName"]= definition.previewAttrName;
					params.push(formComponent);
				}	
			}
		}
	}

};

SymbologyPreview.prototype.createsubParams = function(params, data, json, type) {
	for(var key in json){
		if(json[key].type && json[key].type == "field-definition"){
			if(json[key].definition){
				this.createParamsComponent(params, data, json[key].definition, type);
			}
		}else{
			this.createsubParams(params, data, json[key], type);
		}
	}
};

SymbologyPreview.prototype.createParams = function(data, type) {
	var params = [];
	var featureType = SLDDefaultValues[type];
	this.createsubParams(params, data, featureType, type);

	return params;
};


SymbologyPreview.prototype.getAccessByString = function(o, s) {
	var obj = o;
	s = s.substring(1);
    s = s.replace(/\['(\w+)\']/g, '.$1'); // convert indexes to properties
    s = s.replace(/\[(\w+)\]/g, '.$1'); // convert indexes to properties
    s = s.replace(/^\./, '');           // strip a leading dot
    var a = s.split('.');
    for (var i = 0, n = a.length; i < n; ++i) {
        var k = a[i];
        if(isNaN(k)){
        	if(obj != ""){
		        if (k in obj) {
		        	obj = obj[k];
		        }else{
		        	return;
		        }
	        }
        } else {
        	var index = parseInt(k);
        	if(obj instanceof Array){
	        	if(obj.length > index){
	        		obj = obj[index]
	        	}else{
	            	return;
	            }
            }
        }
    }    
    
    return obj;
};