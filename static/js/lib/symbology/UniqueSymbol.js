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
 * @author: Javier Rodrigo <jrodrigo@scolab.es>
 */
 
 
var UniqueSymbol = function(featureType, layerName, symbologyUtils, rule_opts, previewPointUrl, previewLineUrl, previewPolygonUrl) {
	this.selected = null;
	this.featureType = featureType;
	this.layerName = layerName;
	this.previewPointUrl = previewPointUrl;
	this.previewLineUrl = previewLineUrl;
	this.previewPolygonUrl = previewPolygonUrl;
	this.symbologyUtils = symbologyUtils;
	this.rule = new Rule(0, featureType, rule_opts);
	if (rule_opts != null) {
		if (rule_opts.symbolizers != "") {
			this.loadSymbols(rule_opts.symbolizers);
		}
	}	
};

UniqueSymbol.prototype.getRule = function() {
	return this.rule;
};

UniqueSymbol.prototype.appendSymbolizer = function() {
	var self = this;
	
	var symbolizer = null;
	if (this.featureType == 'PointSymbolizer') {
		symbolizer = new MarkSymbolizer(this.rule, null, this.previewPointUrl, this.symbologyUtils);
		
	} else if (this.featureType == 'LineSymbolizer') {
		symbolizer = new LineSymbolizer(this.rule, null, this.previewLineUrl, this.symbologyUtils);
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		symbolizer = new PolygonSymbolizer(this.rule, null, this.previewPolygonUrl, this.symbologyUtils);
	}
	
	$('#table-symbolizers tbody').append(symbolizer.getTableUI());
	
	$("#table-symbolizers-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-symbolizers-body").on("sortupdate", function(event, ui){
		/*var rows = ui.item[0].parentNode.children;
		for(var i=0; i < rows.length; i++) {
			var symbol = self.rule.getSymbolizerById(rows[i].dataset.rowid);
			symbol.order = i;
		}*/		
	});
	
	$(".edit-symbolizer-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.rule.getSymbolizerById(this.dataset.symbolizerid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-symbolizer-link").one('click', function(e){	
		e.preventDefault();
		self.rule.removeSymbolizer(this.dataset.symbolizerid);
	});
	
	this.rule.appendSymbolizer(symbolizer);
	symbolizer.updatePreview();

	self.setSelected(symbolizer);
	this.updateForm();
};

UniqueSymbol.prototype.appendLabel = function() {
	var self = this;
	
	var label = new TextSymbolizer(this.rule, null, this.symbologyUtils);
	$('#table-symbolizers tbody').append(label.getTableUI());
	$('#table-symbolizers-body').sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	
	$(".edit-label-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.rule.getLabelById(this.dataset.labelid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-label-link").one('click', function(e){	
		e.preventDefault();
		self.rule.removeLabel(this.dataset.labelid);
	});
	
	this.rule.appendLabel(label);
	label.updatePreview();
	
	self.setSelected(label);
	this.updateForm();
	
	$('#append-label-button').css('display', 'none');
};

UniqueSymbol.prototype.setSelected = function(element) {
	this.selected = element;
};

UniqueSymbol.prototype.loadSymbols = function(symbolizers) {
	$("#table-symbolizers-body").empty();
	this.rule.removeAllSymbolizers();
	this.rule.removeAllLabels();
	for (var i=0; i<symbolizers.length; i++) {
		var symbolizer = JSON.parse(symbolizers[i].json);
		if (symbolizer[0].model == 'gvsigol_symbology.textsymbolizer') {
			this.loadTextSymbolizer(symbolizer[0].fields);
		} else if (symbolizer.type == 'gvsigol_symbology.externalgraphic') {
			this.loadExternalGraphicSymbolizer(symbolizer[0].fields);
		} else {
			this.loadSymbolizer(symbolizer);
		}		
	}
};

UniqueSymbol.prototype.loadSymbolizer = function(options) {
	var self = this;
	
	var symbolizer = null;
	if (this.featureType == 'PointSymbolizer') {
		var ext_opts = $.extend( options[0].fields, options[1].fields );
		symbolizer = new MarkSymbolizer(this.rule, ext_opts, this.previewPointUrl, this.symbologyUtils);
		
	} else if (this.featureType == 'LineSymbolizer') {
		symbolizer = new LineSymbolizer(this.rule, options, this.previewLineUrl, this.symbologyUtils);
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		symbolizer = new PolygonSymbolizer(this.rule, options, this.previewPolygonUrl, this.symbologyUtils);
	}
	
	$('#table-symbolizers tbody').append(symbolizer.getTableUI());
	
	$("#table-symbolizers-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-symbolizers-body").on("sortupdate", function(event, ui){
		/*var rows = ui.item[0].parentNode.children;
		for(var i=0; i < rows.length; i++) {
			var symbol = self.rule.getSymbolizerById(rows[i].dataset.rowid);
			symbol.order = i;
		}*/		
	});
	
	$(".edit-symbolizer-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.rule.getSymbolizerById(this.dataset.symbolizerid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-symbolizer-link").one('click', function(e){	
		e.preventDefault();
		self.rule.removeSymbolizer(this.dataset.symbolizerid);
	});
	
	this.rule.appendSymbolizer(symbolizer);
	symbolizer.updatePreview();

	self.setSelected(symbolizer);
	this.updateForm();
};

UniqueSymbol.prototype.loadTextSymbolizer = function(symbolizer_object) {
	var self = this;
	
	var label = new TextSymbolizer(this.rule.getNextLabelId(), this.symbologyUtils, this.rule, symbolizer_object);
	$('#table-symbolizers tbody').append(label.getTableUI());
	$("#table-symbolizers-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-symbolizers-body").on("sortupdate", function(event, ui){
		/*var rows = ui.item[0].parentNode.children;
		for(var i=0; i < rows.length; i++) {
			var symbol = self.rule.getSymbolizerById(rows[i].dataset.rowid);
			symbol.order = i;
		}*/		
	});
	
	$(".edit-label-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.rule.getLabelById(this.dataset.labelid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-label-link").one('click', function(e){	
		e.preventDefault();
		self.rule.removeLabel(this.dataset.labelid);
	});
	
	this.rule.appendLabel(label);
	label.updatePreview();

	self.setSelected(label);
	this.updateForm();
};

UniqueSymbol.prototype.loadExternalGraphicSymbolizer = function(symbolizer_object) {
	var self = this;
	
	var symbolizer = new ExternalGraphicSymbolizer(this.rule.getNextSymbolizerId(), symbolizer_object.name, symbolizer_object.format, symbolizer_object.size, symbolizer_object.online_resource);
	
	$('#table-symbolizers tbody').append(symbolizer.getTableUI());	
	$("#table-symbolizers-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-symbolizers-body").on("sortupdate", function(event, ui){});	
	$(".edit-eg-link").on('click', function(e){	
		e.preventDefault();
		messageBox.show('warning', gettext('Image symbols can only be edited from the library'));
	});
	$(".delete-symbolizer-link").one('click', function(e){	
		e.preventDefault();
		self.rule.removeSymbolizer(this.dataset.symbolizerid);
	});
	
	this.rule.appendSymbolizer(symbolizer);
};

UniqueSymbol.prototype.refreshMap = function() {
	this.symbologyUtils.updateMap(this.rule, this.layerName);
};

UniqueSymbol.prototype.libraryPreview = function(rid,json_symbolizers) {
	var symbolizers = new Array();
	var scount = 0;
	var previewUrl = null;
	for (var i=0; i<json_symbolizers.length; i++) {
		var options = JSON.parse(json_symbolizers[i].json);
		var symbolizer = null;
		if (symbolizer_object.type == 'Mark') {
			symbolizer = new MarkSymbolizer(this.rule, options, this.previewPointUrl, this.symbologyUtils);
			previewUrl = this.previewPointUrl;
			
		} else if (symbolizer_object.type == 'LineSymbolizer') {
			symbolizer = new LineSymbolizer(this.rule, options, this.previewLineUrl, this.symbologyUtils);
			previewUrl = this.previewLineUrl;
			
		} else if (symbolizer_object.type == 'PolygonSymbolizer') {
			symbolizer = new PolygonSymbolizer(this.rule, options, this.previewPolygonUrl, this.symbologyUtils);
			previewUrl = this.previewPolygonUrl;
			
		} else if (symbolizer_object.type == 'TextSymbolizer') {
			symbolizer = new TextSymbolizer(this.count, this, symbolizer_object);
			previewUrl = this.previewPolygonUrl;
			
		}
		symbolizers.push(symbolizer);
		scount++;
	}
	symbolizers.sort(function(a, b){
		return parseInt(b.order) - parseInt(a.order);
	});
	
	var sldBody = this.symbologyUtils.getSLDBody(symbolizers);
	var url = previewUrl + '&SLD_BODY=' + encodeURIComponent(sldBody);
	var ui = '<img id="rule-preview-img" src="' + url + '" class="rule-preview"></img>';
	$("#library-symbol-preview-div-" + rid).empty();
	$("#library-symbol-preview-div-" + rid).append(ui);
};

UniqueSymbol.prototype.updateForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	$('#tab-menu').append(this.selected.getTabMenu());
	if (this.selected.type == 'Mark') {
		$('#tab-content').append(this.selected.getGraphicTabUI());
		$('#tab-content').append(this.selected.getFillTabUI());
		$('#tab-content').append(this.selected.getStrokeTabUI());
		$('#tab-content').append(this.selected.getRotationTabUI());		
		$('.nav-tabs a[href="#graphic-tab"]').tab('show');
		this.selected.registerEvents();
		
	} else if (this.selected.type == 'ExternalGraphicSymbolizer') {
		this.selected.registerEvents();
		
	} else if (this.selected.type == 'LineSymbolizer') {
		$('#tab-content').append(this.selected.getStrokeTabUI());
		$('.nav-tabs a[href="#stroke-tab"]').tab('show');
		this.selected.registerEvents();
		
	} else if (this.selected.type == 'PolygonSymbolizer') {
		$('#tab-content').append(this.selected.getFillTabUI());
		$('#tab-content').append(this.selected.getStrokeTabUI());
		$('.nav-tabs a[href="#fill-tab"]').tab('show');
		this.selected.registerEvents();
		
	} else if (this.selected.type == 'TextSymbolizer') {
		$('#tab-content').append(this.selected.getFontTabUI());
		$('#tab-content').append(this.selected.getHaloTabUI());
		$('.nav-tabs a[href="#label-font-tab"]').tab('show');
		this.selected.registerEvents();
	}
};

UniqueSymbol.prototype.save = function(layerId) {
	
	var symbolizers = new Array();
	for (var i=0; i < this.rule.getSymbolizers().length; i++) {
		var symbolizer = {
			type: this.rule.getSymbolizers()[i].type,
			json: this.rule.getSymbolizers()[i].toJSON(),
			order: this.rule.getSymbolizers()[i].order
		};
		symbolizers.push(symbolizer);
	}
	
	for (var i=0; i < this.rule.getLabels().length; i++) {
		var label = {
			type: this.rule.getLabels()[i].type,
			json: this.rule.getLabels()[i].toJSON(),
			order: this.rule.getLabels()[i].order
		};
		symbolizers.push(label);
	}
	
	symbolizers.sort(function(a, b){
		return parseInt(b.order) - parseInt(a.order);
	});
	
	var style = {
		name: $('#style-name').val(),
		title: $('#style-title').val(),
		is_default: $('#style-is-default').is(":checked"),
		rule: this.rule,
		symbolizers: symbolizers
	}
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/unique_symbol_add/" + layerId + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			style_data: JSON.stringify(style)
		},
		success: function(response){
			if (response.success) {
				location.href = "/gvsigonline/symbology/style_layer_list/";
			} else {
				alert('Error');
			}
			
		},
	    error: function(){}
	});
};

UniqueSymbol.prototype.update = function(layerId, styleId) {
	
	var symbolizers = new Array();
	for (var i=0; i < this.rule.getSymbolizers().length; i++) {
		var symbolizer = {
			type: this.rule.getSymbolizers()[i].type,
			json: this.rule.getSymbolizers()[i].toJSON(),
			order: this.rule.getSymbolizers()[i].order
		};
		symbolizers.push(symbolizer);
	}
	
	for (var i=0; i < this.rule.getLabels().length; i++) {
		var label = {
			type: this.rule.getLabels()[i].type,
			json: this.rule.getLabels()[i].toJSON(),
			order: this.rule.getLabels()[i].order
		};
		symbolizers.push(label);
	}
	
	var style = {
		name: $('#style-name').val(),
		title: $('#style-title').val(),
		is_default: $('#style-is-default').is(":checked"),
		rule: this.rule,
		symbolizers: symbolizers
	}
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/unique_symbol_update/" + layerId + "/" + styleId + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			style_data: JSON.stringify(style)
		},
		success: function(response){
			if (response.success) {
				location.href = "/gvsigonline/symbology/style_layer_list/";
			} else {
				alert('Error');
			}
			
		},
	    error: function(){}
	});
};