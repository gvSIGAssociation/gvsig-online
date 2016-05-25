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
};

LibrarySymbol.prototype.getSymbolizers = function() {
	return this.symbolizers;
};

LibrarySymbol.prototype.loadSymbolizers = function(json_symbolizers) {
	var self = this;
	var previewUrl = null;
	for (var i=0; i<json_symbolizers.length; i++) {
		var symbolizer_object = JSON.parse(json_symbolizers[i].json);
		var symbolizer = null;
		if (symbolizer_object.type == 'PointSymbolizer') {
			symbolizer = new PointSymbolizer(this.count, this, this.symbologyUtils, symbolizer_object, this.previewPointUrl);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.symbolizers.push(symbolizer);
			symbolizer.updatePreview();
			previewUrl = this.previewPointUrl;
			
		} else if (symbolizer_object.type == 'LineSymbolizer') {
			symbolizer = new LineSymbolizer(this.count, this, symbolizer_object, this.previewLineUrl);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.symbolizers.push(symbolizer);
			symbolizer.updatePreview();
			previewUrl = this.previewLineUrl;
			
		} else if (symbolizer_object.type == 'PolygonSymbolizer') {
			symbolizer = new PolygonSymbolizer(this.count, this, symbolizer_object, this.previewPolygonUrl);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.symbolizers.push(symbolizer);
			symbolizer.updatePreview();
			previewUrl = this.previewPolygonUrl;
			
		} else if (symbolizer_object.type == 'TextSymbolizer') {
			symbolizer = new TextSymbolizer(this.count, this, symbolizer_object);
			$('#table-symbolizers tbody').append(symbolizer.getTableUI());
			this.symbolizers.push(symbolizer);
			symbolizer.updatePreview();
		}
		this.count++;
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
	});
	
	this.updatePreview(previewUrl);
};

LibrarySymbol.prototype.appendSymbolizer = function(featureType) {
	var self = this;
	
	this.featureType = featureType;
	var previewUrl = null;
	var symbolizer = null;
	if (this.featureType == 'PointSymbolizer') {
		symbolizer = new PointSymbolizer(this.count, null, this.symbologyUtils, null, this.previewPointUrl);
		previewUrl = this.previewPointUrl;
		
	} else if (this.featureType == 'ExternalGraphicSymbolizer') {
		symbolizer = new ExternalGraphicSymbolizer(this.count, null, this.symbologyUtils);
		
	} else if (this.featureType == 'LineSymbolizer') {
		symbolizer = new LineSymbolizer(this.count, null, null, this.previewLineUrl);
		previewUrl = this.previewLineUrl;
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		symbolizer = new PolygonSymbolizer(this.count, null, null, this.previewPolygonUrl);
		previewUrl = this.previewPolygonUrl;
	}
	this.count++;
	
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

LibrarySymbol.prototype.libraryPreview = function(rid, json_symbolizers) {
	var symbolizers = new Array();
	var scount = 0;
	var previewUrl = null;
	for (var i=0; i<json_symbolizers.length; i++) {
		var symbolizer_object = JSON.parse(json_symbolizers[i].json);
		var symbolizer = null;
		if (symbolizer_object.type == 'PointSymbolizer') {
			symbolizer = new PointSymbolizer(this.count, this, this.symbologyUtils, symbolizer_object, this.previewPointUrl);
			previewUrl = this.previewPointUrl;
			
		} else if (symbolizer_object.type == 'LineSymbolizer') {
			symbolizer = new LineSymbolizer(this.count, this, symbolizer_object, this.previewLineUrl);
			previewUrl = this.previewLineUrl;
			
		} else if (symbolizer_object.type == 'PolygonSymbolizer') {
			symbolizer = new PolygonSymbolizer(this.count, this, symbolizer_object, this.previewPolygonUrl);
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

LibrarySymbol.prototype.updateForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	$('#tab-menu').append(this.selected.getTabMenu());
	if (this.selected.type == 'PointSymbolizer') {
		$('#tab-content').append(this.selected.getGraphicTabUI());
		$('#tab-content').append(this.selected.getFillTabUI());
		$('#tab-content').append(this.selected.getBorderTabUI());
		$('#tab-content').append(this.selected.getRotationTabUI());		
		$('.nav-tabs a[href="#graphic-tab"]').tab('show');
		this.registerSymbolizerEvents(this.previewPointUrl);
		
	} else if (this.selected.type == 'ExternalGraphicSymbolizer') {
		$('#tab-content').append(this.selected.getGraphicTabUI());
		this.selected.registerExternalGraphicEvents();
		
	} else if (this.selected.type == 'LineSymbolizer') {
		$('#tab-content').append(this.selected.getBorderTabUI());
		$('.nav-tabs a[href="#border-tab"]').tab('show');
		this.registerSymbolizerEvents(this.previewLineUrl);
		
	} else if (this.selected.type == 'PolygonSymbolizer') {
		$('#tab-content').append(this.selected.getFillTabUI());
		$('#tab-content').append(this.selected.getBorderTabUI());
		$('#tab-content').append(this.selected.getRotationTabUI());
		$('.nav-tabs a[href="#fill-tab"]').tab('show');
		this.registerSymbolizerEvents(this.previewPolygonUrl);
		
	}
};

LibrarySymbol.prototype.registerSymbolizerEvents = function(previewUrl) {
	var self = this;
	$("#graphic-size").on('change', function(e) {
		self.selected.size = this.value;
		self.selected.updatePreview();	
		self.updatePreview(previewUrl);
	});
	$('input[type=radio][name=symbol-is-vectorial]').change(function() {
        if (this.value == 'vectorial') {
        	self.selected.vectorial = true;
        	self.updateForm();
        	$("#symbolizer-preview").append('<td id="symbolizer-preview"><svg id="symbolizer-preview-' + self.selected.id + '" class="preview-svg"></svg></td>');
        	self.selected.updatePreview();
        	self.updatePreview(previewUrl);
            
        } else if (this.value == 'external-graphic') {
        	self.selected.vectorial = false;
        	self.updateForm();
        	$("#symbolizer-preview").empty();
        }
    });
	$("#shape").on('change', function(e) {
		self.selected.shape = this.value;
		self.selected.updatePreview();	
		self.updatePreview(previewUrl);
	});
	$( "#fill-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.selected.fill_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.fill_opacity = opacity;
	    	self.selected.updatePreview();
	    	self.updatePreview(previewUrl);
	    },
	    slide: function( event, ui ) {
	    	$("#fill-opacity-output").text(ui.value + '%');
	    }
	});	
	$("#fill-color-chooser").on('change', function(e) {
		self.selected.fill_color = this.value;
		self.selected.updatePreview();	
		self.updatePreview(previewUrl);
	});	
	$('#symbol-with-border').on('change', function() {
		self.selected.with_border = this.checked;		
		self.selected.updatePreview();
		self.updatePreview(previewUrl);
	});
	$("#border-color-chooser").on('change', function(e) {
		self.selected.border_color = this.value;
		self.selected.updatePreview();	
		self.updatePreview(previewUrl);
	});
	$( "#border-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.selected.border_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.border_opacity = opacity;
	    	self.selected.updatePreview();
	    	self.updatePreview(previewUrl);
	    },
	    slide: function( event, ui ) {
	    	$("#border-opacity-output").text(ui.value + '%');
	    }
	});
	$("#border-size").on('change', function(e) {
		self.selected.border_size = this.value;
		self.selected.updatePreview();	
		self.updatePreview(previewUrl);
	});
	$('#border-type').on('change', function() {
		self.selected.border_type = this.value;
		self.selected.updatePreview();
		self.updatePreview(previewUrl);
	});
	$( "#rotation-slider" ).slider({
	    min: 0,
	    max: 360,
	    value: self.selected.rotation,
	    slide: function( event, ui ) {
	    	var rotation = ui.value;
	    	$("#rotation-output").text(rotation + 'º');
	    	self.selected.rotation = rotation;
	    }
	});
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
		filter: filter,
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
		filter: filter,
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