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
 
var Charts = function(workspace, layer, style, type, buttoncomp, panelcomp, fields, sldFilterValues) {	
	this.workspace = workspace;
	this.layer = layer;
	this.layer_id = layer[0]["layer"][0].pk;
	this.style = style;
	this.type = type;
	this.legendId = "CH";
	this.currentData = null;
	this.isFirstTime = true;
	this.fields = fields;
	this.sldFilterValues = sldFilterValues;
	this.ancho = 150;
	this.alto = 100;
	
	this.symbologyUtils = new SymbologyUtils();
	this.formHelper = new SymbologyFormComponents();
	this.initializeButtonComponent(buttoncomp);
	this.elements = [];
	
	this.previewMap = new  SymbologyPreviewMap(this.legendId, this.style);
	
	if(panelcomp != null){
		this.initializePanelComponent(panelcomp, fields);
	}
};

Charts.prototype.initializeButtonComponent = function(component) {
	var container = $("<li>", {class:"collection-item avatar"});
	
	var icon = $("<i>", { class:"material-icons circle fa fa-pie-chart"});
	var title = $("<span>", {text: gettext("Charts"), class:"title"});
    var desc = $("<p>", {html: gettext("Charts descripcion")});

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
Charts.prototype.initializePanelComponent = function(component, fields) {
	var panel = $("<div>", {id: this.getID() + "-panel", class:"step-2"});
	var preview = $("<div>", {class:"map-preview col-md-6", style:"float:left;"});
	var mapImage = this.previewMap.createMap();
	preview.append(mapImage);
	
	var mainPanel = $("<div>", {class:"col-md-6"});
	var maintitle = $("<div>", {class:"legend-main-title", text:"Panel de símbolo único"});
	
	var titleDiv = $("<div>", {class:"legend-div-title"});
	var star = $("<i>", {class:"fa fa-star default-legend-element"});
	var title = $("<span>", {class:"legend-title", text: gettext("Charts")});
	titleDiv.append(title);
	titleDiv.append(star);
	mainPanel.append(titleDiv);
	
	var chart_options = '{'+
		'"p": "'+ gettext("2D Pie Chart") +'",'+ 
		'"p3": "'+ gettext("3D Pie Chart") +'",'+ 
		
		'"bvg": "'+ gettext("2D vertical Bars") +'",'+ 
		'"bhg": "'+ gettext("2D horizontal Bars") +'"'+ 
		//'"bvs": "'+ gettext("2D vertical Bars stacks") +'"'+ 
		'}';
	
	var fieldChooser = this.formHelper.createSelectInput(
		gettext("Tipo-chart"), 
		this.getID()+"-field-input", 
		"p",
		chart_options, 
		gettext("Selecciona tipo de grafica"), 
		false, 
		false, 0);
	
	
	var intervalsInput = this.formHelper.createFormTextInput(
		gettext("Titulo-chart"), 
		"charts-title", 
		"",  
		"",  
		false, 
		true);
	
	//mainPanel.append(intervalsInput);
	mainPanel.append(fieldChooser);
	
	
	
	var buttonsTableDiv = $("<div>", {class: "row right"});
	var addButton = $("<button>", {type: "button", 
		id: "button-add-chart", 
		class: "btn-floating btn-flat waves-effect waves-light light-green",
		"data-toggle": "tooltip",
		"data-placement": "bottom"});
	var addIconButton = $("<i>", {class: "fa fa-plus"});
	addButton.append(addIconButton);
	buttonsTableDiv.append(addButton);
	mainPanel.append(buttonsTableDiv);
	
	
	var rulesTableDiv = $("<div>", {class: "legend-mainpanel hidden"});
	var rulesTable = $("<table>", {class: "legend-panel responsive-table highlight bordered"});
	var rulesTHead = $("<thead>");
	var rulesTr = $("<tr>");
	var rulesTh1 = $("<th>", {"data-field": "color", text: gettext("Color"), class:"symbol-row-chart"});
	var rulesTh2 = $("<th>", {"data-field": "label", text: gettext("Label"), class: "symbol-row-chart"});
	var rulesTh3 = $("<th>", {"data-field": "data", text: gettext("data"), class: "symbol-row-chart"});
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
	//rulesTable.append(rules);
	rulesTableDiv.append(rulesTable);
	panel.append(rulesTableDiv);

	$("#"+component).append(panel);
	
	var that = this;
	$("#button-add-chart").unbind("click").click(function(){
		that.createNewData();
	});
	
};


Charts.prototype.getID = function() {
	return this.legendId;
};

Charts.prototype.getChartWidth = function() {
	return this.ancho;
};

Charts.prototype.getChartHeight = function() {
	return this.alto;
};


Charts.prototype.getChartData = function(sldCode) {
	var cMaps = [];
	
	var regex = new RegExp('http:\/\/chart\\?([^\\<]*)', "g");
	if(sldCode != null && sldCode.match(regex)){
		var match = [];
		while (result = regex.exec(sldCode)){
			if(result.length>0){
				match.push(result[1]);
			}
		}
		var chartType = "p";
		var chartData = [];
		var chartColors = [];
		var chartLabels = [];
		var chartOther = "";
		
		for(var i=0; i<match.length; i++){
			var props = match[i].split("&amp;");
			for(var j=0; j<props.length; j++){
				if(props[j].startsWith("cht=")){
					chartType = props[j].replace("cht=", "");
				}
				
				if(props[j].startsWith("chd=t:")){
					aux = props[j].replace("chd=t:", "");
					if(chartType =="bvg" || chartType =="bhg" || chartType =="bvs"){
						auxdata = aux.split("|");
					}else{
						auxdata = aux.split(",");
					}
					for(var k=0; k<auxdata.length; k++){
						auxdata[k] = auxdata[k].replace("${","");
						auxdata[k] = auxdata[k].replace("}","");
					}
					chartData = auxdata;
				}
				
				if(props[j].startsWith("chco=")){
					aux = props[j].replace("chco=", "");
					auxcolors = aux.split(",");
					for(var k=0; k<auxcolors.length; k++){
						auxcolors[k] = "#" + auxcolors[k];
					}
					chartColors = auxcolors;
				}
				
				if(props[j].startsWith("chl=")){
					aux = props[j].replace("chl=", "");
					auxlabels = aux.split("|");
					chartLabels = auxlabels;
				}
				
				if(props[j].startsWith("chs=")){
					aux = props[j].replace("chs=", "");
					auxsize = aux.split("x");
					if(auxsize.length > 1){
						this.ancho = auxsize[0];
						this.alto = auxsize[1];
					}
				}
				
				if(props[j].startsWith("chxl==0:|")){
					aux = props[j].replace("chxl==0:|", "");
					auxlabelsx = aux.split("|");
					chartLabels = auxlabelsx;
				}
				
				if(props[j].startsWith("chxl==1:|")){
					aux = props[j].replace("chxl==1:|", "");
					auxlabelsx = aux.split("|");
					chartLabels = auxlabelsx;
					chartLabels = chartLabels.reverse();
				}
			}
		}
		
		for(var ix=0; ix<chartData.length; ix++){
			var cmap = {};
			
			cmap["filter"] = chartData[ix];
			if(chartLabels.length>ix){
				cmap["label"] = chartLabels[ix];
			}else{
				cmap["label"] = ""+ix;
			}
			if(chartColors.length>ix){
				cmap["color"] = chartColors[ix];
			}else{
				var symbologyUtils = new SymbologyUtils();
				cmap["color"] = symbologyUtils.createColorRange("Random", 1);
			}
			cMaps.push(cmap);
		
		}
		
		$("#"+this.getID()+"-field-input-0 option[value="+chartType+"]").attr("selected", true);
    	$('select').material_select();
		$("#chart-ancho").val(this.ancho);
		$("#chart-alto").val(this.alto);
	}
	
	return cMaps;
}


/**
 * Load Data
 */
 
Charts.prototype.updateChartTable = function() {
	$("."+this.getID() + "-rules-ul").empty();
	
	for(var k=0; k<this.elements.length; k++){
		var ruleTr = $("<tr>", {id:"symbol-"+k});
		var symbolColor = $("<td>", {class: "symbol-row-colortable"});
		var colorInput =  $("<input>", {id: "chart-color-"+k, class: "chart-color waves-effect waves-light btn color-chooser legend-row validate", type: "color", value:this.elements[k].color, style:"display:block", colorMap: k});
		symbolColor.append(colorInput);
		
		var symbolField = $("<td>", {class: "symbol-row-colortable"});
		var fieldInput =  $("<input>", {id: "chart-label-"+k, class: "chart-label legend-row validate", type: "text", value: this.symbologyUtils.decodeXML(this.elements[k].label), colorMap: k});
		symbolField.append(fieldInput);
		
		var symbolName = $("<td>", {class: "symbol-row-colortable filter-field pre-delete-buttons", colorMap: k});
		var filterText = this.elements[k].filter;
		if(filterText == null || filterText == ""){
			filterText = gettext("Editar filtro");
		}
		var fieldInput =  $("<span>", {
				id: "chart-filter-"+k,
				class: "chart-filter legend-row validate filter-text", 
				text: filterText, 
				colorMap: k});
		symbolName.append(fieldInput);
		
		var symbolDelete = $("<td>", {class: "symbol-row-title delete-buttons"});
		var deleteButton = $("<button>", {type: "button", 
			class: "button-delete-chart btn-floating btn-flat waves-effect waves-light right red",
			"data-toggle": "tooltip",
			"data-placement": "bottom",
			colorMap: k});
		var deleteIconButton = $("<i>", {class: "fa fa-minus"});
		deleteButton.append(deleteIconButton);
		symbolDelete.append(deleteButton);
		
		ruleTr.append(symbolColor);
		ruleTr.append(symbolField);
		ruleTr.append(symbolName);
		ruleTr.append(symbolDelete);
		
		$("."+this.getID() + "-rules-ul").append(ruleTr);
	}
	
	
	$(".chart-filter").unbind("change").change(function(){
		var colorMap = $(this).attr("colorMap");
		that.elements[colorMap].filter = $(this).val();
	});
	
	$(".chart-label").unbind("change").change(function(){
		var colorMap = $(this).attr("colorMap");
		that.elements[colorMap].label = that.symbologyUtils.encodeXML($(this).val());
	});
	
	$(".chart-color").unbind("change").change(function(e){
		var colorMap = $(this).attr("colorMap");
		that.elements[colorMap].color = $(this).val();
	});
	
	var that = this;
	$(".filter-field").click(function(){
		var colorMap = $(this).attr("colorMap");
		var symbologyFilter = new SymbologyFilter(that.fields, that, colorMap, that.sldFilterValues);
		symbologyFilter.show(that.elements[colorMap].filter);	
		
	});
	
	$(".button-delete-chart").unbind("click").click(function(){
		var colorMap = $(this).attr("colorMap");
		that.elements.splice(parseInt(colorMap), 1);
		that.updateChartTable();
	});
	
	if(this.elements.length > 0){
		$(".legend-mainpanel").show();
	}
	
	if(this.elements.length == 0){
		$(".legend-mainpanel").hide();
	}
}

Charts.prototype.loadData = function(data) {
	for(var i=0; i<data.length; i++){
		for(var j=0; j<data[i].symbols.length; j++){
				this.elements = this.getChartData(data[i].symbols[j].fields.sld_code);
		}
	}
	
	if(this.elements.length > 0){
		$(".legend-mainpanel").show();
	}
	
	this.updateChartTable();
	
	this.currentData = data;	
	
	var that = this;
	jQuery(window).load(function () {
	    that.updateChartTable();
	});
	//this.previewMap.reloadLayer(this.currentData);
};

Charts.prototype.loadPreviewMap = function(workspace, layer, username, password) {	
	this.previewMap.loadMap(workspace, layer, username, password);
};

Charts.prototype.updateFilterField = function(rule, filterText, minscale, maxscale) {
	this.elements[rule].filter = filterText;
	if(filterText == null || filterText == ""){
		filterText = gettext("Editar filtro");
	}
	$("#chart-filter-"+rule).text(filterText);
	
	//this.previewMap.reloadLayer(this.currentData);
}

Charts.prototype.createNewData = function() {
	var symbologyUtils = new SymbologyUtils();
	var colors = symbologyUtils.createColorRange("Random", 1);
	
	var newData = {
		color: colors[0],
		label: "",
		filter: "",
	}
	
	this.elements.push(newData);	
	this.updateChartTable();
	//this.loadData(this.currentData);
};


/**
 * Get Data
 */
Charts.prototype.getData = function() {
	
	if(this.currentData.length == 0){
		var symbologyUtils = new SymbologyUtils();
		var rl = symbologyUtils.createEmptyRule(this.style, "chart-rule", "", 0);
		var sm = this.symbologyUtils.createEmptySymbol("chart-symbol", "PointSymbolizer", "#FFFFFF");
		var rls = {"rule": [rl], "symbols": [sm]};
		this.currentData.push(rls);
	}
	
	if(this.currentData.length>0){
		var chart_type = $("#"+this.getID()+"-field-input-0").val();
		var base = "http://chart?cht="+chart_type;
		
		
		//  BARS CHART URL EXAMPLE:
		//  http://chart?cht=bvg&amp;chxt=x,y&amp;chd=t:${gmrotation}|${30}&amp;chco=FF0000,0000FF&amp;chxl==0:|M|F&amp;chs=200x100&amp;chf=bg,s,FFFFFF00&amp;chtt=titulo
		
		var data = "&amp;chd=t:";
		var labels = "&amp;chl=";
		var colors = "&amp;chco=";
		var subtype = "";
		var size = "&amp;chs="+this.ancho+"x"+this.alto;
		var other = "&amp;chf=bg,s,FFFFFF00";
		
		if(chart_type =="bvg" || chart_type =="bhg" || chart_type =="bvs"){
			labels = "&amp;chxl==0:|";
			subtype = "&amp;chxt=x,y";
		}
		
		if(chart_type =="bhg"){
			labels = "&amp;chxl==1:|";
		}
		
		var auxLabels = [];
		for(var i=0; i<this.elements.length; i++){
			var dataseparator = ",";
			var colorseparator = ",";
			var labelseparator = "|";
			
			if(chart_type =="bvg" || chart_type =="bhg" || chart_type =="bvs"){
				dataseparator = "|";
			}
		
			if(i==0){
				dataseparator = "";
				colorseparator = "";
				labelseparator = "";
			}
			
			data = data + dataseparator + "${"+this.elements[i].filter+"}";
			colors = colors + colorseparator +this.elements[i].color.replace("#","");
			var labelidx = i;
			if(chart_type =="bhg"){
				labelidx = this.elements.length-1-i;
			}
			labels = labels + labelseparator +this.elements[labelidx].label;
		}
		
		var url = base + subtype + data + colors + labels + size + other;  

		var new_sld_code = "<PointSymbolizer>"+
				            "<Size>"+"100"+"</Size>"+
				            "<Graphic>"+
				            	 "<ExternalGraphic>"+
					            		url+
				            	"</ExternalGraphic>"+
				            "</Graphic>"+
		         			"</PointSymbolizer>"
		
		this.currentData[0]["symbols"][0]["fields"]["sld_code"] = new_sld_code;
	}

	return this.currentData;
};

Charts.prototype.updateSize = function(ancho, alto){
	this.ancho = parseInt(ancho);
	this.alto = parseInt(alto);
}
