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
 
 
var UniqueSymbol = function(featureType, fields, alphanumericFields, sldFilterValues, fonts) {
	this.featureType = featureType;
	this.fields = fields;
	this.alphanumericFields = alphanumericFields;
	this.sldFilterValues = sldFilterValues;
	this.fonts = fonts;
	this.fontStyles = [{
		value: 'normal',
		title: gettext('Normal') 
	},{
		value: 'cursive',
		title: gettext('Cursive') 
	},{
		value: 'oblique',
		title: gettext('Oblique') 
	}];
	
	this.fontWeights = [{
		value: 'normal',
		title: gettext('Normal') 
	},{
		value: 'bold',
		title: gettext('Bold') 
	}];
	
	this.shapes = [{
		value: 'circle',
		title: gettext('Circle') 
	},{
		value: 'square',
		title: gettext('Square') 
	},{
		value: 'star',
		title: gettext('Star') 
	}];
};

UniqueSymbol.prototype.count = 0;

UniqueSymbol.prototype.symbols = new Array();
UniqueSymbol.prototype.labels = new Array();

UniqueSymbol.prototype.selected = null;


UniqueSymbol.prototype.appendSymbol = function() {
	var self = this;
	
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
		rotation: 0
	};
	
	var ui = '';
	ui += '<tr data-rowid="' + symbol.id + '">';
	ui += 	'<td><a class="symbol-link" data-symid="' + symbol.id + '" href="javascript:void(0)">' + symbol.name + '</a></td>';
	ui += 	'<td id="symbol-preview"><svg id="symbol-preview-' + symbol.id + '" class="preview-svg"></svg></td>';	
	ui += 	'<td><a class="delete-symbol-link" data-symid="' + symbol.id + '" href="javascript:void(0)"><i class="fa fa-times" style="color: #ff0000;"></i></a></td>';
	ui += '</tr>';	
	$('#table-unique-symbol tbody').append(ui);
	
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

UniqueSymbol.prototype.appendLabel = function() {
	var self = this;
	
	var label = {
		id: this.count,
		type: 'label',
		name: "label " + this.count,
		field: "",
		font_family: "",
		font_size: 12,
		font_color: "#000000",
		font_weight: "normal",
		font_style: "normal",
		halo_color: "#ffffff",
		halo_opacity: 0,
		halo_radius: 1,
		max_iterations: 1,
		max_length: 100,
		min_wrapper: 0,
		solve_overlaps: true,
		preview: null
	};
	
	var ui = '';
	ui += '<tr data-rowid="' + label.id + '">';
	ui += 	'<td><a class="label-link" data-lbid="' + label.id + '" href="javascript:void(0)">' + label.name + '</a></td>';
	ui += 	'<td><svg id="label-preview-' + label.id + '" class="label-preview-svg"></td>';	
	ui += 	'<td><a class="delete-label-link" data-lbid="' + label.id + '" href="javascript:void(0)"><i class="fa fa-times" style="color: #ff0000;"></i></a></td>';
	ui += '</tr>';	
	$('#table-unique-symbol tbody').append(ui);
	
	$(".label-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.getLabelById(this.dataset.lbid));
		self.updateForm();
	});
	
	$(".delete-label-link").one('click', function(e){	
		e.preventDefault();
		self.deleteLabel(this.dataset.lbid);
	});
	
	label.preview = this.renderLabelPreview(label);
	
	this.labels.push(label);
	this.count++;
	self.setSelected(label);
	this.updateForm();
	
	return label;
};

UniqueSymbol.prototype.setSelected = function(element) {
	this.selected = element;
	
	$(".symbol-link").each(function() {$(this).removeClass('link-selected');});
	$(".label-link").each(function() {$(this).removeClass('link-selected');});
	
	if (this.selected.type == 'symbol') {		
		$(".symbol-link").each(function() {
			if (this.dataset.symid == element.id) {
				$(this).addClass('link-selected');
			}			
		});
		
	} else if (this.selected.type == 'label') {
		$(".label-link").each(function() {
			if (this.dataset.lbid == element.id) {
				$(this).addClass('link-selected');
			}			
		});
		
	}
	
};

UniqueSymbol.prototype.deleteSymbol = function(id) {
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

UniqueSymbol.prototype.deleteLabel = function(id) {
	for (var i=0; i < this.labels.length; i++) {
		if (this.labels[i].id == id) {
			this.labels.splice(i, 1);
		}
	}
	var tbody = document.getElementById('table-unique-symbol-body');
	for (var i=0; i<tbody.children.length; i++) {
		if(tbody.children[i].dataset.rowid == id) {
			tbody.removeChild(tbody.children[i]);
		}
	}
	if (this.labels.length >= 1) {
		this.setSelected(this.labels[0]);
		this.updateForm();
	} else {
		$('#tab-content').empty();
		$('#tab-menu').empty();
	}
};

UniqueSymbol.prototype.getSymbolById = function(id) {
	var symbol = null;
	for (var i=0; i < this.symbols.length; i++) {
		if (this.symbols[i].id == id) {
			symbol = this.symbols[i];
		}
	}
	return symbol;
};

UniqueSymbol.prototype.getLabelById = function(id) {
	var label = null;
	for (var i=0; i < this.labels.length; i++) {
		if (this.labels[i].id == id) {
			label = this.labels[i];
		}
	}
	return label;
};

UniqueSymbol.prototype.renderSymbolPreview = function(symbol) {
	
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
	$("#symbol-preview-" + symbol.id).empty();
	var previewElement = Snap("#symbol-preview-" + symbol.id);
	if (this.featureType == 'PointSymbolizer') {
		if (symbol.shape == 'circle') {
			preview = previewElement.circle(10, 10, 10);
			preview.attr(attributes);
			
		} else if (symbol.shape == 'square') {
			preview = previewElement.polygon(0, 0, 20, 0, 20, 20, 0, 20);
			preview.attr(attributes);
			
		} else if (symbol.shape == 'star') {
			preview = previewElement.path('M 0.000 15.000,L 23.511 32.361,L 14.266 4.635,L 38.042 -12.361,L 8.817 -12.135,L 0.000 -40.000,L -8.817 -12.135,L -38.042 -12.361,L -14.266 4.635,L -23.511 32.361,L 0.000 15.000');
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

UniqueSymbol.prototype.renderLabelPreview = function(label) {
	
	var preview = null;
	$("#label-preview-" + label.id).empty();
	var previewElement = Snap("#label-preview-" + label.id);
	
	var f_Shadow = previewElement.filter(Snap.filter.shadow(0, 0, label.halo_color, parseFloat(label.halo_opacity)));
	
	var attributes = {
		fontSize: label.font_size, 
		fontFamily: label.font_family,
		fill: label.font_color,
		fontWeight: label.font_weight,
		fontStyle: label.font_style/*,
		filter : f_Shadow*/
	}

	preview = previewElement.text(10,20, "Text");
	preview.attr(attributes);

	return preview;
};

UniqueSymbol.prototype.updateForm = function() {
	$('#tab-menu').empty();
	$('#tab-content').empty();	
	
	if (this.selected.type == 'symbol') {
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
		
	} else if (this.selected.type == 'label') {
		$('#tab-menu').append(this.newLabelTabMenu());
		$('#tab-content').append(this.newLabelFontTab());
		$('#tab-content').append(this.newLabelHaloTab());
		$('#tab-content').append(this.newLabelVendorTab());
		
		this.registerLabelEvents();
		$('.nav-tabs a[href="#label-font-tab"]').tab('show');
	
	}
};

UniqueSymbol.prototype.registerSymbolEvents = function() {
	var self = this;
	
	$('input[type=radio][name=symbol-is-vectorial]').change(function() {
        if (this.value == 'vectorial') {
        	self.selected.vectorial = true;
        	self.updateForm();
        	$("#symbol-preview").append('<td id="symbol-preview"><svg id="symbol-preview-' + self.selected.id + '" class="preview-svg"></svg></td>');
    		self.selected.preview = self.renderSymbolPreview(self.selected);
            
        } else if (this.value == 'external-graphic') {
        	self.selected.vectorial = false;
        	self.updateForm();
        	$("#symbol-preview").empty();
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

UniqueSymbol.prototype.registerLabelEvents = function() {
	var self = this;
	
	$('#label-field').on('change', function() {
		self.selected.field = this.value;
		self.selected.preview = self.renderLabelPreview(self.selected);
	});
	
	$('#label-font-family').on('change', function() {
		self.selected.font_family = this.value;
		self.selected.preview = self.renderLabelPreview(self.selected);
	});
	
	$('#label-font-size').on('change', function() {
		self.selected.font_size = this.value;
		self.selected.preview = self.renderLabelPreview(self.selected);
	});
	
	$('#label-font-color').on('change', function() {
		self.selected.font_color = this.value;		
		self.selected.preview = self.renderLabelPreview(self.selected);
	});
	
	$('#label-font-weight').on('change', function() {
		self.selected.font_weight = this.value;
		self.selected.preview = self.renderLabelPreview(self.selected);
	});
	
	$('#label-font-style').on('change', function() {
		self.selected.font_style = this.value;
		self.selected.preview = self.renderLabelPreview(self.selected);
	});
	
	$('#label-halo-color').on('change', function() {
		self.selected.halo_color = this.value;		
		self.selected.preview = self.renderLabelPreview(self.selected);
	});
	
	$('#label-halo-radius').on('change', function() {
		self.selected.halo_radius = this.value;		
		self.selected.preview = self.renderLabelPreview(self.selected);
	});
	
	$( "#halo-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.selected.halo_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.halo_opacity = opacity;
			self.selected.preview = self.renderLabelPreview(self.selected);
	    },
	    slide: function( event, ui ) {
	    	$("#halo-opacity-output").text(ui.value + '%');
	    }
	});
	
	$('#label-max-iterations').on('change', function() {
		self.selected.max_iterations = this.value;		
		self.selected.preview = self.renderLabelPreview(self.selected);
	});
	
	$('#label-max-length').on('change', function() {
		self.selected.max_length = this.value;		
		self.selected.preview = self.renderLabelPreview(self.selected);
	});
	
	$('#label-min-wrapper').on('change', function() {
		self.selected.min_wrapper = this.value;		
		self.selected.preview = self.renderLabelPreview(self.selected);
	});
	
	$('#label-solve-overlaps').on('change', function() {
		self.selected.solve_overlaps = this.checked;		
		self.selected.preview = self.renderLabelPreview(self.selected);
	});
};

UniqueSymbol.prototype.newSymbolTabMenu = function() {
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

UniqueSymbol.prototype.newSymbolGraphicTab = function(active) {
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

UniqueSymbol.prototype.newSymbolFillTab = function(active) {
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

UniqueSymbol.prototype.newSymbolBorderTab = function(active) {
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

UniqueSymbol.prototype.newSymbolRotationTab = function() {
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

UniqueSymbol.prototype.newLabelTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#label-font-tab" data-toggle="tab">' + gettext('Font') + '</a></li>';
	ui += '<li><a href="#label-halo-tab" data-toggle="tab">' + gettext('Halo') + '</a></li>';
	ui += '<li><a href="#label-vendor-tab" data-toggle="tab">' + gettext('Vendor') + '</a></li>'; 
	
	return ui;	
};

UniqueSymbol.prototype.newLabelFontTab = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="label-font-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Label field') + '</label>';
	ui += 			'<select id="label-field" class="form-control">';
	for (var i=0; i < this.alphanumericFields.length; i++) {
		if (this.alphanumericFields[i].name == this.selected.field) {
			ui += '<option value="' + this.alphanumericFields[i].name + '" selected>' + this.alphanumericFields[i].name + '</option>';
		} else {
			ui += '<option value="' + this.alphanumericFields[i].name + '">' + this.alphanumericFields[i].name + '</option>';
		}
	}	
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font family') + '</label>';
	ui += 			'<select id="label-font-family" class="form-control">';
	for (var font in this.fonts) {
		if (font == this.selected.font_family) {
			ui += '<option value="' + font + '" selected>' + font + '</option>';
		} else {
			ui += '<option value="' + font + '">' + font + '</option>';
		}
	}	
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font size') + '</label>';
	ui += 			'<input id="label-font-size" type="number" class="form-control" value="' + parseInt(this.selected.font_size) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font color') + '</label>';
	ui += 			'<input id="label-font-color" type="color" value="' + this.selected.font_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font weight') + '</label>';
	ui += 			'<select id="label-font-weight" class="form-control">';
	for (var i=0; i < this.fontWeights.length; i++) {
		if (this.fontWeights[i].value == this.selected.font_weight) {
			ui += '<option value="' + this.fontWeights[i].value + '" selected>' + this.fontWeights[i].title + '</option>';
		} else {
			ui += '<option value="' + this.fontWeights[i].value + '">' + this.fontWeights[i].title + '</option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font style') + '</label>';
	ui += 			'<select id="label-font-style" class="form-control">';
	for (var i=0; i < this.fontStyles.length; i++) {
		if (this.fontStyles[i].value == this.selected.font_style) {
			ui += '<option value="' + this.fontStyles[i].value + '" selected>' + this.fontStyles[i].title + '</option>';
		} else {
			ui += '<option value="' + this.fontStyles[i].value + '">' + this.fontStyles[i].title + '</option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
	
};

UniqueSymbol.prototype.newLabelHaloTab = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="label-halo-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Halo color') + '</label>';
	ui += 			'<input id="label-halo-color" type="color" value="' + this.selected.halo_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Halo opacity') + '<span id="halo-opacity-output" class="margin-l-15 gol-slider-output">' + (this.selected.halo_opacity * 100) + '%</span>' + '</label>';
	ui += 			'<div id="halo-opacity-slider"></div>';
	ui += 		'</div>';					 
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Halo radius') + '</label>';
	ui += 			'<input id="label-halo-radius" type="number" class="form-control" value="' + parseInt(this.selected.halo_radius) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
	
};

UniqueSymbol.prototype.newLabelVendorTab = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="label-vendor-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Maximum number of repetitions') + '</label>';
	ui += 			'<input id="label-max-iterations" type="number" class="form-control" value="' + parseInt(this.selected.max_iterations) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Maximum label length (in pixels)') + '</label>';
	ui += 			'<input id="label-max-length" type="number" class="form-control" value="' + parseInt(this.selected.max_length) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Minimum space surround tag') + '</label>';
	ui += 			'<input id="label-min-wrapper" type="number" class="form-control" value="' + parseInt(this.selected.min_wrapper) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 checkbox">';
	ui += 			'<label>';
	if (this.selected.solve_overlaps) {
		ui += '<input type="checkbox" id="label-solve-overlaps" name="label-solve-overlaps" checked/>' + gettext('Solve overlaps');
	} else {
		ui += '<input type="checkbox" id="label-solve-overlaps" name="label-solve-overlaps"/>' + gettext('Solve overlaps');
	}	
	ui += 			'</label>';	
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
	
};

UniqueSymbol.prototype.save = function(layerId) {
	
	var symbologyUtils = new SymbologyUtils();
	
	var elements = new Array();
	for (var i=0; i < this.symbols.length; i++) {
		if (this.featureType == 'PointSymbolizer') {
			elements.push(symbologyUtils.createPointSymbolizer(this.symbols[i]));
				
		} else if (this.featureType == 'LineSymbolizer') {
			elements.push(symbologyUtils.createLineSymbolizer(this.symbols[i]));
			
		} else if (this.featureType == 'PolygonSymbolizer') {
			elements.push(symbologyUtils.createPolygonSymbolizer(this.symbols[i]));
			
		} 
	}
	
	for (var i=0; i < this.labels.length; i++) {
		elements.push(symbologyUtils.createTextSymbolizer(this.labels[i]));
	}
	
	var data = {
		type: "SU",
		rule: {
			name: "",
			order: 0,
			minscale: -1,
			maxscale: -1
		},
		symbols: elements
	}
	
	$.ajax({
		type: "POST",
		async: false,
		url: "/gvsigonline/symbology/save_style/" + layerId + "/",
		beforeSend:function(xhr){
			xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
		},
		data: {
			style_data: JSON.stringify(data)
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