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
 
 
var SymbolLibrary = function(symbologyUtils) {
	this.selected = null;
	this.featureType = null;
	this.symbologyUtils = symbologyUtils;
	this.symbolizers = new Array();
};

SymbolLibrary.prototype.appendSymbol = function(featureType) {
	var self = this;
	
	this.featureType = featureType;
	
	var symbol = {
		id: this.count,
		type: "symbol",
		name: "symbol " + this.count,
		preview: null,
		shape: "circle",
		fill_color: "#000000",
		fill_opacity: 0.5,
		with_border: true,
		border_color: "#000000",
		border_size: 1,
		border_opacity: 1,
		border_type: "solid",
		vectorial: true,
		online_resource: "",
		format: "",
		rotation: 0,
		order: 0
	};
		
	var ui = '';
	ui += '<tr data-rowid="' + symbol.id + '">';
	ui += 	'<td>'
	ui += 		'<span class="handle"> ';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 		'</span>';
	ui += 	'</td>'
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
			console.log(symbol.name + ' -> ' + symbol.order);
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
	
	return symbol;
};

SymbolLibrary.prototype.setSelected = function(element) {
	this.selected = element;
};

SymbolLibrary.prototype.deleteSymbol = function(id) {
	for (var i=0; i < this.symbols.length; i++) {
		if (this.symbols[i].id == id) {
			this.symbols.splice(i, 1);
		}
	}
	var tbody = document.getElementById('table-unique-symbol-body');
	for (var i=0; i<tbody.children.length; i++) {
		if(tbody.children[i].dataset.rowid == id) {
			tbody.removeChild(tbody.children[i]);
		}
	}
	if (this.symbols.length >= 1) {
		this.setSelected(this.symbols[0]);
		this.updateForm();
	} else {
		$('#tab-content').empty();
		$('#tab-menu').empty();
	}
};

SymbolLibrary.prototype.getSymbolById = function(id) {
	var symbol = null;
	for (var i=0; i < this.symbols.length; i++) {
		if (this.symbols[i].id == id) {
			symbol = this.symbols[i];
		}
	}
	return symbol;
};

SymbolLibrary.prototype.loadSymbols = function(symbolizers) {
	for (var i=0; i<symbolizers.length; i++) {
		var symbolizer = JSON.parse(symbolizers[i].json);
		this.loadSymbol(symbolizer, symbolizers[i].type);
	}
};

SymbolLibrary.prototype.loadSymbol = function(symbolizer, featureType) {
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
			console.log(symbol.name + ' -> ' + symbol.order);
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

SymbolLibrary.prototype.createPreview = function(rid,symbolizers) {
	
	$("#symbolizer-preview-" + rid).empty();
	var previewElement = Snap("#symbolizer-preview-" + rid);
	var previewGroup = previewElement.g();
	
	for (var i=0; i<symbolizers.length; i++) {
		var symbolizer = JSON.parse(symbolizers[i].json);
		var preview = this.addSymbolizer(previewElement, symbolizer, symbolizers[i].type);
		previewGroup.add(preview);
	}
};

SymbolLibrary.prototype.addSymbolizer = function(previewElement, symbol, stype) {
	
	var attributes = {
		fill: symbol.fill_color,
		fillOpacity: parseFloat(symbol.fill_opacity),
		stroke: symbol.border_color,
		strokeOpacity: symbol.border_opacity,
		strokeWidth: symbol.border_size
	}
	if (symbol.border_type == 'dotted') {
		attributes.strokeDasharray= "1 1";
	} else if (symbol.border_type == 'stripped') {
		attributes.strokeDasharray= "4 4";
	}
	
	var preview = null;
	if (stype == 'PointSymbolizer') {
		if (symbol.shape == 'circle') {
			preview = previewElement.circle(10, 10, 10);
			preview.attr(attributes);
			
		} else if (symbol.shape == 'square') {
			preview = previewElement.polygon(0, 0, 20, 0, 20, 20, 0, 20);
			preview.attr(attributes);
			
		} else if (symbol.shape == 'triangle') {
			preview = previewElement.path('M 12.462757,7.4046606 -2.6621031,7.3865562 4.9160059,-5.7029049 z');
			preview.transform( 't5,8');
			preview.attr(attributes);
			
		}  else if (symbol.shape == 'star') {
			preview = previewElement.path('M 7.0268739,7.8907968 2.2616542,5.5298295 -2.3847299,8.1168351 -1.6118504,2.8552628 -5.5080506,-0.76428228 -0.2651651,-1.6551455 1.9732348,-6.479153 4.4406368,-1.7681645 9.7202441,-1.13002 6.0022969,2.6723943 z');
			preview.transform( 't8,9');
			preview.attr(attributes);
			
		} else if (symbol.shape == 'cross') {
			preview = previewElement.path('M 7.875 0.53125 L 7.875 7.40625 L 0.59375 7.40625 L 0.59375 11.3125 L 7.875 11.3125 L 7.875 19.46875 L 11.78125 19.46875 L 11.78125 11.28125 L 19.5625 11.28125 L 19.53125 7.375 L 11.78125 7.375 L 11.78125 0.53125 L 7.875 0.53125 z');
			preview.transform( 't0,0');
			preview.attr(attributes);
			
		} else if (symbol.shape == 'x') {
			preview = previewElement.path('M 4.34375 0.90625 L 0.90625 3.5 L 6.90625 9.9375 L 0.78125 15.53125 L 3.34375 19.03125 L 9.84375 13.09375 L 15.53125 19.15625 L 19 16.5625 L 13.03125 10.1875 L 19.1875 4.5625 L 16.625 1.09375 L 10.09375 7.03125 L 4.34375 0.90625 z');
			preview.transform( 't0,0');
			preview.attr(attributes);
			
		}
		
		
	} else if (stype == 'LineSymbolizer') {
		preview = previewElement.line(0, 0, 20, 20);
		preview.attr(attributes);
		
	} else if (stype == 'PolygonSymbolizer') {
		preview = previewElement.polygon(0, 0, 20, 0, 20, 20, 0, 20);
		preview.attr(attributes);
	}
	return preview;
};

SymbolLibrary.prototype.renderSymbolPreview = function(symbol) {
	
	var attributes = {
		fill: symbol.fill_color,
		fillOpacity: parseFloat(symbol.fill_opacity),
		stroke: symbol.border_color,
		strokeOpacity: symbol.border_opacity,
		strokeWidth: symbol.border_size
	}
	if (symbol.border_type == 'dotted') {
		attributes.strokeDasharray= "1 1";
	} else if (symbol.border_type == 'stripped') {
		attributes.strokeDasharray= "4 4";
	}
	
	var preview = null;
	$("#symbolizer-preview-" + symbol.id).empty();
	var previewElement = Snap("#symbolizer-preview-" + symbol.id);
	if (this.featureType == 'PointSymbolizer') {
		if (symbol.shape == 'circle') {
			preview = previewElement.circle(10, 10, 10);
			preview.attr(attributes);
			
		} else if (symbol.shape == 'square') {
			preview = previewElement.polygon(0, 0, 20, 0, 20, 20, 0, 20);
			preview.attr(attributes);
			
		} else if (symbol.shape == 'triangle') {
			preview = previewElement.path('M 12.462757,7.4046606 -2.6621031,7.3865562 4.9160059,-5.7029049 z');
			preview.transform( 't7,10');
			preview.attr(attributes);
			
		}  else if (symbol.shape == 'star') {
			preview = previewElement.path('M 7.0268739,7.8907968 2.2616542,5.5298295 -2.3847299,8.1168351 -1.6118504,2.8552628 -5.5080506,-0.76428228 -0.2651651,-1.6551455 1.9732348,-6.479153 4.4406368,-1.7681645 9.7202441,-1.13002 6.0022969,2.6723943 z');
			preview.transform( 't10,10');
			preview.attr(attributes);
			
		} else if (symbol.shape == 'cross') {
			preview = previewElement.path('M 7.875 0.53125 L 7.875 7.40625 L 0.59375 7.40625 L 0.59375 11.3125 L 7.875 11.3125 L 7.875 19.46875 L 11.78125 19.46875 L 11.78125 11.28125 L 19.5625 11.28125 L 19.53125 7.375 L 11.78125 7.375 L 11.78125 0.53125 L 7.875 0.53125 z');
			preview.transform( 't0,0');
			preview.attr(attributes);
			
		} else if (symbol.shape == 'x') {
			preview = previewElement.path('M 4.34375 0.90625 L 0.90625 3.5 L 6.90625 9.9375 L 0.78125 15.53125 L 3.34375 19.03125 L 9.84375 13.09375 L 15.53125 19.15625 L 19 16.5625 L 13.03125 10.1875 L 19.1875 4.5625 L 16.625 1.09375 L 10.09375 7.03125 L 4.34375 0.90625 z');
			preview.transform( 't0,0');
			preview.attr(attributes);
			
		}
		
		
	} else if (this.featureType == 'LineSymbolizer') {
		preview = previewElement.line(0, 0, 20, 20);
		preview.attr(attributes);
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		preview = previewElement.polygon(0, 0, 20, 0, 20, 20, 0, 20);
		preview.attr(attributes);
	}
	return preview;
};

SymbolLibrary.prototype.updateForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	$('#tab-menu').append(this.newSymbolTabMenu());
	if (this.featureType == 'PointSymbolizer' && this.selected.vectorial) {
		$('#tab-content').append(this.newSymbolGraphicTab("active"));
		$('#tab-content').append(this.newSymbolFillTab(""));
		$('#tab-content').append(this.newSymbolBorderTab(""));
		$('#tab-content').append(this.newSymbolRotationTab(""));			
		$('.nav-tabs a[href="#graphic-tab"]').tab('show');
		
	} else if (this.featureType == 'PointSymbolizer' && !this.selected.vectorial) {
		$('#tab-content').append(this.newSymbolGraphicTab("active"));			
		$('.nav-tabs a[href="#graphic-tab"]').tab('show');
		
	} else if (this.featureType == 'LineSymbolizer') {
		$('#tab-content').append(this.newSymbolBorderTab("active"));
		$('#tab-content').append(this.newSymbolRotationTab(""));
		$('.nav-tabs a[href="#border-tab"]').tab('show');
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		$('#tab-content').append(this.newSymbolFillTab("active"));
		$('#tab-content').append(this.newSymbolBorderTab(""));
		$('#tab-content').append(this.newSymbolRotationTab(""));
		$('.nav-tabs a[href="#fill-tab"]').tab('show');
	}
	
	this.registerSymbolEvents();
};

SymbolLibrary.prototype.registerSymbolEvents = function() {
	var self = this;
	
	$('input[type=radio][name=symbol-is-vectorial]').change(function() {
        if (this.value == 'vectorial') {
        	self.selected.vectorial = true;
        	self.updateForm();
        	$("#symbolizer-preview").append('<td id="symbolizer-preview"><svg id="symbolizer-preview-' + self.selected.id + '" class="preview-svg"></svg></td>');
    		self.selected.preview = self.renderSymbolPreview(self.selected);
            
        } else if (this.value == 'external-graphic') {
        	self.selected.vectorial = false;
        	self.updateForm();
        	$("#symbolizer-preview").empty();
    		//self.selected.preview = self.renderExternalGraphicPreview(self.selected);
        }
    });
	$("#shape").on('change', function(e) {
		self.selected.shape = this.value;
		self.selected.preview = self.renderSymbolPreview(self.selected);		
	});
	$( "#fill-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.selected.fill_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.fill_opacity = opacity;
			self.selected.preview = self.renderSymbolPreview(self.selected);
	    },
	    slide: function( event, ui ) {
	    	$("#fill-opacity-output").text(ui.value + '%');
	    }
	});	
	$("#fill-color-chooser").on('change', function(e) {
		self.selected.fill_color = this.value;
		self.selected.preview = self.renderSymbolPreview(self.selected);		
	});	
	$('#symbol-with-border').on('change', function() {
		self.selected.with_border = this.checked;		
		self.selected.preview = self.renderSymbolPreview(self.selected);
	});
	$("#border-color-chooser").on('change', function(e) {
		self.selected.border_color = this.value;
		self.selected.preview = self.renderSymbolPreview(self.selected);		
	});
	$( "#border-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.selected.border_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.border_opacity = opacity;
			self.selected.preview = self.renderSymbolPreview(self.selected);
	    },
	    slide: function( event, ui ) {
	    	$("#border-opacity-output").text(ui.value + '%');
	    }
	});
	$("#border-size").on('change', function(e) {
		self.selected.border_size = this.value;
		self.selected.preview = self.renderSymbolPreview(self.selected);		
	});
	$('#border-type').on('change', function() {
		self.selected.border_type = this.value;
		self.selected.preview = self.renderSymbolPreview(self.selected);
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

SymbolLibrary.prototype.newSymbolTabMenu = function() {
	var ui = '';
	if (this.featureType == 'PointSymbolizer' && this.selected.vectorial) {
		ui += '<li class="active"><a href="#graphic-tab" data-toggle="tab">' + gettext('Graphic') + '</a></li>';
		ui += '<li><a href="#fill-tab" data-toggle="tab">' + gettext('Fill') + '</a></li>';
		ui += '<li><a href="#border-tab" data-toggle="tab">' + gettext('Border') + '</a></li>';
		ui += '<li><a href="#rotation-tab" data-toggle="tab">' + gettext('Rotation') + '</a></li>';
		
	} else if (this.featureType == 'PointSymbolizer' && !this.selected.vectorial) {
		ui += '<li class="active"><a href="#graphic-tab" data-toggle="tab">' + gettext('Graphic') + '</a></li>';
		
	} else if (this.featureType == 'LineSymbolizer') {
		ui += '<li class="active"><a href="#border-tab" data-toggle="tab">' + gettext('Border') + '</a></li>';
		ui += '<li><a href="#rotation-tab" data-toggle="tab">' + gettext('Rotation') + '</a></li>';
		
	} else if (this.featureType == 'PolygonSymbolizer') {
		ui += '<li class="active"><a href="#fill-tab" data-toggle="tab">' + gettext('Fill') + '</a></li>';
		ui += '<li><a href="#border-tab" data-toggle="tab">' + gettext('Border') + '</a></li>';
		ui += '<li><a href="#rotation-tab" data-toggle="tab">' + gettext('Rotation') + '</a></li>';
	} 
	
	return ui;	
};

SymbolLibrary.prototype.newSymbolGraphicTab = function(active) {
	var ui = '';
	ui += '<div class="tab-pane ' + active + '" id="graphic-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	if (this.selected.vectorial) {
		ui += 		'<label class="radio-inline"><input type="radio" value="vectorial" name="symbol-is-vectorial" checked>' + gettext('Vectorial') + '</label>';
		ui += 		'<label class="radio-inline"><input type="radio" value="external-graphic" name="symbol-is-vectorial">' + gettext('External graphic') + '</label>';
	} else {
		ui += 		'<label class="radio-inline"><input type="radio" value="vectorial" name="symbol-is-vectorial">' + gettext('Vectorial') + '</label>';
		ui += 		'<label class="radio-inline"><input type="radio" value="external-graphic" name="symbol-is-vectorial" checked>' + gettext('External graphic') + '</label>';
	}
	ui += 		'</div>';
	ui += 	'</div>';
	if (this.selected.vectorial) {
		ui += 	'<div class="row">';
		ui += 		'<div class="col-md-12 form-group">';
		ui += 			'<label>' + gettext('Select shape') + '</label>';
		ui += 			'<select id="shape" class="form-control">';
		for (var i=0; i < this.shapes.length; i++) {
			if (this.shapes[i].value == this.selected.shape) {
				ui += '<option value="' + this.shapes[i].value + '" selected>' + this.shapes[i].title + '</option>';
			} else {
				ui += '<option value="' + this.shapes[i].value + '">' + this.shapes[i].title + '</option>';
			}
		}
		ui += 			'</select>';
		ui += 		'</div>';
		ui += 	'</div>';
	}
	ui += '</div>';
	
	return ui;
	
};

SymbolLibrary.prototype.newSymbolFillTab = function(active) {
	var ui = '';
	ui += '<div class="tab-pane ' + active + '" id="fill-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Fill color') + '</label>';
	ui += 			'<input id="fill-color-chooser" type="color" value="' + this.selected.fill_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Fill opacity') + '<span id="fill-opacity-output" class="margin-l-15 gol-slider-output">' + (this.selected.fill_opacity * 100) + '%</span>' + '</label>';
	ui += 			'<div id="fill-opacity-slider"><div/>';
	ui += 		'</div>';				 
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
	
};

SymbolLibrary.prototype.newSymbolBorderTab = function(active) {
	var ui = '';
	ui += '<div class="tab-pane ' + active + '" id="border-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 checkbox">';
	ui += 			'<label>';
	if (this.selected.with_border) {
		ui += '<input type="checkbox" id="symbol-with-border" name="symbol-with-border" checked/>' + gettext('With border');
	} else {
		ui += '<input type="checkbox" id="symbol-with-border" name="symbol-with-border"/>' + gettext('With border');
	}	
	ui += 			'</label>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Border color') + '</label>';
	ui += 			'<input id="border-color-chooser" type="color" value="' + this.selected.border_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Border size') + '</label>';
	ui += 			'<input id="border-size" type="number" class="form-control" value="' + parseInt(this.selected.border_size) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Border opacity') + '<span id="border-opacity-output" class="margin-l-15 gol-slider-output">' + (this.selected.border_opacity * 100) + '%</span>' + '</label>';
	ui += 			'<div id="border-opacity-slider"></div>';
	ui += 		'</div>';					 
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Border type') + '</label>';
	ui += 			'<select id="border-type" class="form-control">';
	ui += 				'<option value="solid">' + gettext('Solid') + '</option>';
	ui += 				'<option value="dotted">' + gettext('Dotted') + '</option>';
	ui += 				'<option value="stripped">' + gettext('Stripped') + '</option>';
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

SymbolLibrary.prototype.newSymbolRotationTab = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="rotation-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Rotation') + '<span id="rotation-output" class="margin-l-15 gol-slider-output">' + this.selected.rotation + 'º</span>' + '</label>';
	ui += 			'<div id="rotation-slider"><div/>';
	ui += 		'</div>';			 
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

SymbolLibrary.prototype.save = function(libraryid, name, title, filter, minscale, maxscale) {
	
	var symbologyUtils = new SymbologyUtils();
	var type = null;
	var symbolizers = new Array();
	for (var i=0; i < this.symbols.length; i++) {
		if (this.featureType == 'PointSymbolizer') {
			type = 'point';
			symbolizers.push(symbologyUtils.createPointSymbolizer(this.symbols[i]));
				
		} else if (this.featureType == 'LineSymbolizer') {
			type = 'line';
			symbolizers.push(symbologyUtils.createLineSymbolizer(this.symbols[i]));
			
		} else if (this.featureType == 'PolygonSymbolizer') {
			type = 'polygon';
			symbolizers.push(symbologyUtils.createPolygonSymbolizer(this.symbols[i]));
			
		} 
	}
	
	var rule = {
		name: name,
		title: title,
		filter: filter,
		minscale: minscale,
		maxscale: maxscale,
		symbolizers: symbolizers
	};
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/symbol_add/" + libraryid + "/" + type + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			rule: JSON.stringify(rule)
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

SymbolLibrary.prototype.update = function(id, name, title, filter, minscale, maxscale) {
	
	var symbologyUtils = new SymbologyUtils();
	var type = null;
	var symbolizers = new Array();
	for (var i=0; i < this.symbols.length; i++) {
		if (this.featureType == 'PointSymbolizer') {
			type = 'point';
			symbolizers.push(symbologyUtils.createPointSymbolizer(this.symbols[i]));
				
		} else if (this.featureType == 'LineSymbolizer') {
			type = 'line';
			symbolizers.push(symbologyUtils.createLineSymbolizer(this.symbols[i]));
			
		} else if (this.featureType == 'PolygonSymbolizer') {
			type = 'polygon';
			symbolizers.push(symbologyUtils.createPolygonSymbolizer(this.symbols[i]));
			
		} 
	}
	
	var rule = {
		name: name,
		title: title,
		filter: filter,
		minscale: minscale,
		maxscale: maxscale,
		symbolizers: symbolizers
	};
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/symbol_update/" + id + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			rule: JSON.stringify(rule)
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