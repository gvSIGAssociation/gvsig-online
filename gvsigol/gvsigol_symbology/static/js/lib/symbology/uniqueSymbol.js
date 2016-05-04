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
};

UniqueSymbol.prototype.count = 0;

UniqueSymbol.prototype.vectors = new Array();
UniqueSymbol.prototype.graphics = new Array();
UniqueSymbol.prototype.labels = new Array();

UniqueSymbol.prototype.selected = null;


UniqueSymbol.prototype.appendVector = function() {
	var self = this;
	
	var vector = {
		id: this.count,
		type: "vector",
		name: "vector " + this.count,
		preview: null,
		fill_color: "#000000",
		fill_opacity: 0.5,
		with_border: true,
		border_color: "#000000",
		border_size: 1,
		border_opacity: 1,
		border_type: "solid",
		rotation: 0
	};
	
	var ui = '';
	ui += '<tr data-rowid="' + vector.id + '">';
	ui += 	'<td><a class="vector-link" data-vid="' + vector.id + '" href="javascript:void(0)">' + vector.name + '</a></td>';
	ui += 	'<td><svg id="vector-preview-' + vector.id + '" class="preview-svg"></svg></td>';	
	ui += 	'<td><a class="delete-vector-link" data-vid="' + vector.id + '" href="javascript:void(0)"><i class="fa fa-times" style="color: #ff0000;"></i></a></td>';
	ui += '</tr>';	
	$('#table-unique-symbol tbody').append(ui);
	
	$(".vector-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.getVectorById(this.dataset.vid));
		self.updateForm();
	});
	
	$(".delete-vector-link").one('click', function(e){	
		e.preventDefault();
		self.deleteVector(this.dataset.vid);
	});
	
	vector.preview = this.renderVectorPreview(vector);
	
	this.vectors.push(vector);
	this.count++;
	self.setSelected(vector);
	this.updateForm();
	
	return vector;
};

UniqueSymbol.prototype.appendGraphic = function() {
	var self = this;
	
	var graphic = {
		id: this.count,
		type: 'graphic',
		name: "graphic " + this.count,
		preview: null
	};
	
	var ui = '';
	ui += '<tr data-rowid="' + graphic.id + '">';
	ui += 	'<td><a class="graphic-link" data-gid="' + graphic.id + '" href="javascript:void(0)">' + graphic.name + '</a></td>';
	ui += 	'<td><img id="graphic-preview-' + graphic.id + '" class="" /></td>';	
	ui += 	'<td><a class="delete-graphic-link" data-gid="' + graphic.id + '" href="javascript:void(0)"><i class="fa fa-times" style="color: #ff0000;"></i></a></td>';
	ui += '</tr>';	
	$('#table-unique-symbol tbody').append(ui);
	
	$(".graphic-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.getGraphicById(this.dataset.gid));
		self.updateForm();
	});
	
	$(".delete-graphic-link").one('click', function(e){	
		e.preventDefault();
		self.deleteGraphic(this.dataset.gid);
	});
	
	//graphic.preview = this.renderVectorPreview(vector);
	
	this.graphics.push(graphic);
	this.count++;
	self.setSelected(graphic);
	this.updateForm();
	
	return graphic;
};

UniqueSymbol.prototype.appendLabel = function() {
	var self = this;
	
	var label = {
		id: this.count,
		type: 'label',
		name: "label " + this.count,
		field: "",
		font_type: "",
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
	ui += 	'<td><a class="label-link" data-lid="' + label.id + '" href="javascript:void(0)">' + label.name + '</a></td>';
	ui += 	'<td><svg id="label-preview-' + label.id + '" class="label-preview-svg"></td>';	
	ui += 	'<td><a class="delete-label-link" data-lid="' + label.id + '" href="javascript:void(0)"><i class="fa fa-times" style="color: #ff0000;"></i></a></td>';
	ui += '</tr>';	
	$('#table-unique-symbol tbody').append(ui);
	
	$(".label-link").on('click', function(e){	
		e.preventDefault();
		self.setSelected(self.getLabelById(this.dataset.lid));
		self.updateForm();
	});
	
	$(".delete-label-link").one('click', function(e){	
		e.preventDefault();
		self.deleteLabel(this.dataset.lid);
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
	
	$(".vector-link").each(function() {$(this).removeClass('link-selected');});
	$(".graphic-link").each(function() {$(this).removeClass('link-selected');});
	$(".label-link").each(function() {$(this).removeClass('link-selected');});
	
	if (this.selected.type == 'vector') {		
		$(".vector-link").each(function() {
			if (this.dataset.vid == element.id) {
				$(this).addClass('link-selected');
			}			
		});
		
	} else if (this.selected.type == 'graphic') {
		$(".graphic-link").each(function() {
			if (this.dataset.gid == element.id) {
				$(this).addClass('link-selected');
			}			
		});
		
	} else if (this.selected.type == 'label') {
		$(".label-link").each(function() {
			if (this.dataset.lid == element.id) {
				$(this).addClass('link-selected');
			}			
		});
		
	}
	
};

UniqueSymbol.prototype.deleteVector = function(id) {
	for (var i=0; i < this.vectors.length; i++) {
		if (this.vectors[i].id == id) {
			this.vectors.splice(i, 1);
		}
	}
	var tbody = document.getElementById('table-unique-symbol-body');
	for (var i=0; i<tbody.children.length; i++) {
		if(tbody.children[i].dataset.rowid == id) {
			tbody.removeChild(tbody.children[i]);
		}
	}
	if (this.vectors.length >= 1) {
		this.setSelected(this.vectors[0]);
		this.updateForm();
	} else {
		$('#tab-content').empty();
		$('#tab-menu').empty();
	}
};

UniqueSymbol.prototype.deleteGraphic = function(id) {
	for (var i=0; i < this.graphics.length; i++) {
		if (this.graphics[i].id == id) {
			this.graphics.splice(i, 1);
		}
	}
	var tbody = document.getElementById('table-unique-symbol-body');
	for (var i=0; i<tbody.children.length; i++) {
		if(tbody.children[i].dataset.rowid == id) {
			tbody.removeChild(tbody.children[i]);
		}
	}
	if (this.graphics.length >= 1) {
		this.setSelected(this.graphics[0]);
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

UniqueSymbol.prototype.getVectorById = function(id) {
	var vector = null;
	for (var i=0; i < this.vectors.length; i++) {
		if (this.vectors[i].id == id) {
			vector = this.vectors[i];
		}
	}
	return vector;
};

UniqueSymbol.prototype.getGraphicById = function(id) {
	var graphic = null;
	for (var i=0; i < this.graphics.length; i++) {
		if (this.graphics[i].id == id) {
			graphic = this.graphics[i];
		}
	}
	return graphic;
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

UniqueSymbol.prototype.renderVectorPreview = function(vector) {
	
	var attributes = {
		fill: vector.fill_color,
		fillOpacity: parseFloat(vector.fill_opacity),
		stroke: vector.border_color,
		strokeOpacity: vector.border_opacity,
		strokeWidth: vector.border_size
	}
	if (vector.border_type == 'dotted') {
		attributes.strokeDasharray= "1 1";
	} else if (vector.border_type == 'stripped') {
		attributes.strokeDasharray= "4 4";
	}
	
	var preview = null;
	$("#vector-preview-" + vector.id).empty();
	var previewElement = Snap("#vector-preview-" + vector.id);
	if (this.featureType == 'PointSymbolizer') {
		preview = previewElement.circle(10, 10, 10);
		preview.attr(attributes);
		
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
	
	if (this.selected.type == 'vector') {
		$('#tab-menu').append(this.newVectorTabMenu());
		$('#tab-content').append(this.newVectorFillTab());
		$('#tab-content').append(this.newVectorBorderTab());
		$('#tab-content').append(this.newVectorRotationTab());
		this.registerVectorEvents();
		$('.nav-tabs a[href="#fill-tab"]').tab('show');
		
	} else if (this.selected.type == 'graphic') {
		
		
	} else if (this.selected.type == 'label') {
		$('#tab-menu').append(this.newLabelTabMenu());
		$('#tab-content').append(this.newLabelFontTab());
		$('#tab-content').append(this.newLabelHaloTab());
		$('#tab-content').append(this.newLabelVendorTab());
		
		this.registerLabelEvents();
		$('.nav-tabs a[href="#label-font-tab"]').tab('show');
	
	}
};

UniqueSymbol.prototype.registerVectorEvents = function() {
	var self = this;
	
	$( "#fill-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.selected.fill_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.fill_opacity = opacity;
			self.selected.preview = self.renderVectorPreview(self.selected);
	    },
	    slide: function( event, ui ) {
	    	$("#fill-opacity-output").text(ui.value + '%');
	    }
	});	
	$("#fill-color-chooser").on('change', function(e) {
		self.selected.fill_color = this.value;
		self.selected.preview = self.renderVectorPreview(self.selected);		
	});	
	$('#vector-with-border').on('change', function() {
		self.selected.with_border = this.checked;		
		self.selected.preview = self.renderVectorPreview(self.selected);
	});
	$("#border-color-chooser").on('change', function(e) {
		self.selected.border_color = this.value;
		self.selected.preview = self.renderVectorPreview(self.selected);		
	});
	$( "#border-opacity-slider" ).slider({
	    min: 0,
	    max: 100,
	    value: (self.selected.border_opacity * 100),
	    change: function( event, ui ) {
	    	var opacity = parseFloat((ui.value / 100)).toFixed(1);
	    	self.selected.border_opacity = opacity;
			self.selected.preview = self.renderVectorPreview(self.selected);
	    },
	    slide: function( event, ui ) {
	    	$("#border-opacity-output").text(ui.value + '%');
	    }
	});
	$("#border-size").on('change', function(e) {
		self.selected.border_size = this.value;
		self.selected.preview = self.renderVectorPreview(self.selected);		
	});
	$('#border-type').on('change', function() {
		self.selected.border_type = this.value;
		self.selected.preview = self.renderVectorPreview(self.selected);
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

UniqueSymbol.prototype.registerGraphicEvents = function() {
	var self = this;
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

UniqueSymbol.prototype.newVectorTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#fill-tab" data-toggle="tab">' + gettext('Fill') + '</a></li>';
	ui += '<li><a href="#border-tab" data-toggle="tab">' + gettext('Border') + '</a></li>';
	ui += '<li><a href="#rotation-tab" data-toggle="tab">' + gettext('Rotation') + '</a></li>'; 
	
	return ui;	
};

UniqueSymbol.prototype.newVectorFillTab = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="fill-tab">';
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

UniqueSymbol.prototype.newVectorBorderTab = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="border-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 checkbox">';
	ui += 			'<label>';
	if (this.selected.with_border) {
		ui += '<input type="checkbox" id="vector-with-border" name="vector-with-border" checked/>' + gettext('With border');
	} else {
		ui += '<input type="checkbox" id="vector-with-border" name="vector-with-border"/>' + gettext('With border');
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

UniqueSymbol.prototype.newVectorRotationTab = function() {
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