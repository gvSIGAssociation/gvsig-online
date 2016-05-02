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
 
var ColorTable = function(workspace, layer, style, type, buttoncomp, panelcomp, fields) {	
	this.workspace = workspace;
	this.layer = layer;

	this.style = style;
	this.type = type;
	this.legendId = "CT";
	this.currentData = null;
	this.isFirstTime = true;
	this.fields = fields;
	this.num_intervalos = 8;
	
	this.symbologyUtils = new SymbologyUtils();
	this.formHelper = new SymbologyFormComponents();
	this.initializeButtonComponent(buttoncomp);
	
	this.previewMap = new  SymbologyPreviewMap(this.legendId, this.style);
	
	this.layer_id = layer[0]["layer"][0].pk;
	this.minValue = layer[0]["layer"][0].fields.rastermin;
	this.maxValue = layer[0]["layer"][0].fields.rastermax;
	
	if(panelcomp != null){
		this.initializePanelComponent(panelcomp, fields);
	}
	
};

ColorTable.prototype.initializeButtonComponent = function(component) {
	var container = $("<li>", {class:"collection-item avatar"});
	
	var icon = $("<i>", { class:"material-icons circle fa  fa-picture-o"});
	var title = $("<span>", {text: gettext("Colortable"), class:"title"});
    var desc = $("<p>", {html: gettext("Colortable descripcion")});

	var aLink  = $("<a>", {id: this.getID(), href: "#!", class: "secondary-content legend-button"});
	var iLink  = $("<i>", {class: "go-icon fa fa-chevron-right"});
	aLink.append(iLink);

	container.append(icon);
	container.append(title);
	container.append(desc);
	container.append(aLink);
	
	$("#"+component).append(container);
};

/**
 * Initialize component method
 */
 
ColorTable.prototype.getInitialColor = function() {
	if(this.colorstart){
		return this.colorstart;
	}
	return "#FFFFFF";
}

ColorTable.prototype.getFinalColor = function() {
	if(this.colorend){
		return this.colorend;
	}
	return "#000000";
}


ColorTable.prototype.initializePanelComponent = function(component, fields) {
	var panel = $("<div>", {id: this.getID() + "-panel", class:"step-2"});
	var preview = $("<div>", {class:"map-preview col s6", style:"float:left;"});
	var mapImage = this.previewMap.createMap();
	preview.append(mapImage);
	
	var mainPanel = $("<div>", {class:"legend-main-panel"});
	var maintitle = $("<div>", {class:"legend-main-title", text:"Panel de símbolo único"});
	
	var titleDiv = $("<div>", {class:"legend-div-title"});
	var star = $("<i>", {class:"fa fa-star default-legend-element"});
	var title = $("<span>", {class:"legend-title", text: gettext("Colortable")});
	titleDiv.append(title);
	titleDiv.append(star);
	mainPanel.append(titleDiv);
	
	
	for(var i=0; i<fields.length; i++){
		if(fields[i].name.toLowerCase() != "geom" &&
			fields[i].name.toLowerCase() != "geometry"){
			var selectItem = $("<option>", {value: fields[i].name, text: fields[i].name});
		}
	}
	
	var intervalsInput = this.formHelper.createFormInput(
		gettext("Num intervalos"), 
		"colortable-input", 
		"number",  
		1,
		100, 
		8, 
		false, 
		true, 0);
	
	mainPanel.append(intervalsInput);
	var rulesTableDiv = $("<div>", {class: "legend-mainpanel hidden"});
	var rulesTable = $("<table>", {class: "legend-panel responsive-table highlight bordered"});
	var rulesTHead = $("<thead>");
	var rulesTr = $("<tr>");
	var rulesTh1 = $("<th>", {"data-field": "preview", text: gettext("Color"), class:"symbol-row-colortable"});
	var rulesTh2 = $("<th>", {"data-field": "field", text: gettext("Opacidad"), class: "symbol-row-colortable"});
	var rulesTh3 = $("<th>", {"data-field": "quantity", text: gettext("Quantity"), class: "symbol-row-colortable"});
	var rulesTh4 = $("<th>", {"data-field": "name", text: gettext("Name"), class: "symbol-row-colortable"});
	var rulesTBody = $("<tbody>", {class: this.getID() + "-rules-ul"});
	
	var separator = $("<div>", {class: "clearBoth"});
	
	panel.append(preview);
	panel.append(mainPanel);
	panel.append(separator);

	rulesTable.append(rulesTHead);
	rulesTable.append(rulesTBody);
	rulesTHead.append(rulesTr);
	rulesTr.append(rulesTh1);
	rulesTr.append(rulesTh2);
	rulesTr.append(rulesTh3);
	rulesTr.append(rulesTh4);
	//rulesTable.append(rules);
	rulesTableDiv.append(rulesTable);
	panel.append(rulesTableDiv);

	$("#"+component).append(panel);
	
	var that = this;
	$('#colortable-input-0').on('change',function() {
		that.num_intervalos = parseInt($("#colortable-input-0").val());
		if(that.maxValue != null  && that.minValue != null){
	        that.createNewData();
	    }else{
	    	if(that.isFirstTime){
	    		that.updateIntervals();
	    	}else{
	    		that.symbologyUtils.showModal(
	        	"colortable-modal", 
	        	gettext("Campo valido"), 
	        	gettext("Campo valido descripcion"), 
	        	function(){},
	        	false);
        	}
    	}
    	
	});
	
};

ColorTable.prototype.updateIntervals = function() {
		var that = this;
		if(this.minValue == null || this.maxValue == null){
			ajaxPost("/gvsigonline/get_minmax_rastervalues/"+ that.layer_id +"/"+ that.style +"/", {}, function(content){
	            	if(content.max != null && content.min != null){
	            		that.maxValue = content.max;
	            		that.minValue = content.min;
	            		that.nullValue = content.null;
	            		that.num_intervalos = parseInt($("#colortable-input-0").val());
	            		if(that.num_intervalos<=0){
	            			that.num_intervalos = 1;
	            		}
	            		that.createNewData();
	            	}else{
	            		that.symbologyUtils.showModal(
		            	"colortable-modal", 
		            	gettext("Calcular raster"), 
		            	gettext("Calcular raster descripcion"), 
		            	function(){
		            		//alert("Modificar min y máximo a mano");
		            		//window.location.href = "/gvsigonline/style_layer_update/"+ that.layer_id +"/"+ that.style +"/";
		            	},
		            	false);
	            	}
	        });
        }else{
        	that.createNewData();
        }
};


ColorTable.prototype.getID = function() {
	return this.legendId;
};


ColorTable.prototype.getColorMapData = function(sldCode) {
	var cMaps = [];
	
	/* Extraemos los tags ColorMapEntry */
	var regex = new RegExp("ColorMapEntry ([^\/]*)", "g");
	if(sldCode != null && sldCode.match(regex)){
		var match = [];
		while (result = regex.exec(sldCode)){
			if(result.length>0){
				match.push(result[1]);
			}
		}
		for(var i=0; i<match.length; i++){
			var cmap = {};
			
			cmap["color"] = "#000000";
			var color = match[i].match(/color="([^"]*)/);
			if(color && color.length>0){
				cmap["color"] = color[1];
			}
			
			cmap["opacity"] = "1";
			var opacity = match[i].match(/opacity="([^"]*)/);
			if(opacity && opacity.length>0){
				cmap["opacity"] = parseFloat(opacity[1]);
			}
			
			cmap["quantity"] = "0";
			var quantity = match[i].match(/quantity="([^"]*)/);
			if(quantity && quantity.length>0){
				cmap["quantity"] = quantity[1];
			}
			
			cmap["label"] = "0";
			var label = match[i].match(/label="([^"]*)/);
			if(label && label.length>0){
				cmap["label"] = label[1];
			}
			cMaps.push(cmap);
		}
	}
	
	return cMaps;
}


/**
 * Load Data
 */
 
ColorTable.prototype.updateColorRamp = function(color_ini, color_fin){
	if(color_ini != this.colorstart || color_fin != this.colorend){
		this.colorstart = color_ini;
		this.colorend = color_fin;
		if(this.minValue == null || this.maxValue == null){
			this.updateIntervals();
		}else{
			this.createNewData();
		}
	}
}

ColorTable.prototype.updateNullMinMaxValues = function(nullValue, minValue, maxValue){
		this.nullValue = parseFloat(nullValue);
		this.minValue = parseFloat(minValue);
		this.maxValue = parseFloat(maxValue);
		if(this.nullValue != null && this.minValue != null && this.maxValue != null){
			this.createNewData();
		}
}

ColorTable.prototype.getNullValue = function(){
		return this.nullValue;
}

ColorTable.prototype.getMinValue = function(){
		return this.minValue;
}

ColorTable.prototype.getMaxValue = function(){
		return this.maxValue;
}


ColorTable.prototype.loadData = function(data) {
	//this.updateIntervals();
	
	$("."+this.getID() + "-rules-ul").empty();
	if(data.length > 0){
		$(".legend-mainpanel").show();
	}

	for(var i=0;i<data.length; i++){
		for(var j=0; j<data[i].symbols.length; j++){
			this.colorMaps = this.getColorMapData(data[i].symbols[j].fields.sld_code);
			$('#colortable-input-0').val(this.colorMaps.length-1);
			if(this.colorMaps.length>0){
				this.colornull = this.colorMaps[0].color;
				this.nullValue = parseFloat(this.colorMaps[0].quantity)
				this.colorstart = this.colorMaps[0].color;
				if(this.colorMaps.length>1){
					this.colorstart = this.colorMaps[1].color;
					this.minValue = parseFloat(this.colorMaps[1].quantity);
					var penultimValue = parseFloat(this.colorMaps[this.colorMaps.length-1].quantity);
					this.maxValue = ((penultimValue-this.minValue)/(this.colorMaps.length-2))*(this.colorMaps.length-1);
				}
				this.colorend = this.colorMaps[this.colorMaps.length-1].color;
			}
			
			for(var k=0; k<this.colorMaps.length; k++){
				var ruleTr = $("<tr>", {id:"symbol-"+i+"-"+j+"-"+k});
				var symbolColor = $("<td>", {class: "symbol-row-colortable"});
				var colorInput =  $("<input>", {id: "symbol-color-"+k, class: "symbol-color waves-effect waves-light btn color-chooser legend-row validate", type: "color", value:this.colorMaps[k].color, style:"display:block", colorMap: k});
				symbolColor.append(colorInput);
				
				var symbolOpacity = $("<td>", {class: "symbol-row-colortable"});
				var opacityInput =  $("<input>", {id: "symbol-opacity-"+k, class: "symbol-opacity legend-row validate", type: "number", min: 0, max:1, step:0.01, value: this.colorMaps[k].opacity, colorMap: k});
				symbolOpacity.append(opacityInput);
				
				var symbolField = $("<td>", {class: "symbol-row-colortable"});
				var fieldInput =  $("<input>", {id: "symbol-field-"+k, class: "symbol-quantity legend-row validate", type: "number", min: null, max:null, step:0.01, value: this.colorMaps[k].quantity, colorMap: k});
				symbolField.append(fieldInput);
				
				var symbolName = $("<td>", {class: "symbol-row-colortable"});
				var nameInput =  $("<input>", {id: "symbol-name-"+k, class: "symbol-label legend-row validate", type: "text", value: this.symbologyUtils.decodeXML(this.colorMaps[k].label), colorMap: k});
				symbolName.append(nameInput);
				
				ruleTr.append(symbolColor);
				ruleTr.append(symbolOpacity);
				ruleTr.append(symbolField);
				ruleTr.append(symbolName);
				
				$("."+this.getID() + "-rules-ul").append(ruleTr);
			}
		}
	}
	
	var that = this;
	
	$(".symbol-label").unbind("change").change(function(){
		var colorMap = $(this).attr("colorMap");
		that.colorMaps[colorMap].label = that.symbologyUtils.encodeXML($(this).val());
		that.previewMap.reloadLayer(that.getData());
	});
	
	$(".symbol-opacity").unbind("change").change(function(){
		var colorMap = $(this).attr("colorMap");
		that.colorMaps[colorMap].opacity = $(this).val();
		that.previewMap.reloadLayer(that.getData());
	});
	
	$(".symbol-quantity").unbind("change").change(function(){
		var colorMap = $(this).attr("colorMap");
		that.colorMaps[colorMap].quantity = $(this).val();
		that.previewMap.reloadLayer(that.getData());
	});
	
	$(".symbol-color").unbind("change").change(function(e){
		var colorMap = $(this).attr("colorMap");
		that.colorMaps[colorMap].color = $(this).val();
		that.previewMap.reloadLayer(that.getData());
	});
	
	this.currentData = data;
	
	if(this.isFirstTime){
		this.isFirstTime = false;
		//this.loadData(this.currentData);
	}
	//this.previewMap.reloadLayer(this.currentData);
};

ColorTable.prototype.loadPreviewMap = function(workspace, layer, username, password) {	
	var that = this;
	document.addEventListener("preview-map-painting-finished", function(e) {
	  that.loadData(that.currentData);
	}); 
	this.previewMap.loadMap(workspace, layer, username, password);
};

ColorTable.prototype.createNewData = function() {
	var symbologyUtils = new SymbologyUtils();
	
	this.colorMaps = null;
	this.currentData = [];
	var colors = symbologyUtils.createColorRange("Intervals", this.num_intervalos, this.colorstart, this.colorend);
	if(!this.colornull){
		var color = symbologyUtils.createColorRange("Random", 1);
		this.colornull = color[0];
	}
	
    var name = $("#"+this.getID()+"-field-input").val();
    var rl = symbologyUtils.createEmptyRule(this.style, "ColorTableRule", "", 0);
    var sm = this.symbologyUtils.createEmptySymbol("ColorTable", "RasterSymbolizer", colors[i]);
    var colorMapsText = "";
    if(this.nullValue != null){
    	colorMapsText = colorMapsText + "<ColorMapEntry color=\""+this.colornull+"\" quantity=\""+this.nullValue+"\" opacity=\"0\" label=\""+this.nullValue+"\" />";
	}	
	
	for(var i=0; i<this.num_intervalos; i++){
		// Creamos la regla con un símbolo estándar 
		var min = this.getMinValueForInterval(this.minValue, this.maxValue, i, this.num_intervalos);
		var max = this.getMaxValueForInterval(this.minValue, this.maxValue, i, this.num_intervalos);

		colorMapsText = colorMapsText + "<ColorMapEntry color=\""+colors[i]+"\" quantity=\""+min+"\" opacity=\"1\" label=\""+min+"\" />";
		
	}
	
	sm["fields"]["sld_code"] = sm["fields"]["sld_code"].replace("<ColorMap></ColorMap>", "<ColorMap>"+colorMapsText+"</ColorMap>");
	var rls = {"rule": [rl], "symbols": [sm]};
	this.currentData.push(rls);

	this.loadData(this.currentData);
	
};

ColorTable.prototype.getMinValueForInterval = function(min, max, it, num_intervalos){
	if(it == 0){
		return min;
	}
	var gap = (max-min)/num_intervalos;
	var value = min + (gap*it);
	
	return value;
}

ColorTable.prototype.getMaxValueForInterval = function(min, max, it, num_intervalos){
	if(it == num_intervalos-1){
		return max;
	}
	var gap = (max-min)/num_intervalos;
	var value = min + (gap*(it+1));
	
	return value;
}


/**
 * Get Data
 */
ColorTable.prototype.getData = function() {
	
	if(this.currentData.length>0){
		var colorMapsText = "";
		for(var i=0; i<this.colorMaps.length; i++){
			colorMapsText = colorMapsText + "<ColorMapEntry color=\""+this.colorMaps[i].color+"\" quantity=\""+this.colorMaps[i].quantity+"\" opacity=\""+this.colorMaps[i].opacity+"\" label=\""+this.colorMaps[i].label+"\" />";
		}
	
		var new_sld_code = "<RasterSymbolizer>"+
				            "<Opacity>"+"1"+"</Opacity>"+
				            "<ColorMap>"+
				            	colorMapsText+
				            "</ColorMap>"+
		         			"</RasterSymbolizer>"
		this.currentData[0]["symbols"][0]["fields"]["sld_code"] = new_sld_code;
	}

	return this.currentData;
};
