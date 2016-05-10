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
 
 
var PointSymbolizer = function(id, rule) {
	this.id = id;
	this.type = 'PointSymbolizer';
	this.name = 'PointSymbolizer ' + id;
	this.shape = 'circle';
	this.fill_color = "#000000";
	this.fill_opacity = 0.5;
	this.with_border = true;
	this.border_color = "#000000";
	this.border_size = 1;
	this.border_opacity = 1;
	this.border_type = "solid";
	this.rotation = 0;
	this.order = 0;
	this.is_vector = true;
	this.rule = rule;
};

PointSymbolizer.prototype.getTableUI = function() {
	var ui = '';
	ui += '<tr data-rowid="' + this.id + '">';
	ui += 	'<td>'
	ui += 		'<span class="handle"> ';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 		'</span>';
	ui += 	'</td>';
	ui += 	'<td><span class="text-muted">' + this.name + '</span></td>';
	ui += 	'<td id="symbolizer-preview"><svg id="symbolizer-preview-' + this.id + '" class="preview-svg"></svg></td>';	
	ui += 	'<td><a class="edit-symbolizer-link" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-edit text-primary"></i></a></td>';
	ui += 	'<td><a class="delete-symbolizer-link" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-times text-danger"></i></a></td>';
	ui += '</tr>';	
	
	return ui;
};

PointSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#fill-tab" data-toggle="tab">' + gettext('Fill') + '</a></li>';
	ui += '<li><a href="#border-tab" data-toggle="tab">' + gettext('Border') + '</a></li>';
	ui += '<li><a href="#rotation-tab" data-toggle="tab">' + gettext('Rotation') + '</a></li>';
	
	return ui;	
};

PointSymbolizer.prototype.getFillTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="fill-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Fill color') + '</label>';
	ui += 			'<input id="fill-color-chooser" type="color" value="' + this.fill_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Fill opacity') + '<span id="fill-opacity-output" class="margin-l-15 gol-slider-output">' + (this.fill_opacity * 100) + '%</span>' + '</label>';
	ui += 			'<div id="fill-opacity-slider"><div/>';
	ui += 		'</div>';				 
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

PointSymbolizer.prototype.getBorderTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="border-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 checkbox">';
	ui += 			'<label>';
	if (this.with_border) {
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
	ui += 			'<input id="border-color-chooser" type="color" value="' + this.border_color + '" class="form-control color-chooser">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Border size') + '</label>';
	ui += 			'<input id="border-size" type="number" class="form-control" value="' + parseInt(this.border_size) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Border opacity') + '<span id="border-opacity-output" class="margin-l-15 gol-slider-output">' + (this.border_opacity * 100) + '%</span>' + '</label>';
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

PointSymbolizer.prototype.getRotationTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="rotation-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label style="display: block;">' + gettext('Rotation') + '<span id="rotation-output" class="margin-l-15 gol-slider-output">' + this.rotation + 'º</span>' + '</label>';
	ui += 			'<div id="rotation-slider"><div/>';
	ui += 		'</div>';			 
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

PointSymbolizer.prototype.updatePreview = function() {
	var attributes = {
		fill: this.fill_color,
		fillOpacity: parseFloat(this.fill_opacity),
		stroke: this.border_color,
		strokeOpacity: this.border_opacity,
		strokeWidth: this.border_size
	}
	if (this.border_type == 'dotted') {
		attributes.strokeDasharray= "1 1";
	} else if (this.border_type == 'stripped') {
		attributes.strokeDasharray= "4 4";
	}
	
	var preview = null;
	$("#symbolizer-preview-" + this.id).empty();
	var previewElement = Snap("#symbolizer-preview-" + this.id);

	if (this.shape == 'circle') {
		preview = previewElement.circle(10, 10, 10);
		preview.attr(attributes);
		
	} else if (this.shape == 'square') {
		preview = previewElement.polygon(0, 0, 20, 0, 20, 20, 0, 20);
		preview.attr(attributes);
		
	} else if (this.shape == 'triangle') {
		preview = previewElement.path('M 12.462757,7.4046606 -2.6621031,7.3865562 4.9160059,-5.7029049 z');
		preview.transform( 't7,10');
		preview.attr(attributes);
		
	}  else if (this.shape == 'star') {
		preview = previewElement.path('M 7.0268739,7.8907968 2.2616542,5.5298295 -2.3847299,8.1168351 -1.6118504,2.8552628 -5.5080506,-0.76428228 -0.2651651,-1.6551455 1.9732348,-6.479153 4.4406368,-1.7681645 9.7202441,-1.13002 6.0022969,2.6723943 z');
		preview.transform( 't10,10');
		preview.attr(attributes);
		
	} else if (this.shape == 'cross') {
		preview = previewElement.path('M 7.875 0.53125 L 7.875 7.40625 L 0.59375 7.40625 L 0.59375 11.3125 L 7.875 11.3125 L 7.875 19.46875 L 11.78125 19.46875 L 11.78125 11.28125 L 19.5625 11.28125 L 19.53125 7.375 L 11.78125 7.375 L 11.78125 0.53125 L 7.875 0.53125 z');
		preview.transform( 't0,0');
		preview.attr(attributes);
		
	} else if (symbol.shape == 'x') {
		preview = previewElement.path('M 4.34375 0.90625 L 0.90625 3.5 L 6.90625 9.9375 L 0.78125 15.53125 L 3.34375 19.03125 L 9.84375 13.09375 L 15.53125 19.15625 L 19 16.5625 L 13.03125 10.1875 L 19.1875 4.5625 L 16.625 1.09375 L 10.09375 7.03125 L 4.34375 0.90625 z');
		preview.transform( 't0,0');
		preview.attr(attributes);
		
	}

	this.rule.updatePreview();
};

PointSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	xml += '<PointSymbolizer>';
	xml += 	'<Graphic>';
	xml += 		'<Mark>';
	xml += 			'<WellKnownName>' + this.shape + '</WellKnownName>';
	xml += 			'<Fill>';
	xml += 				'<CssParameter name="fill">' + this.fill_color + '</CssParameter>';
	xml += 				'<CssParameter name="fill-opacity">' + this.fill_opacity + '</CssParameter>';
	xml += 			'</Fill>';
	xml += 			'<Stroke>';
	xml += 				'<CssParameter name="stroke">' + this.border_color + '</CssParameter>';
	xml += 				'<CssParameter name="stroke-width">' + this.border_size + '</CssParameter>';
	xml += 				'<CssParameter name="stroke-opacity">' + this.border_opacity + '</CssParameter>';
	xml += 			'</Stroke>';
	xml += 		'</Mark>';
	xml += 	'</Graphic>';
	xml += '</PointSymbolizer>';
	
	return xml;
};