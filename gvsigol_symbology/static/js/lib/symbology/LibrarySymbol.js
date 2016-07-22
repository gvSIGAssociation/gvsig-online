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
 
 
var LibrarySymbol = function(previewPointUrl, previewLineUrl, previewPolygonUrl, symbologyUtils) {
	this.count = 0;
	this.selected = null;
	this.featureType = null;
	this.previewPointUrl = previewPointUrl;
	this.previewLineUrl = previewLineUrl;
	this.previewPolygonUrl = previewPolygonUrl;
	this.symbologyUtils = symbologyUtils;
	this.symbolizers = new Array();
	this.rules = new Array();
};

LibrarySymbol.prototype.getSymbolizers = function() {
	return this.symbolizers;
};

LibrarySymbol.prototype.appendRule = function(rule) {
	this.rules.push(rule);
};

LibrarySymbol.prototype.setFeatureType = function(featureType) {
	this.featureType = featureType;
};

LibrarySymbol.prototype.loadSymbolizers = function(r, json_symbolizers) {
	var self = this;
	var previewUrl = null;
	for (var i=0; i<json_symbolizers.length; i++) {

		var json = JSON.parse(json_symbolizers[i].json);
		var order = json_symbolizers[i].order;
		
		var options = json[0].fields;
		options['order'] = order;
		
		var symbolizer = null;
		if (this.featureType == 'MarkSymbolizer') {
			var utils = new LibraryUtils(this.previewPointUrl);
			symbolizer = new MarkSymbolizer(r, options, utils);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.symbolizers.push(symbolizer);
			symbolizer.updatePreview();
			previewUrl = this.previewPointUrl;
			
		} else if (this.featureType == 'LineSymbolizer') {
			var utils = new LibraryUtils(this.previewLineUrl);
			symbolizer = new LineSymbolizer(r, options, utils);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.symbolizers.push(symbolizer);
			symbolizer.updatePreview();
			previewUrl = this.previewLineUrl;
			
		} else if (this.featureType == 'PolygonSymbolizer') {
			var utils = new LibraryUtils(this.previewPolygonUrl);
			symbolizer = new PolygonSymbolizer(r, options, utils);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.symbolizers.push(symbolizer);
			symbolizer.updatePreview();
			previewUrl = this.previewPolygonUrl;
			
		}
	}
	
	$("#table-symbolizers-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-symbolizers-body").on("sortupdate", function(event, ui){
		var rows = ui.item[0].parentNode.children;
		for(var i=0; i < rows.length; i++) {
			var symbol = self.getSymbolizerById(rows[i].dataset.rowid);
			symbol.order = i;
		}
		self.updatePreview(previewUrl);
	});
	
	$(".edit-symbolizer-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.getSymbolizerById(this.dataset.symbolizerid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-symbolizer-link").one('click', function(e){	
		e.preventDefault();
		self.removeSymbolizer(this.dataset.symbolizerid);
		self.updatePreview(previewUrl);
	});
	
	this.updatePreview(previewUrl);
};

LibrarySymbol.prototype.appendSymbolizer = function(rule, featureType) {
	var self = this;
	
	this.featureType = featureType;
	var previewUrl = null;
	var symbolizer = null;
	if (this.featureType == 'MarkSymbolizer') {
		var utils = new LibraryUtils(this.previewPointUrl);
		symbolizer = new MarkSymbolizer(rule, null, utils);
		previewUrl = this.previewPointUrl;
		
	} else if (this.featureType == 'LineSymbolizer') {
		var utils = new LibraryUtils(this.previewLineUrl);
		symbolizer = new LineSymbolizer(rule, null, utils);
		previewUrl = this.previewLineUrl;
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		var utils = new LibraryUtils(this.previewPolygonUrl);
		symbolizer = new PolygonSymbolizer(rule, null, this.previewPolygonUrl, utils);
		previewUrl = this.previewPolygonUrl;
	}
	
	$('#table-symbolizers tbody').append(symbolizer.getTableUI());
	$("#table-symbolizers-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-symbolizers-body").on("sortupdate", function(event, ui){
		var rows = ui.item[0].parentNode.children;
		for(var i=0; i < rows.length; i++) {
			var symbol = self.getSymbolizerById(rows[i].dataset.rowid);
			symbol.order = i;
		}
		self.updatePreview(previewUrl);
	});
	
	$(".edit-symbolizer-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.getSymbolizerById(this.dataset.symbolizerid));
		self.updateForm();
		$('#modal-symbolizer').modal('show');
	});
	
	$(".delete-symbolizer-link").one('click', function(e){	
		e.preventDefault();
		self.removeSymbolizer(this.dataset.symbolizerid);
		self.updatePreview(previewUrl);
	});
	this.symbolizers.push(symbolizer);
	symbolizer.updatePreview();
	self.updatePreview(previewUrl);
	self.setSelected(symbolizer);
	this.updateForm();
	
};

LibrarySymbol.prototype.setSelected = function(element) {
	this.selected = element;
};

LibrarySymbol.prototype.removeSymbolizer = function(id) {
	for (var i=0; i < this.symbolizers.length; i++) {
		if (this.symbolizers[i].id == id) {
			this.symbolizers.splice(i, 1);
		}
	}
	var tbody = document.getElementById('table-symbolizers-body');
	for (var i=0; i<tbody.children.length; i++) {
		if(tbody.children[i].dataset.rowid == id) {
			tbody.removeChild(tbody.children[i]);
		}
	}
};

LibrarySymbol.prototype.getSymbolizerById = function(id) {
	var symbolizer = null;
	for (var i=0; i < this.symbolizers.length; i++) {
		if (this.symbolizers[i].id == id) {
			symbolizer = this.symbolizers[i];
		}
	}
	return symbolizer;
};

LibrarySymbol.prototype.loadSymbols = function(symbolizers) {
	for (var i=0; i<symbolizers.length; i++) {
		var symbolizer = JSON.parse(symbolizers[i].json);
		this.loadSymbol(symbolizer, symbolizers[i].type);
	}
};

LibrarySymbol.prototype.loadSymbol = function(symbolizer, featureType) {
	var self = this;
	
	this.featureType = featureType;
	
	var symbol = symbolizer;
	
	var ui = '';
	ui += '<tr data-rowid="' + symbol.id + '">';
	ui += 	'<td>'
	ui += 		'<span class="handle"> ';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 		'</span>';
	ui += 	'</td>';
	ui += 	'<td><a class="symbol-link" data-symid="' + symbol.id + '" href="javascript:void(0)">' + symbol.name + '</a></td>';
	ui += 	'<td id="symbolizer-preview"><svg id="symbolizer-preview-' + symbol.id + '" class="preview-svg"></svg></td>';	
	ui += 	'<td><a class="delete-symbol-link" data-symid="' + symbol.id + '" href="javascript:void(0)"><i class="fa fa-times" style="color: #ff0000;"></i></a></td>';
	ui += '</tr>';	
	$('#table-unique-symbol tbody').append(ui);
	
	$("#table-unique-symbol-body").sortable({
		placeholder: "sort-highlight",
		handle: ".handle",
		forcePlaceholderSize: true,
		zIndex: 999999
	});
	$("#table-unique-symbol-body").on("sortupdate", function(event, ui){
		var rows = ui.item[0].parentNode.children;
		for(var i=0; i < rows.length; i++) {
			var symbol = self.getSymbolById(rows[i].dataset.rowid);
			symbol.order = i;
		}		
	});
	
	$(".symbol-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.getSymbolById(this.dataset.symid));
		self.updateForm();
	});
	
	$(".delete-symbol-link").one('click', function(e){	
		e.preventDefault();
		self.deleteSymbol(this.dataset.symid);
		self.updatePreview(previewUrl);
	});
	
	symbol.preview = this.renderSymbolPreview(symbol);
	
	this.symbols.push(symbol);
	this.count++;
	self.setSelected(symbol);
	this.updateForm();
};

LibrarySymbol.prototype.updatePreview = function(previewUrl) {
	for (var i=0; i<this.symbolizers.length; i++) {
		if (this.symbolizers[i].type == 'ExternalGraphicSymbolizer') {
			
		} else {			
			this.symbolizers.sort(function(a, b){
				return parseInt(b.order) - parseInt(a.order);
			});
			
			var sldBody = this.symbologyUtils.getSLDBody(this.symbolizers);
			var url = previewUrl + '&SLD_BODY=' + encodeURIComponent(sldBody);
			var ui = '<img id="rule-preview-img" src="' + url + '" class="rule-preview"></img>';
			$(".library-symbol-preview-div").empty();
			$(".library-symbol-preview-div").append(ui);
		}
		
	}
};

LibrarySymbol.prototype.libraryPreview = function(r, json_symbolizers) {
	var symbolizers = new Array();
	var previewUrl = null;
	for (var i=0; i<json_symbolizers.length; i++) {
		
		var json = JSON.parse(json_symbolizers[i].json);
		var order = json_symbolizers[i].order;
		
		var options = json[0].fields;
		options['order'] = order;
		
		var symbolizer = null;
		if (this.featureType == 'MarkSymbolizer') {
			var utils = new LibraryUtils(this.previewPointUrl);
			symbolizer = new MarkSymbolizer(r, options, utils);
			previewUrl = this.previewPointUrl;
			
		} else if (this.featureType == 'LineSymbolizer') {
			var utils = new LibraryUtils(this.previewLineUrl);
			symbolizer = new LineSymbolizer(r, options, utils);
			previewUrl = this.previewLineUrl;
			
		} else if (this.featureType == 'PolygonSymbolizer') {
			var utils = new LibraryUtils(this.previewPolygonUrl);
			symbolizer = new PolygonSymbolizer(r, options, utils);
			previewUrl = this.previewPolygonUrl;
			
		}
		symbolizers.push(symbolizer);
	}
	symbolizers.sort(function(a, b){
		return parseInt(b.order) - parseInt(a.order);
	});
	
	var sldBody = this.symbologyUtils.getSLDBody(symbolizers);
	var url = previewUrl + '&SLD_BODY=' + encodeURIComponent(sldBody);
	var ui = '<img id="rule-preview-img" src="' + url + '" class="rule-preview"></img>';
	$("#library-symbol-preview-div-" + r.id).empty();
	$("#library-symbol-preview-div-" + r.id).append(ui);
};

LibrarySymbol.prototype.updateForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	$('#tab-menu').append(this.selected.getTabMenu());
	if (this.selected.type == 'MarkSymbolizer') {
		$('#tab-content').append(this.selected.getGraphicTabUI());
		$('#tab-content').append(this.selected.getFillTabUI());
		$('#tab-content').append(this.selected.getStrokeTabUI());
		$('#tab-content').append(this.selected.getRotationTabUI());		
		$('.nav-tabs a[href="#graphic-tab"]').tab('show');
		this.selected.registerEvents(this);
		
	} else if (this.selected.type == 'ExternalGraphicSymbolizer') {
		this.selected.registerEvents();
		
	} else if (this.selected.type == 'LineSymbolizer') {
		$('#tab-content').append(this.selected.getStrokeTabUI());
		$('.nav-tabs a[href="#stroke-tab"]').tab('show');
		this.selected.registerEvents(this);
		
	} else if (this.selected.type == 'PolygonSymbolizer') {
		$('#tab-content').append(this.selected.getFillTabUI());
		$('#tab-content').append(this.selected.getStrokeTabUI());
		$('.nav-tabs a[href="#fill-tab"]').tab('show');
		this.selected.registerEvents(this);
		
	} else if (this.selected.type == 'TextSymbolizer') {
		$('#tab-content').append(this.selected.getFontTabUI());
		$('#tab-content').append(this.selected.getHaloTabUI());
		$('.nav-tabs a[href="#label-font-tab"]').tab('show');
		this.selected.registerEvents();
	}
};

LibrarySymbol.prototype.save = function(libraryid, name, title, filter) {
	
	var elements = new Array();
	for (var i=0; i < this.symbolizers.length; i++) {
		var symbolizer = {
			type: this.symbolizers[i].type,
			sld: this.symbolizers[i].toXML(),
			json: this.symbolizers[i].toJSON(),
			order: this.symbolizers[i].order
		};
		elements.push(symbolizer);
	}
	
	var symbol = {
		name: name,
		title: title,
		order: 0,
		minscale: -1,
		maxscale: -1,
		symbolizers: elements
	};
	
	$.ajax({
		type: "POST",
		async: false,
		//contentType: false,
	    enctype: 'multipart/form-data',
		url: "/gvsigonline/symbology/symbol_add/" + libraryid + "/" + this.featureType + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			file: $("#eg-file")[0],
			rule: JSON.stringify(symbol)
		},
		success: function(response){
			if (response.success) {
				location.href = "/gvsigonline/symbology/library_update/" + libraryid + "/";
			} else {
				$("#form-error").append('<p>*' + response.message + '</p>');
			}
			
		},
	    error: function(){}
	});
};

LibrarySymbol.prototype.update = function(id, name, title, filter) {
	
	var elements = new Array();
	for (var i=0; i < this.symbolizers.length; i++) {
		var symbolizer = {
			type: this.symbolizers[i].type,
			sld: this.symbolizers[i].toXML(),
			json: this.symbolizers[i].toJSON(),
			order: this.symbolizers[i].order
		};
		elements.push(symbolizer);
	}
	
	var symbol = {
		name: name,
		title: title,
		order: 0,
		minscale: -1,
		maxscale: -1,
		symbolizers: elements
	};
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/symbol_update/" + id + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			rule: JSON.stringify(symbol)
		},
		success: function(response){
			if (response.success) {
				location.href = "/gvsigonline/symbology/library_update/" + response.library_id + "/";
			} else {
				$("#form-error").append('<p>*' + response.message + '</p>');
			}
			
		},
	    error: function(){}
	});
};