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
 
var Intervals = function(workspace, layer, style, type, buttoncomp, panelcomp, fields) {	
	this.workspace = workspace;
	this.layer = layer;
	this.layer_id = layer[0]["layer"][0].pk;
	this.style = style;
	this.type = type;
	this.legendId = "IN";
	this.currentData = null;
	this.isFirstTime = true;
	this.fields = fields;
	
	this.symbologyUtils = new SymbologyUtils();
	this.formHelper = new SymbologyFormComponents();
	this.initializeButtonComponent(buttoncomp);
	
	this.previewMap = new  SymbologyPreviewMap(this.legendId, this.style);
	
	if(panelcomp != null){
		this.initializePanelComponent(panelcomp, fields);
	}
};

Intervals.prototype.initializeButtonComponent = function(component) {	
	var ui = '';
	ui += '<li class="item">';
	ui += 		'<div class="product-icon text-primary">';
	ui += 			'<i class="fa fa-sort-numeric-asc"></i>';
	ui += 		'</div>';
	ui += 		'<div class="product-info">';
	ui += 			'<a id="' + this.getID() + '" href="#!" id="option1" class="product-title legend-button option-selection">';
	ui += 				gettext("Intervals");							
	ui += 			'</a>';
	ui += 			'<span class="product-description">' + gettext("Intervals description") + '</span>';
	ui += 		'</div>';
	ui += '</li>';
	$("#"+component).append(ui);
};

/**
 * Initialize component method
 */
Intervals.prototype.initializePanelComponent = function(component, fields) {
	var panel = $("<div>", {id: this.getID() + "-panel", class:"step-2"});
	var preview = $("<div>", {class:"map-preview col s6", style:"float:left;"});
	var mapImage = this.previewMap.createMap();
	preview.append(mapImage);
	
	var mainPanel = $("<div>", {class:"legend-main-panel"});
	var maintitle = $("<div>", {class:"legend-main-title", text:"Panel de símbolo único"});
	
	var titleDiv = $("<div>", {class:"legend-div-title"});
	var star = $("<i>", {class:"fa fa-star default-legend-element"});
	var title = $("<span>", {class:"legend-title", text: gettext("Intervals")});
	titleDiv.append(title);
	titleDiv.append(star);
	mainPanel.append(titleDiv);
	
	var fieldChooser = this.formHelper.createSelectInput(
		gettext("Campos"), 
		this.getID()+"-field-input", 
		"",
		'{}', 
		gettext("Selecciona campo numerico"), 
		false, 
		false, 0);
	
	for(var i=0; i<fields.length; i++){
		if(fields[i].name.toLowerCase() != "geom" &&
			fields[i].name.toLowerCase() != "geometry"){
			var selectItem = $("<option>", {value: fields[i].name, text: fields[i].name});
			fieldChooser.find('select').append(selectItem);
		}
	}
	
	var intervalsInput = this.formHelper.createFormInput(
		gettext("Num intervalos"), 
		"interval-input", 
		"number",  
		1,
		100, 
		8, 
		false, 
		true, 0);
	
	mainPanel.append(fieldChooser);
	mainPanel.append(intervalsInput);
	var rulesTableDiv = $("<div>", {class: "legend-mainpanel hidden"});
	var rulesTable = $("<table>", {class: "legend-panel responsive-table highlight bordered"});
	var rulesTHead = $("<thead>");
	var rulesTr = $("<tr>");
	var rulesTh1 = $("<th>", {class:"symbol-header", "data-field": "preview", text: gettext("Symbol")});
	var rulesTh2 = $("<th>", {"data-field": "field", text: gettext("Field"), class: "symbol-row-title"});
	var rulesTh3 = $("<th>", {"data-field": "name", text: gettext("Name"), class: "symbol-row-title"});
	var rulesTh4 = $("<th>", {"data-field": "", text: "", class: "symbol-row-title  delete-buttons"});
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
	$("#"+this.getID()+"-field-input-0").change(function() {
		that.isFirstTime = false;
		that.updateIntervals();
	});
	
	$('#interval-input-0').on('change',function() {
		that.num_intervalos = parseInt($("#interval-input-0").val());
		if($("#"+that.getID()+"-field-input-0").val() != null){
			if(that.maxValue  && that.minValue){
		        that.createNewData();
		    }else{
		    	if(that.isFirstTime){
		    		that.updateIntervals();
		    	}else{
		    		that.symbologyUtils.showModal(
		        	"interval-modal", 
		        	gettext("Campo valido"), 
		        	gettext("Campo valido descripcion"), 
		        	function(){},
		        	false);
	        	}
	    	}
    	}
	});
	
};

Intervals.prototype.updateIntervals = function() {
		var field = $("#"+this.getID()+"-field-input-0").val();
		var that = this;
		
		ajaxPost("/gvsigonline/get_minmax_values/"+ that.layer_id +"/"+field+"/", {}, function(maxdata){
            	var content = JSON.parse(maxdata);
            	if(content.max != null && content.min != null){
            		that.maxValue = content.max;
            		that.minValue = content.min;
            		that.num_intervalos = parseInt($("#interval-input-0").val());
            		that.createNewData();
            	}else{
            		that.symbologyUtils.showModal(
	            	"interval-modal", 
	            	gettext("Calcular intervalos"), 
	            	gettext("Calcular intervalos descripcion"), 
	            	function(){},
	            	false);
            	}
        });
};


Intervals.prototype.getID = function() {
	return this.legendId;
};

Intervals.prototype.getFieldName = function(filter) {
	if(filter == null){
		return null;
	}
	
	var regexs = ["(.+)<=(.+)<=(.+)", "(.+)<(.+)<=(.+)", "(.+)<(.+)<=(.+)", "(.+)<(.+)<(.+)"];
	for(var i=0; i<regexs.length; i++){
		var re = new RegExp(regexs[i], "g");
		var fieldArray = re.exec(filter);
		if(fieldArray != null && fieldArray.length > 3){
			var field = fieldArray[2];
			return field.trim();
		}
	}
	
	return filter;
}

Intervals.prototype.getMinValue = function(filter) {
	if(filter == null){
		return null;
	}
	
	var regexs = ["(.+)<=(.+)<=(.+)", "(.+)<(.+)<=(.+)", "(.+)<(.+)<=(.+)", "(.+)<(.+)<(.+)"];
	for(var i=0; i<regexs.length; i++){
		var re = new RegExp(regexs[i], "g");
		var fieldArray = re.exec(filter);
		if(fieldArray != null && fieldArray.length > 3){
			var field = fieldArray[1];
			return field.trim();
		}
	}
	
	return filter;
}

Intervals.prototype.getMaxValue = function(filter) {
	if(filter == null){
		return null;
	}
	
	var regexs = ["(.+)<=(.+)<=(.+)", "(.+)<(.+)<=(.+)", "(.+)<(.+)<=(.+)", "(.+)<(.+)<(.+)"];
	for(var i=0; i<regexs.length; i++){
		var re = new RegExp(regexs[i], "g");
		var fieldArray = re.exec(filter);
		if(fieldArray != null && fieldArray.length > 3){
			var field = fieldArray[3];
			return field.trim();
		}
	}
	
	return filter;
}



/**
 * Load Data
 */
Intervals.prototype.loadData = function(data) {
	if(data.length>0){
		var field = this.getFieldName(data[0].rule[0].fields.filter);
		if(field != null && field != "" && field.length > 0){
			$("#"+this.getID()+"-field-input-0").val(field);
		}
		$("#interval-input-0").val(data.length);
		$(".legend-mainpanel").show();
	}
	var previews = []
	$("."+this.getID() + "-rules-ul").empty();
	for(var i=0;i<data.length; i++){
		
		for(var j=0; j<data[i].symbols.length; j++){
			var ruleTr = $("<tr>", {id:"symbol-"+i+"-"+j});
			var symbolPreviewButton = $("<td>", {
				class: "load-symbol-form-button",
				rule: i,
				symbol: j});
			var symbolPreview = $("<div>", {
				id:"symbol-"+i+"-"+j+"-preview", 
				class: ""});
			var symbolField = $("<td>", {class: "symbol-row-title symbol-row-filter"});
			var fieldInput =  $("<div>", {id: "symbol-field", class: "legend-row validate", text: data[i].rule[0].fields.name,  rule: i,  min: this.getMinValue(data[i].rule[0].fields.filter), max: this.getMaxValue(data[i].rule[0].fields.filter)});
			symbolField.append(fieldInput);
			var symbolName = $("<td>", {class: "symbol-row-title"});
			var nameInput =  $("<input>", {id: "symbol-name", class: "legend-row symbol-name validate", type: "text", value: this.symbologyUtils.decodeXML(data[i].symbols[0].fields.name), rule: i, symbol: j});
			symbolName.append(nameInput);
			
			var symbolDelete = $("<td>", {class: "symbol-row-title delete-buttons"});
			var deleteButton = $("<button>", {type: "button", 
				class: "button-delete-in btn-floating btn-flat waves-effect waves-light right red",
				"data-toggle": "tooltip",
				"data-placement": "bottom",
				rule: i,
				symbol: j});
			var deleteIconButton = $("<i>", {class: "fa fa-minus"});
			deleteButton.append(deleteIconButton);
			symbolDelete.append(deleteButton);			
			
			symbolPreviewButton.append(symbolPreview);
			ruleTr.append(symbolPreviewButton);
			ruleTr.append(symbolField);
			ruleTr.append(symbolName);
			ruleTr.append(symbolDelete);
			
			previews.push({'symbol': data[i].symbols[j], 'container': symbolPreview });
			$("."+this.getID() + "-rules-ul").append(ruleTr);
		}
		
		//$("."+this.getID() + "-rules-ul").append(ruleTr);
	}
	
	this.loadPreviews(previews);
	var that = this;
	$(".load-symbol-form-button").unbind("click").click(function(){
		var rule = $(this).attr("rule");
		var symbol = $(this).attr("symbol");
		var fds = {};
		for(var i=0; i<that.fields.length; i++){
			var fd = that.fields[i];
			fds[fd.name] = fd.name;
		}
		if(SLDDefaultValues[that.type].Geometry && 
			SLDDefaultValues[that.type].Geometry.Function && 
			SLDDefaultValues[that.type].Geometry.Function.definition){
				SLDDefaultValues[that.type].Geometry.Function.definition.fieldvalues = JSON.stringify(fds);
		}
		that.symbologyUtils.createSymbolForm(that, that.getID(), that.type, that.currentData, rule, symbol, $(this).parent(), that.style);
	});
	
	$(".button-delete-in").click(function(){
		var rule = $(this).attr("rule");
		var symbol = $(this).attr("symbol");
		that.currentData.splice(rule, 1);
		that.loadData(that.currentData);
	});
	
	$(".symbol-row-filter").unbind("click").click(function(){
		var min = $(this).find("div").attr("min");
		var max = $(this).find("div").attr("max");
		
		var rule = $(this).find("div").attr("rule");
		
		$("#modal-interval-symbology").openModal();
		
		$("#interval-min-input").val(parseFloat(min));
		$("#interval-max-input").val(parseFloat(max));
		
		$(".update-interval").unbind("click").click(function(){
			var min = $("#interval-min-input").val();
			var max = $("#interval-max-input").val();
			
			that.currentData[rule].rule[0].fields.filter = min+"<="+$("#"+that.getID()+"-field-input-0").val()+"<="+max;
			that.currentData[rule].rule[0].fields.name = min+"-"+max;
						
			$("#modal-interval-symbology").closeModal();
			
			that.loadData(that.currentData);
		});
	});
	
	$(".symbol-name").unbind("change").change(function(){
		var rule = $(this).attr("rule");
		var symbol = $(this).attr("symbol");
		that.currentData[rule].symbols[symbol].fields.name = that.symbologyUtils.encodeXML($(this).val());
	});
	this.currentData = data;
	this.previewMap.reloadLayer(this.currentData);
};

Intervals.prototype.loadPreviewMap = function(workspace, layer, username, password) {	
	this.previewMap.loadMap(workspace, layer, username, password);
};

Intervals.prototype.createNewData = function() {
	var symbologyUtils = new SymbologyUtils();
	
	this.currentData = [];
	var colors = symbologyUtils.createColorRange("Intervals", this.num_intervalos, this.colorstart, this.colorend);
	
    var name = $("#"+this.getID()+"-field-input-0").val();
	for(var i=0; i<this.num_intervalos; i++){
		// Creamos la regla con un símbolo estándar 
		var min = this.getMinValueForInterval(this.minValue, this.maxValue, i, this.num_intervalos);
		var max = this.getMaxValueForInterval(this.minValue, this.maxValue, i, this.num_intervalos);
		
		var fieldFilter = "";
		var fieldName = min+"-"+max;
		
		if(name != null && name != ""){
				fieldFilter = min + "<=" + name + "<=" + max;
		}else{
			fieldFilter = "";
		}
		
		var rl = symbologyUtils.createEmptyRule(this.style, fieldName, fieldFilter, i);
		var sm = this.symbologyUtils.createEmptySymbol(fieldName, this.type, colors[i]);
		var rls = {"rule": [rl], "symbols": [sm]};
		this.currentData.push(rls);
	}

	this.loadData(this.currentData);
	
};

Intervals.prototype.getMinValueForInterval = function(min, max, it, num_intervalos){
	if(it == 0){
		return min;
	}
	var gap = (max-min)/num_intervalos;
	var value = min + (gap*it);
	
	return value;
}

Intervals.prototype.getMaxValueForInterval = function(min, max, it, num_intervalos){
	if(it == num_intervalos-1){
		return max;
	}
	var gap = (max-min)/num_intervalos;
	var value = min + (gap*(it+1));
	
	return value;
}

Intervals.prototype.loadPreviews = function(previews) {
	for(var i=0; i<previews.length; i++){
		var symbologyPreview = new SymbologyPreview(null);
		var sldjson = $.xml2json("<StoredSLD>" +
					previews[i].symbol.fields.sld_code + "</StoredSLD>");
			
		var symbolPreview = symbologyPreview.renderPreview(
				sldjson[this.type], 
				this.type, 
				previews[i].container.attr("id"));
		if(symbolPreview != null){
			previews[i].container.append(symbolPreview);
		}
	}
	
};

/**
 * Get Data
 */
Intervals.prototype.getData = function() {
	return this.currentData;
};

Intervals.prototype.getInitialColor = function() {
	if(this.colorstart){
		return this.colorstart;
	}
	return "#FFFFFF";
}

Intervals.prototype.getFinalColor = function() {
	if(this.colorend){
		return this.colorend;
	}
	return "#000000";
}

Intervals.prototype.updateColorRamp = function(color_ini, color_fin){
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
