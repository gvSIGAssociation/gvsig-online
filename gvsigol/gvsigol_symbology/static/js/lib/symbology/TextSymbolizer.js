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
 
var TextSymbolizer = function(id, symbologyUtils, rule, symbolizer_object) {
	this.id = 'textsymbolizer' + id;
	this.type = 'TextSymbolizer';
	this.name = 'TextSymbolizer ' + id;
	this.field = '';
	this.font_family = "";
	this.font_size= 12;
	this.font_color = "#000000";
	this.font_weight = "normal";
	this.font_style = "normal";
	this.halo_color = "#ffffff";
	this.halo_opacity = 0;
	this.halo_radius = 1;
	this.max_iterations = 1;
	this.max_length = 100;
	this.min_wrapper = 0;
	this.solve_overlaps = true;
	this.order = 0;
	this.symbologyUtils = symbologyUtils;
	this.rule = rule;
	
	if (symbolizer_object) {
		this.name = symbolizer_object.name;
		this.field = symbolizer_object.field;
		this.font_family = symbolizer_object.font_family;
		this.font_size = symbolizer_object.font_size;
		this.font_color = symbolizer_object.font_color;
		this.font_weight = symbolizer_object.font_weight;
		this.font_style = symbolizer_object.font_style;
		this.halo_color = symbolizer_object.halo_color;
		this.halo_opacity = symbolizer_object.halo_opacity;
		this.halo_radius = symbolizer_object.halo_radius;
		this.max_iterations = symbolizer_object.max_iterations;
		this.max_length = symbolizer_object.max_length;
		this.min_wrapper = symbolizer_object.min_wrapper;
		this.solve_overlaps = symbolizer_object.solve_overlaps;
		this.order = symbolizer_object.order;
	}
};

TextSymbolizer.prototype.getTableUI = function() {
	var ui = '';
	ui += '<tr data-rowid="' + this.id + '">';
	ui += 	'<td>'
	ui += 		'<span class="handle"> ';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 		'</span>';
	ui += 	'</td>';
	ui += 	'<td><span class="text-muted">' + this.name + '</span></td>';
	ui += 	'<td id="label-preview"><svg id="label-preview-' + this.id + '" class="label-preview-svg"></svg></td>';	
	ui += 	'<td><a class="edit-label-link" data-labelid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-edit text-primary"></i></a></td>';
	ui += 	'<td><a class="delete-label-link" data-labelid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-times text-danger"></i></a></td>';
	ui += '</tr>';	
	
	return ui;
};

TextSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#label-font-tab" data-toggle="tab">' + gettext('Font') + '</a></li>';
	ui += '<li><a href="#label-halo-tab" data-toggle="tab">' + gettext('Halo') + '</a></li>';
	ui += '<li><a href="#label-vendor-tab" data-toggle="tab">' + gettext('Vendor') + '</a></li>'; 
	
	return ui;	
};

TextSymbolizer.prototype.getFontTabUI = function() {
	
	var fields = this.symbologyUtils.getAlphanumericFields();
	var fonts = this.symbologyUtils.getFonts();
	var fontWeights = this.symbologyUtils.getFontWeights();
	var fontStyles = this.symbologyUtils.getFontStyles();
	
	var ui = '';
	ui += '<div class="tab-pane active" id="label-font-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Label field') + '</label>';
	ui += 			'<select id="label-field" class="form-control">';
	for (var i=0; i < fields.length; i++) {
		if (fields[i].name == this.field) {
			ui += '<option value="' + fields[i].name + '" selected>' + fields[i].name + '</option>';
		} else {
			ui += '<option value="' + fields[i].name + '">' + fields[i].name + '</option>';
		}
	}	
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font family') + '</label>';
	ui += 			'<select id="label-font-family" class="form-control">';
	for (var font in fonts) {
		if (font == this.font_family) {
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
	ui += 			'<input id="label-font-size" type="number" class="form-control" value="' + parseInt(this.font_size) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font color') + '</label>';
	ui += 			'<input id="label-font-color" type="color" value="' + this.font_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font weight') + '</label>';
	ui += 			'<select id="label-font-weight" class="form-control">';
	for (var i=0; i < fontWeights.length; i++) {
		if (fontWeights[i].value == this.font_weight) {
			ui += '<option value="' + fontWeights[i].value + '" selected>' + fontWeights[i].title + '</option>';
		} else {
			ui += '<option value="' + fontWeights[i].value + '">' + fontWeights[i].title + '</option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Font style') + '</label>';
	ui += 			'<select id="label-font-style" class="form-control">';
	for (var i=0; i < fontStyles.length; i++) {
		if (fontStyles[i].value == this.font_style) {
			ui += '<option value="' + fontStyles[i].value + '" selected>' + fontStyles[i].title + '</option>';
		} else {
			ui += '<option value="' + fontStyles[i].value + '">' + fontStyles[i].title + '</option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

TextSymbolizer.prototype.getHaloTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="label-halo-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Halo color') + '</label>';
	ui += 			'<input id="label-halo-color" type="color" value="' + this.halo_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Halo opacity') + '<span id="halo-opacity-output" class="margin-l-15 gol-slider-output">' + (this.halo_opacity * 100) + '%</span>' + '</label>';
	ui += 			'<div id="halo-opacity-slider"></div>';
	ui += 		'</div>';					 
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Halo radius') + '</label>';
	ui += 			'<input id="label-halo-radius" type="number" class="form-control" value="' + parseInt(this.halo_radius) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

TextSymbolizer.prototype.getVendorTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="label-vendor-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Maximum number of repetitions') + '</label>';
	ui += 			'<input id="label-max-iterations" type="number" class="form-control" value="' + parseInt(this.max_iterations) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Maximum label length (in pixels)') + '</label>';
	ui += 			'<input id="label-max-length" type="number" class="form-control" value="' + parseInt(this.max_length) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Minimum space surround tag') + '</label>';
	ui += 			'<input id="label-min-wrapper" type="number" class="form-control" value="' + parseInt(this.min_wrapper) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 checkbox">';
	ui += 			'<label>';
	if (this.solve_overlaps) {
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

TextSymbolizer.prototype.updatePreview = function() {
	var preview = null;
	$("#label-preview-" + this.id).empty();
	var previewElement = Snap("#label-preview-" + this.id);
	
	var f_Shadow = previewElement.filter(Snap.filter.shadow(0, 0, this.halo_color, parseFloat(this.halo_opacity)));
	
	var attributes = {
		fontSize: this.font_size, 
		fontFamily: this.font_family,
		fill: this.font_color,
		fontWeight: this.font_weight,
		fontStyle: this.font_style/*,
		filter : f_Shadow*/
	}

	preview = previewElement.text(10,20, "Text");
	preview.attr(attributes);

	if (this.rule != null) {
		//this.rule.updatePreview();
	}
};

TextSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	xml += '<TextSymbolizer>';
	xml += 	'<Label>';
	xml += 		'<ogc:PropertyName>' + this.field + '</ogc:PropertyName>';
	xml +=  '</Label>';
	xml += 	'<Font>';
	xml += 		'<CssParameter name="font-family">' + this.font_family + '</CssParameter>';
	xml += 		'<CssParameter name="font-size">' + this.font_size + '</CssParameter>';
	xml += 		'<CssParameter name="font-style">' + this.font_style + '</CssParameter>';
	xml += 	'</Font>';
	xml += 	'<LabelPlacement>';
	xml += 		'<PointPlacement>';
	xml += 			'<AnchorPoint>';
	xml += 				'<AnchorPointX>0.5</AnchorPointX>';
	xml += 				'<AnchorPointY>0.0</AnchorPointY>';
	xml += 			'</AnchorPoint>';
	xml += 		'</PointPlacement>';
	xml += 	'</LabelPlacement>';
	xml += 	'<Fill>';
	xml += 		'<CssParameter name="fill">' + this.font_color + '</CssParameter>';
	xml += 		'<CssParameter name="fill-opacity">1</CssParameter>';
	xml += 	'</Fill>';
	xml += '</TextSymbolizer>';
	
	return xml;
};

TextSymbolizer.prototype.toJSON = function(){
	
	var object = {
		id: this.id,
		type: this.type,
		name: this.name,
		field: this.field,
		font_family: this.font_family,
		font_size: this.font_size,
		font_color: this.font_color,
		font_weight: this.font_weight,
		font_style: this.font_style,
		halo_color: this.halo_color,
		halo_opacity: this.halo_opacity,
		halo_radius: this.halo_radius,
		max_iterations: this.max_iterations,
		max_length: this.max_length,
		min_wrapper: this.min_wrapper,
		solve_overlaps: this.solve_overlaps,
		order: this.order
	};
	
	return JSON.stringify(object);
};