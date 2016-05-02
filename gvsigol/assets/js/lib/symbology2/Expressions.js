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
 
var Expressions = function(workspace, layer, style, type, buttoncomp, panelcomp, fields, sldFilterValues) {	
	this.workspace = workspace;
	this.layer = layer;
	this.layer_id = layer[0]["layer"][0].pk;
	this.style = style;
	this.type = type;
	this.legendId = "EX";
	this.currentData = null;
	this.isFirstTime = true;
	this.fields = fields;
	this.sldFilterValues = sldFilterValues;
	
	this.symbologyUtils = new SymbologyUtils();
	this.formHelper = new SymbologyFormComponents();
	this.initializeButtonComponent(buttoncomp);
	
	this.previewMap = new  SymbologyPreviewMap(this.legendId, this.style);
	
	if(panelcomp != null){
		this.initializePanelComponent(panelcomp, fields);
	}
};

Expressions.prototype.initializeButtonComponent = function(component) {
	var ui = '';
	ui += '<li class="item">';
	ui += 		'<div class="product-icon text-primary">';
	ui += 			'<i class="fa fa-terminal"></i>';
	ui += 		'</div>';
	ui += 		'<div class="product-info">';
	ui += 			'<a id="' + this.getID() + '" href="#!" id="option1" class="product-title legend-button option-selection">';
	ui += 				gettext("Expressions");							
	ui += 			'</a>';
	ui += 			'<span class="product-description">' + gettext("Expressions description") + '</span>';
	ui += 		'</div>';
	ui += '</li>';
	$("#"+component).append(ui);
};

/**
 * Initialize component method
 */
Expressions.prototype.initializePanelComponent = function(component, fields) {
	var panel = $("<div>", {id: this.getID() + "-panel", class:"step-2"});
	var preview = $("<div>", {class:"map-preview col s6", style:"float:left;"});
	var mapImage = this.previewMap.createMap();
	preview.append(mapImage);
	
	var mainPanel = $("<div>", {class:"legend-main-panel"});
	var maintitle = $("<div>", {class:"legend-main-title", text:"Panel de símbolo único"});
	
	var titleDiv = $("<div>", {class:"legend-div-title"});
	var star = $("<i>", {class:"fa fa-star default-legend-element"});
	var title = $("<span>", {class:"legend-title", text: gettext("Expressions")});
	titleDiv.append(title);
	titleDiv.append(star);
	mainPanel.append(titleDiv);
	
	var buttonsTableDiv = $("<div>", {class: "row right"});
	var addButton = $("<button>", {type: "button", 
		id: "button-add-expression", 
		class: "btn-floating btn-flat waves-effect waves-light light-green",
		"data-toggle": "tooltip",
		"data-placement": "bottom"});
	var addIconButton = $("<i>", {class: "fa fa-plus"});
	addButton.append(addIconButton);
	buttonsTableDiv.append(addButton);
	
	var rulesTableDiv = $("<div>", {class: "legend-mainpanel"});
	var rulesTable = $("<table>", {class: "legend-panel responsive-table highlight bordered"});
	var rulesTHead = $("<thead>");
	var rulesTr = $("<tr>");
	var rulesTh1 = $("<th>", {class:"symbol-header", "data-field": "preview", text: gettext("Symbol")});
	var rulesTh2 = $("<th>", {"data-field": "Filter", text: gettext("Filter"), class: "symbol-row-title"});
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
	rulesTableDiv.append(rulesTable);
	panel.append(buttonsTableDiv);
	panel.append(rulesTableDiv);

	$("#"+component).append(panel);
	
	var that = this;
	$("#button-add-expression").unbind("click").click(function(){
		that.createNewData();
	});
		
};


Expressions.prototype.getID = function() {
	return this.legendId;
};


/**
 * Load Data
 */
Expressions.prototype.loadData = function(data) {
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
			var symbolField = $("<td>", {class: "symbol-row-title filter-field ", 
				rule: i,
				symbol: j});
			var filterText = data[i].rule[0].fields.filter;
			if(filterText == null || filterText == ""){
				filterText = gettext("Editar filtro");
			}
			var fieldInput =  $("<span>", {
				class: "legend-row validate filter-text rule-"+i, 
				text: filterText, 
				rule: i,
				symbol: j});
			symbolField.append(fieldInput);
			var symbolName = $("<td>", {class: "symbol-row-title pre-delete-buttons"});
			var nameInput =  $("<input>", {id: "symbol-name", class: "legend-row symbol-name validate", type: "text", value: this.symbologyUtils.decodeXML(data[i].symbols[0].fields.name), rule: i, symbol: j});
			symbolName.append(nameInput);
			
			
			var symbolDelete = $("<td>", {class: "symbol-row-title delete-buttons"});
			var deleteButton = $("<button>", {type: "button", 
				class: "button-delete-expression btn-floating btn-flat waves-effect waves-light right red",
				"data-toggle": "tooltip",
				"data-placement": "bottom",
				rule: i,
				symbol: j});
			var deleteIconButton = $("<i>", {class: "fa fa-minus"});
			deleteButton.append(deleteIconButton);
			symbolDelete.append(deleteButton);
			
			//var separator = $("<div>", {class: "clearBoth"});
			
			symbolPreviewButton.append(symbolPreview);
			ruleTr.append(symbolPreviewButton);
			ruleTr.append(symbolField);
			ruleTr.append(symbolName);
			ruleTr.append(symbolDelete);
			
			previews.push({'symbol': data[i].symbols[j], 'container': symbolPreview });
			$("."+this.getID() + "-rules-ul").append(ruleTr);
		}
		
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
	
	$(".symbol-name").unbind("change").change(function(){
			var rule = $(this).attr("rule");
			var symbol = $(this).attr("symbol");
			that.currentData[rule].symbols[symbol].fields.name = $(this).val();
			that.currentData[rule].rule[0].fields.name = that.symbologyUtils.encodeXML($(this).val());
		});
	
	$(".filter-field").click(function(){
		var rule = $(this).attr("rule");
		var symbol = $(this).attr("symbol");
		
		var symbologyFilter = new SymbologyFilter(that.fields, that, rule, that.sldFilterValues);
		symbologyFilter.show();	
		
	});
	
	$(".button-delete-expression").click(function(){
		var rule = $(this).attr("rule");
		var symbol = $(this).attr("symbol");
		that.currentData.splice(rule, 1);
		that.loadData(that.currentData);
	});
	
	this.currentData = data;
	this.previewMap.reloadLayer(this.currentData);
};

Expressions.prototype.loadPreviewMap = function(workspace, layer, username, password) {	
	this.previewMap.loadMap(workspace, layer, username, password);
};

Expressions.prototype.updateFilterField = function(rule, filterText, minscale, maxscale) {
	this.currentData[rule].rule[0].fields.filter = filterText;
	this.currentData[rule].rule[0].fields.minscale = minscale;
	this.currentData[rule].rule[0].fields.maxscale = maxscale;
	if(filterText == null || filterText == ""){
		filterText = gettext("Editar filtro");
	}
	$(".filter-text.rule-"+rule).text(filterText);
	
	this.previewMap.reloadLayer(this.currentData);
}

Expressions.prototype.createNewData = function() {
	var symbologyUtils = new SymbologyUtils();
	
	// Creamos la regla con un símbolo estándar 
	var fieldName = gettext("new expression");
	var fieldFilter = "";
	
	var rl = symbologyUtils.createEmptyRule(this.style, fieldName, fieldFilter, 0);
	var color = symbologyUtils.createColorRange("Random", 1);
	var sm = this.symbologyUtils.createEmptySymbol(fieldName, this.type, color[0]);
	var rls = {"rule": [rl], "symbols": [sm]};
	this.currentData.push(rls);

	this.loadData(this.currentData);
	
};



Expressions.prototype.loadPreviews = function(previews) {
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
Expressions.prototype.getData = function() {
	var that = this;
	$(".symbol-name").each(function(){
		var rule = $(this).attr("rule");
		var symbol = $(this).attr("symbol");
		that.currentData[rule].symbols[symbol].fields.name = that.symbologyUtils.encodeXML($(this).val());
		that.currentData[rule].rule[0].fields.name = that.symbologyUtils.encodeXML($(this).val());
	});
	return this.currentData;
};
