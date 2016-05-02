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
 
 
var UniqueSymbol = function(workspace, layer, style, type, buttoncomp, panelcomp, fields) {	
	this.workspace = workspace;
	this.layer = layer;
	//this.layer_id = layer[0]["layer"][0].pk;
	this.style = style;
	this.type = type;
	this.legendId = "SU";
	this.currentData = null;
	this.fields = fields;
	
	this.symbologyUtils = new SymbologyUtils();
	this.formHelper = new SymbologyFormComponents();
	this.initializeButtonComponent(buttoncomp);
	
	this.previewMap = new  SymbologyPreviewMap(this.legendId, this.style);
	
	if(panelcomp != null){
		this.initializePanelComponent(panelcomp);
		this.createNewData();
	}
};

UniqueSymbol.prototype.initializeButtonComponent = function(component) {	
	var ui = '';
	ui += '<li class="item">';
	ui += 		'<div class="product-icon text-primary">';
	ui += 			'<i class="fa fa-map-marker"></i>';
	ui += 		'</div>';
	ui += 		'<div class="product-info">';
	ui += 			'<a id="' + this.getID() + '" href="#!" id="option1" class="product-title legend-button option-selection">';
	ui += 				gettext("Unique Symbol");							
	ui += 			'</a>';
	ui += 			'<span class="product-description">' + gettext("Unique Symbol description") + '</span>';
	ui += 		'</div>';
	ui += '</li>';
	$("#"+component).append(ui);
};

/**
 * Initialize component method
 */
UniqueSymbol.prototype.initializePanelComponent = function(component) {
	var panel = $("<div>", {id: this.getID() + "-panel", class:"step-2"});
	
	var preview = $("<div>", {class:"map-preview col-md-6", style:"float:left;"});
	var mapImage = this.previewMap.createMap();
	preview.append(mapImage);
	
	var mainPanel = $("<div>", {class:"col-md-6"});
	
	var titleDiv = $("<div>", {class:"legend-div-title"});
	var star = $("<i>", {class:"fa fa-star default-legend-element"});
	var title = $("<span>", {class:"legend-title", text: gettext("Unique Symbol")});
	titleDiv.append(title);
	titleDiv.append(star);
	mainPanel.append(titleDiv);

	var rulesTable = $("<table>", {style: "width: 100%;"});
	var rulesTHead = $("<thead>");
	var rulesTr = $("<tr>");
	var rulesTh1 = $("<th>", {class:"symbol-header", "data-field": "preview", text: gettext("Symbol")});
	var rulesTh2 = $("<th>", {"data-field": "name", text: gettext("Name")});
	var rulesTBody = $("<tbody>", {class: this.getID() + "-rules-ul"});
	
	var separator = $("<div>", {class: "clearBoth"});
	
	rulesTable.append(rulesTHead);
	rulesTable.append(rulesTBody);
	rulesTHead.append(rulesTr);
	rulesTr.append(rulesTh1);
	rulesTr.append(rulesTh2);
	mainPanel.append(rulesTable);
	
	panel.append(preview);
	panel.append(mainPanel);
	panel.append(separator);

	$("#"+component).append(panel);
};

UniqueSymbol.prototype.getID = function() {
	return this.legendId;
};

/**
 * Load Data
 */
UniqueSymbol.prototype.loadData = function(data) {
	if(data && data.length > 0){
		$("."+this.getID() + "-rules-ul").empty();
	}
	this.currentData = data;
	var previews = []
	
	for(var i=0;i<data.length; i++){
		for(var j=0; j<data[i].symbols.length; j++){
			var ruleTr = $("<tr>", {id:"symbol-"+data[i].symbols[j].pk});
			var symbolPreviewButton = $("<td>", {
				class: "load-symbol-form-button",
				rule: i,
				symbol: j});
			var symbolPreview = $("<div>", {
				id:"symbol-" + data[i].symbols[j].pk + "-preview", 
				class: ""});
			var symbolName = $("<td>", {class: "symbol-row-title"});
			var nameInput =  $("<input>", {id: "symbol-name", class: "legend-row validate", type: "text", value: this.symbologyUtils.decodeXML(data[i].symbols[j].fields.name), rule: i, symbol: j});
			symbolName.append(nameInput);
			
			symbolPreviewButton.append(symbolPreview);
			ruleTr.append(symbolPreviewButton);
			ruleTr.append(symbolName);
			
			previews.push({'symbol': data[i].symbols[j], 'container': symbolPreview });
			$("."+this.getID() + "-rules-ul").append(ruleTr);
			
			var that = this;
			nameInput.change(function(){
				var rule = $(this).attr("rule");
				var symbol = $(this).attr("symbol");
				
				that.currentData[parseInt(rule)].symbols[parseInt(symbol)].fields.name = that.symbologyUtils.encodeXML($(this).val());
			});
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
	this.previewMap.reloadLayer(this.currentData);
};

UniqueSymbol.prototype.loadPreviewMap = function(workspace, layer, username, password) {	
	this.previewMap.loadMap(workspace, layer, username, password);
};


UniqueSymbol.prototype.createNewData = function() {
	var previews = []
	var ruleTr = $("<tr>", {id:"symbol-new"});
	var symbolPreviewButton = $("<td>", {
		class: "load-symbol-form-button",
		rule: -1,
		symbol: -1});
	var symbolPreview = $("<div>", {
		id:"symbol-" + "new" + "-preview", 
		class: ""});
	var symbolName = $("<td>", {class: "symbol-row-title"});
	var nameInput =  $("<input>", {id: "symbol-name", class: "legend-row validate", type: "text", value: "default-symbol"});
	symbolName.append(nameInput);
	
	symbolPreviewButton.append(symbolPreview);
	ruleTr.append(symbolPreviewButton);
	ruleTr.append(symbolName);
	
	sym = null;
	previews.push({'symbol': sym, 'container': symbolPreview });
	$("."+this.getID() + "-rules-ul").append(ruleTr);
	
	this.loadPreviews(previews);
	var that = this;
	$(".load-symbol-form-button").unbind("click").click(function(){
		var rule = $(this).attr("rule");
		var symbol = $(this).attr("symbol");
		that.symbologyUtils.createSymbolForm(that, that.getID(), that.type, that.currentData, rule, symbol, $(this).parent(), that.style);
	});
};

UniqueSymbol.prototype.loadPreviews = function(previews) {
	for(var i=0; i<previews.length; i++){
		var symbologyPreview = new SymbologyPreview(null);
		if(previews[i].symbol != null 
			&& previews[i].symbol.fields != null){
				var sldjson = $.xml2json("<StoredSLD>" +
					previews[i].symbol.fields.sld_code + "</StoredSLD>");
			
				var symbolPreview = symbologyPreview.renderPreview(
					sldjson[this.type], 
					this.type, 
					"symbol-" + previews[i].symbol.pk + "-preview");
		}else{
			var symbolPreview = symbologyPreview.renderPreview(
				null, 
				this.type, 
				"symbol-" + "new" + "-preview");
		}
		
		if(symbolPreview != null){
			previews[i].container.append(symbolPreview);
		}
	} 
};

/**
 * Get Data
 */
UniqueSymbol.prototype.getData = function() {
	return this.currentData;
};
