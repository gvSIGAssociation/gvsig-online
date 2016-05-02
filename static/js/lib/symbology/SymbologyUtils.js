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

var xmlDocument = null;
var symbologyEditor = null;

var SymbologyUtils = function(sEditor) {	
	this.symbologyEditor = sEditor;
};

SymbologyUtils.prototype.getKeys = function(json) {
	var keys = Object.keys(json);

	// HACK para borrar campos residuales
	if(!(json instanceof Array)){
		for(var idx = keys.length-1; idx>=0; idx--){
			if($.isNumeric(keys[idx])){
				keys.splice(idx,1);
			}
		}
	}

	return keys;
};


SymbologyUtils.prototype.json2xml = function(json, label) {
	var xmlstring = "";
	xmlDocument = $.parseXML("<"+label+"></"+label+">");
	if(xmlDocument){
		xmlDocument = this.createXMLComponent(xmlDocument.documentElement, json, xmlDocument.documentElement);

		var xmlData = $(xmlDocument);
		if(window.ActiveXObject){
			var xmlstring = xmlData.xml;
		}else{
			var oSerializer = new XMLSerializer();
			xmlstring = oSerializer.serializeToString(xmlData[0]);
			xmlDocument = null;

		}
	}
	return xmlstring;
};


SymbologyUtils.prototype.createXMLComponent = function(comp, json, parcomp) {
	if( typeof json === 'string'){
						var newTxt = xmlDocument.createTextNode(json);
						comp.appendChild(newTxt);
						return comp;
	}
	var keys = this.getKeys(json);
	if(keys.length == 1){
		var curcomp = comp;
		var parentcomp = null;
		while(keys.length == 1){
			var k = keys[0];   // sólo se ejecutará una vez
			if(!$.isNumeric(k)){ // continuamos por los hijos
				var first = k.charAt(0);
				if(first === first.toUpperCase() && first !== first.toLowerCase()){  
					// Si empieza por mayúscula
					// es un hijo
					var newel = xmlDocument.createElement(k);
					comp.appendChild(newel);
					parentcomp = comp;
					comp = newel;
				}
				if(first === first.toLowerCase() && first !== first.toUpperCase()){  
					// Si empieza por minúscula es un atributo de la etiqueta en la que estamos
					if(k == "text"){
						var newTxt = xmlDocument.createTextNode(json[k]);
						comp.appendChild(newTxt);
						return curcomp;
					}else{
						var newatt=xmlDocument.createAttribute(k);
						newatt.nodeValue=json[k];
						comp.setAttributeNode(newatt);

					}
				}
			}
			json = json[k];
			if(json instanceof Array){
				//for(var ix=0; ix<json.length; ix++){
					parentcomp.appendChild(this.createXMLComponent(comp, json, parentcomp));
				//}
				return parentcomp;
			}else{
				if( typeof json === 'string'){
							var newTxt = xmlDocument.createTextNode(json);
							comp.appendChild(newTxt);
							keys = [];
				}else{
					keys = this.getKeys(json);
				}
			}
		}
		if(keys.length>1){
			if(this.hasMultipleElements(keys) && parentcomp != null){
				//parentcomp.removeChild(parentcomp.childNodes[0]);
				for(var i=0;i<keys.length; i++){
					var clonecomp = comp.cloneNode(true);
					parentcomp.appendChild(this.createXMLComponent(clonecomp, json[keys[i]], parentcomp));
				}
			}else{
				this.createXMLComponent(comp, json, parentcomp);
			}
		}
		return curcomp;
	}else{
		var curjson = json;
		for(var ind=0; ind<keys.length; ind++){
			var k = keys[ind];
			if($.isNumeric(k)){ // continuamos por los hijos
				//this.createXMLComponent(comp, curjson[k], parcomp);

				if(this.hasMultipleElements(keys) && parcomp != null){
					var clonecomp = comp.cloneNode(true);
					parcomp.appendChild(this.createXMLComponent(clonecomp, curjson[k], parcomp));
				}else{
					var newel = this.createXMLComponent(comp, curjson[k], parcomp);
					comp.appendChild(newel);
				}
			}else{
				var first = k.charAt(0);
				if(first === first.toUpperCase() && first !== first.toLowerCase()){  
					// Si empieza por mayúscula
					// es un hijo
					var newel = this.createXMLComponent(xmlDocument.createElement(k), curjson[k], comp);
					comp.appendChild(newel);
				}
				if(first === first.toLowerCase() && first !== first.toUpperCase()){  
					// Si empieza por minúscula
					// es un atributo de la etiqueta en la que estamos
					if(k == "text"){
						var newTxt = xmlDocument.createTextNode(curjson[k]);
						comp.appendChild(newTxt);
						//return comp;
					}else{
						var newatt=xmlDocument.createAttribute(k);
						newatt.nodeValue=curjson[k];
						comp.setAttributeNode(newatt);
					}
				}
			}
		}
	}
	return comp;
};

SymbologyUtils.prototype.hasMultipleElements = function(keys) {
	for(var idx = 0; idx < keys.length; idx++){
		if($.isNumeric(keys[idx])){
			return true;
		}
	}
	return false;
};

SymbologyUtils.prototype.createModal = function(iden, title, content, func, showCancel, onReady) {
	var mainDiv = $("<div>", {id: iden, class:"modal"});
	var contentDiv = $("<div>", {class:"modal-maincontent"});
	
	var contentTitleDiv = $("<h5>", {class:"modal-title red-text", text:title});
	var contentPDiv = $("<p>", {class:"modal-content", text: content});
	contentDiv.append(contentTitleDiv);
	contentDiv.append(contentPDiv);
	
	mainDiv.append(contentDiv);
	
	var footerDiv = $("<div>", {class:"modal-footer", style: "width: 98%;"});
	var footerDivButton = $("<button>", {id: iden+"-ok", class:"waves-effect waves-green btn-flat grey-text darken-1", text: "Ok"});
	footerDiv.append(footerDivButton);
	
	if(showCancel){
		var footerDivCancelButton = $("<button>", {id: iden+"-cancel", class:"waves-effect waves-green btn-flat grey-text darken-1", text: "Cancel"});
		footerDiv.append(footerDivCancelButton);
	}
	
	mainDiv.append(footerDiv);
	
	$("body").append(mainDiv);
	
	$('#'+iden).openModal({
    	dismissible: false, // Modal can be dismissed by clicking outside of the modal
    	opacity: .5, // Opacity of modal background
    	in_duration: 300, // Transition in duration
    	out_duration: 200, // Transition out duration
    	ready: onReady, // Callback for Modal open
    	complete: function() {} // Callback for Modal close
    });
	
	$('#'+iden+"-ok").click( function() {
		$('#'+iden).closeModal();
		if(func){
			func();
		}
	});
	
	if(showCancel){
		$('#'+iden+"-cancel").click( function() {
			$('#'+iden).closeModal();
		});
	}
};

SymbologyUtils.prototype.showModal = function(id, title, content, func, showCancel, onReady) {
	if(!onReady){
		onReady = function(){};
	}

	if(!$('#'+id).length){
		this.createModal(id, title, content, func, showCancel, onReady);
	}else{
		$('#'+id+" .modal-title").empty();
		$('#'+id+" .modal-title").append(title);
		$('#'+id+" .modal-content").empty()
		$('#'+id+" .modal-content").append(content);
		$('#'+id).openModal({
	    	dismissible: false, // Modal can be dismissed by clicking outside of the modal
	    	opacity: .5, // Opacity of modal background
	    	in_duration: 300, // Transition in duration
	    	out_duration: 200, // Transition out duration
	    	ready: onReady, // Callback for Modal open
	    	complete: function() {} // Callback for Modal close
	    });
		
		$('#'+id+"-ok").unbind("click").click( function() {
			if(func){
				func();
			}
			$('#'+id).closeModal();
		});
	}
};
SymbologyUtils.prototype.createEmptyRule = function(styd, nm, rule, ord){
	if(ord == null){
		ord = 0;
	}
	return {
		pk: null,
		fields: {
			name: nm,
			filter: rule,
			order: ord,
			style_id: styd
		}
	};
};
	
SymbologyUtils.prototype.createEmptySymbol = function(nm, type, color){
		var symbol = {};
		if(color == null){
			color = "#000000";
		}
		if(type == "PointSymbolizer"){
			 symbol = {
				pk: null,
				fields: {
					name: nm,
					sld_code: "<PointSymbolizer>"+
	            "<Graphic>"+
	              "<Mark>"+
	                "<WellKnownName>circle</WellKnownName>"+
	                "<Fill>"+
	                  "<CssParameter name=\"fill\">"+
	                    color+
	                  "</CssParameter>"+
			  			"<CssParameter name=\"fill-opacity\">"+
	                    "1.0"+
	                  "</CssParameter>"+
	                "</Fill>"+
	                "<Stroke>"+
	                  "<CssParameter name=\"stroke\">"+
	                    color+
	                  "</CssParameter>"+
	                  "<CssParameter name=\"stroke-width\">"+
	                    "1"+
	                  "</CssParameter>"+
	                  "<CssParameter name=\"stroke-opacity\">"+
	                    "1.0"+
	                  "</CssParameter>"+
	                "</Stroke>"+
	              "</Mark>"+
	              "<Opacity>"+
	                "1.0"+
	              "</Opacity>"+
	              "<Size>"+
	                "6"+
	              "</Size>"+
	            "</Graphic>"+
	         "</PointSymbolizer>"
				}
			};
		}
		
		if(type == "LineSymbolizer"){
			 symbol = {
				pk: null,
				fields: {
					name: nm,
					sld_code: "<LineSymbolizer>"+
			           "<Stroke>"+
			              "<CssParameter name=\"stroke\">"+color+"</CssParameter>"+
			              "<CssParameter name=\"stroke-width\">3</CssParameter>"+
			            "</Stroke>"+
	         		"</LineSymbolizer>"
				}
			};
		}
		
		if(type == "PolygonSymbolizer"){
			 symbol = {
				pk: null,
				fields: {
					name: nm,
					sld_code: "<PolygonSymbolizer>"+
			            "<Fill>"+
			              "<CssParameter name=\"fill\">"+color+"</CssParameter>"+
			              "<CssParameter name=\"fill-opacity\">1</CssParameter>"+
			            "</Fill>"+
			            "<Stroke>"+
			              "<CssParameter name=\"stroke\">"+color+"</CssParameter>"+
			              "<CssParameter name=\"stroke-width\">1</CssParameter>"+
			            "</Stroke>"+
	         "</PolygonSymbolizer>"
				}
			};
		}
		
		if(type == "RasterSymbolizer"){
			 symbol = {
				pk: null,
				fields: {
					name: nm,
					sld_code: "<RasterSymbolizer>"+
			            "<Opacity>"+
			              "1"+
			            "</Opacity>"+
			            "<ColorMap>"+
			            "</ColorMap>"+
	         "</RasterSymbolizer>"
				}
			};
		}
		
		if(type == "TextSymbolizer"){
			 symbol = {
				pk: null,
				fields: {
					name: nm,
					sld_code: "<TextSymbolizer>"+
         					"<Label>"+
           						"<PropertyName>name</PropertyName>"+
         					"</Label>"+
         					"<Font>"+
           						"<CssParameter name=\"font-family\">Arial</CssParameter>"+
           						"<CssParameter name=\"font-size\">12</CssParameter>"+
           						"<CssParameter name=\"font-style\">normal</CssParameter>"+
					        "</Font>"+
         					"<Fill>"+
           						"<CssParameter name=\"fill\">#000000</CssParameter>"+
           						"<CssParameter name=\"fill-opacity\">1</CssParameter>"+
         					"</Fill>"+
       					"</TextSymbolizer>"
				}
			};
		}
			
		return symbol;
	};
	
SymbologyUtils.prototype.createSymbolForm = function(style, styleType, featureType, data, rule, symbol, parent, style_id){
		var symbolForm = new  SymbologySymbolForm(parent, style.layer);
		var symbologyUtils = new SymbologyUtils();
		var rl = symbologyUtils.createEmptyRule(style_id, "");
		var sym = symbologyUtils.createEmptySymbol(parent.find("#symbol-name").val(), featureType);
		if(rule != "-1" && symbol != "-1"){
			rl = data[rule];
		}else{
			data = [];
			var rls = {"rule": [rl], "symbols": []};
			data.push(rls);
			rule = data.length-1;
			parent.find(".load-symbol-form-button").attr("rule", rule);
		}
		
		if(symbol != "-1"){
			sym = data[rule].symbols[symbol];
		}else{
			data[rule].symbols.push(sym);
			symbol = data[rule].symbols.length-1;
			parent.find(".load-symbol-form-button").attr("symbol", symbol);
		}
		symbolForm.createForm(featureType, sym, null, rule, symbol, false);

		var that = this;
		$('#modal-symbology').modal('show');
		$("#modal-symbology").on('show.bs.modal', function () {
			var sldjson = $.xml2json("<StoredSLD>" + sym.fields.sld_code + "</StoredSLD>");
	     	symbolForm.loadPreviews(sldjson[featureType]);
		});
		$("#modal-symbology").on('shown.bs.modal', function () {
			data[rule].symbols[symbol] = symbolForm.getData();
      		that.loadData(style, styleType, data);
      		$(".load-symbol-form-button").unbind("click").click(function(){
				var rule = $(this).attr("rule");
				var symbol = $(this).attr("symbol");
				var symbologyUtils = new SymbologyUtils();
				symbologyUtils.createSymbolForm(style, styleType, featureType, data, rule, symbol, $(this).parent(), style_id);
			});
		});
};

SymbologyUtils.prototype.loadData = function(legend, styleType, data){
		if(styleType == legend.getID()){
			legend.loadData( data );
		}
	};
	
	
SymbologyUtils.prototype.rgb2hex = function(rgb){
	 var rgb = rgb.match(/^rgba?[\s+]?\([\s+]?(\d+)[\s+]?,[\s+]?(\d+)[\s+]?,[\s+]?(\d+)[\s+]?/i);
	 return (rgb && rgb.length === 4) ? "#" +
	  ("0" + parseInt(rgb[1],10).toString(16)).slice(-2) +
	  ("0" + parseInt(rgb[2],10).toString(16)).slice(-2) +
	  ("0" + parseInt(rgb[3],10).toString(16)).slice(-2) : '';
};

SymbologyUtils.prototype.createColorRange = function(type, num_colors, init_color, end_color){
	var colors = [];
	for(var i=0; i<num_colors; i++){
		if(type == "Default"){
			colors.push("#000000");
		}
		if(type == "Random"){
			colors.push(this.getRandomColor());
		}
		if(type == "Intervals"){
			if(!init_color || !end_color){
				init_color = "#FF0000";
				end_color = "#0000FF"
			}
			colors.push(this.getIntervalColor(init_color, end_color, num_colors, i));
		}
	}
	return colors;
}

SymbologyUtils.prototype.convertHex = function(hex){
    hex = hex.replace('#','');
    r = parseInt(hex.substring(0,2), 16);
    g = parseInt(hex.substring(2,4), 16);
    b = parseInt(hex.substring(4,6), 16);

    return {'red': r, 'green': g, 'blue': b};
}


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
}

SymbologyUtils.prototype.getRandomColor = function() {
    var letters = '0123456789ABCDEF'.split('');
    var color = '#';
    for (var i = 0; i < 6; i++ ) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

SymbologyUtils.prototype.encodeXML = function (cad) {
    return cad.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;')
               .replace(/"/g, '&quot;')
               .replace(/'/g, '&apos;');
  };

SymbologyUtils.prototype.decodeXML = function (cad) {
    return cad.replace(/&apos;/g, "'")
               .replace(/&quot;/g, '"')
               .replace(/&gt;/g, '>')
               .replace(/&lt;/g, '<')
               .replace(/&amp;/g, '&');
  };
  
  
  