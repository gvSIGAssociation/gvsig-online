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
 
var UniqueValues = function(workspace, layer, style, type, buttoncomp, panelcomp, fields) {	
	this.workspace = workspace;
	this.layer = layer;
	this.layer_id = layer[0]["layer"][0].pk;
	this.style = style;
	this.type = type;
	this.legendId = "VU";
	this.currentData = null;
	this.fields = fields;
	
	this.symbologyUtils = new SymbologyUtils();
	this.formHelper = new SymbologyFormComponents();
	this.initializeButtonComponent(buttoncomp);
	
	this.previewMap = new  SymbologyPreviewMap(this.legendId, this.style);
	
	if(panelcomp != null){
		this.initializePanelComponent(panelcomp, fields);
	}
};

UniqueValues.prototype.initializeButtonComponent = function(component) {	
	var ui = '';
	ui += '<li class="item">';
	ui += 		'<div class="product-icon text-primary">';
	ui += 			'<i class="fa fa-list"></i>';
	ui += 		'</div>';
	ui += 		'<div class="product-info">';
	ui += 			'<a id="' + this.getID() + '" href="#!" id="option1" class="product-title legend-button option-selection">';
	ui += 				gettext("Unique Values");							
	ui += 			'</a>';
	ui += 			'<span class="product-description">' + gettext("Unique Values description") + '</span>';
	ui += 		'</div>';
	ui += '</li>';
	$("#"+component).append(ui);
};

/**
 * Initialize component method
 */
UniqueValues.prototype.initializePanelComponent = function(component, fields) {
	var panel = $("<div>", {id: this.getID() + "-panel", class:"step-2"});
	
	var preview = $("<div>", {class:"map-preview col s6", style:"float:left;"});
	var mapImage = this.previewMap.createMap();
	preview.append(mapImage);
	
	var mainPanel = $("<div>", {class:"legend-main-panel"});
	var maintitle = $("<div>", {class:"legend-main-title", text:"Panel de símbolo único"});
	
	var titleDiv = $("<div>", {class:"legend-div-title"});
	var star = $("<i>", {class:"fa fa-star default-legend-element"});
	var title = $("<span>", {class:"legend-title", text: gettext("Unique Values")});
	titleDiv.append(title);
	titleDiv.append(star);
	mainPanel.append(titleDiv);
	
	var fieldChooser = this.formHelper.createSelectInput(
		gettext("Campos"), 
		this.getID()+"-field-input", 
		"",
		'{}', 
		gettext("Selecciona campo"), 
		false, 
		false, 0);
	
	for(var i=0; i<fields.length; i++){
		if(fields[i].name.toLowerCase() != "geom" &&
			fields[i].name.toLowerCase() != "geometry"){
			var selectItem = $("<option>", {value: fields[i].name, text: fields[i].name});
			fieldChooser.find('select').append(selectItem);
		}
	}
	
	mainPanel.append(fieldChooser);
	var rulesTableDiv = $("<div>", {class: "legend-mainpanel hidden"});
	var rulesTable = $("<table>", {class: "legend-panel responsive-table highlight bordered"});
	var rulesTHead = $("<thead>");
	var rulesTr = $("<tr>");
	var rulesTh1 = $("<th>", {class:"symbol-header", "data-field": "preview", text:  gettext("Symbol")});
	var rulesTh2 = $("<th>", {"data-field": "field", text:  gettext("Field"), class: "symbol-row-title"});
	var rulesTh3 = $("<th>", {"data-field": "name", text:  gettext("Name"), class: "symbol-row-title"});
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
		var field = $(this).val();
		
		ajaxPost("/gvsigonline/get_unique_values/"+ that.layer_id +"/"+field+"/", {}, function(content){
            
            if(content.values.length > 50){
	            var cnewdata = function(){
	            	that.createNewData(content.values);
	            };
	            
	            that.symbologyUtils.showModal(
	            	"unique-values-modal", 
	            	gettext("Muchos valores"), 
	            	gettext("Muchos valores descripcion"), 
	            	cnewdata,
	            	true);
            }else{
            	that.createNewData(content.values);
            }
        })
	});
};

UniqueValues.prototype.getID = function() {
	return this.legendId;
};

UniqueValues.prototype.getFieldName = function(filter) {
	if(filter == null){
		return null;
	}
	var fieldArray = filter.match(/(.+)==(.+)/);
	if(fieldArray == null || fieldArray.length == 0){
		return fieldArray;
	}
	var field = fieldArray[1].trim();
	return field;
}

UniqueValues.prototype.getFieldValue = function(filter) {
	if(filter == null){
		return "";
	}
	var fieldArray = filter.match(/<Literal>([^<]+)<\/Literal>/);
	if(fieldArray == null || fieldArray.length == 0){
		var fieldArray2 = filter.match(/== "(.*)"/);
		if(fieldArray2 == null || fieldArray2.length == 0){
			return "";
		}
		var field = fieldArray2[1];
		return field;
	}
	var field = fieldArray[1];
	return field;
}

/**
 * Load Data
 */
UniqueValues.prototype.loadData = function(data) {
	if(data.length>0){
		var field = this.getFieldName(data[0].rule[0].fields.filter);
		if(field != null && field != "" && field.length > 0){
			$("#"+this.getID()+"-field-input-0").val(field);
		}
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
			var symbolField = $("<td>", {class: "symbol-row-title"});
			var fieldInput =  $("<input>", {id: "symbol-field", class: "legend-row validate", type: "text", value: this.getFieldValue(data[i].rule[0].fields.filter), "disabled": "disabled"});
			symbolField.append(fieldInput);
			var symbolName = $("<td>", {class: "symbol-row-title  pre-delete-buttons"});
			var nameInput =  $("<input>", {id: "symbol-name", class: "legend-row symbol-name validate", type: "text", value: this.symbologyUtils.decodeXML(data[i].symbols[0].fields.name), rule: i, symbol: j});
			symbolName.append(nameInput);
			
			var symbolDelete = $("<td>", {class: "symbol-row-title delete-buttons"});
			var deleteButton = $("<button>", {type: "button", 
				class: "button-delete-vu btn-floating btn-flat waves-effect waves-light right red",
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
	
	$(".button-delete-vu").click(function(){
		var rule = $(this).attr("rule");
		var symbol = $(this).attr("symbol");
		that.currentData.splice(rule, 1);
		that.loadData(that.currentData);
	});
	
	$(".symbol-name").unbind("change").change(function(){
		var rule = $(this).attr("rule");
		var symbol = $(this).attr("symbol");
		that.currentData[rule].symbols[symbol].fields.name = that.symbologyUtils.encodeXML($(this).val());
	});
	this.currentData = data;
	this.previewMap.reloadLayer(this.currentData);
};

UniqueValues.prototype.loadPreviewMap = function(workspace, layer, username, password) {	
	this.previewMap.loadMap(workspace, layer, username, password);
};

UniqueValues.prototype.createNewData = function(data) {
	var symbologyUtils = new SymbologyUtils();
	
	this.currentData = [];
	var colors = symbologyUtils.createColorRange("Random", data.length);
	
	for(var i=0;i<data.length; i++){
		/* Creamos la regla con un símbolo estándar */
		var fieldFilter = "";
		
		var fName = data[i];
		if(data[i] == null){
			fName = "";
		}
		var fieldName = fName;
		
		if($("#"+this.getID()+"-field-input-0").val() != null && 
			$("#"+this.getID()+"-field-input-0").val() != ""){
				fieldFilter = $("#"+this.getID()+"-field-input-0").val() + " == \"" + this.symbologyUtils.encodeXML(fName) + "\"";
		}else{
			fieldFilter = "";
		}
		
		var rl = symbologyUtils.createEmptyRule(this.style, fieldName, fieldFilter);
		var sm = this.symbologyUtils.createEmptySymbol(fieldName, this.type, colors[i]);
		var rls = {"rule": [rl], "symbols": [sm]};
		this.currentData.push(rls);
	}

	this.loadData(this.currentData);
};

UniqueValues.prototype.loadPreviews = function(previews) {
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
UniqueValues.prototype.getData = function() {
	return this.currentData;
};
