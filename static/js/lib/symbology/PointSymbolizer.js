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
 
 
var PointSymbolizer = function(id, rule, symbologyUtils, symbolizer_object, previewUrl) {
	this.id = 'pointsymbolizer' + id;
	this.type = 'PointSymbolizer';
	this.name = 'PointSymbolizer ' + id;
	this.shape = 'circle';
	this.fill_color = "#000000";
	this.fill_opacity = 0.5;
	this.with_border = false;
	this.border_color = "#000000";
	this.border_size = 1;
	this.border_opacity = 1;
	this.border_type = "solid";
	this.rotation = 0;
	this.order = 0;
	this.size = 10;
	this.rule = rule;
	this.previewUrl = previewUrl;
	this.symbologyUtils = symbologyUtils;
	
	if (symbolizer_object) {
		this.name = symbolizer_object.name;
		this.shape = symbolizer_object.shape;
		this.fill_color = symbolizer_object.fill_color;
		this.fill_opacity = parseFloat(symbolizer_object.fill_opacity) || 0.5;
		this.with_border = symbolizer_object.with_border;
		this.border_color = symbolizer_object.border_color;
		this.border_size = parseInt(symbolizer_object.border_size);
		this.border_opacity = parseFloat(symbolizer_object.border_opacity) || 1.0;
		this.border_type = symbolizer_object.border_type;
		this.rotation = parseInt(symbolizer_object.rotation) || 0;
		this.order = parseInt(symbolizer_object.order) || 0;
		this.size = parseInt(symbolizer_object.size);
	}
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
	ui += 	'<td id="symbolizer-preview-div-' + this.id + '"></td>';	
	ui += 	'<td><a class="edit-symbolizer-link" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-edit text-primary"></i></a></td>';
	ui += 	'<td><a class="delete-symbolizer-link" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-times text-danger"></i></a></td>';
	ui += '</tr>';	
	
	return ui;
};

PointSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#graphic-tab" data-toggle="tab">' + gettext('Graphic') + '</a></li>';
	ui += '<li><a href="#fill-tab" data-toggle="tab">' + gettext('Fill') + '</a></li>';
	ui += '<li><a href="#border-tab" data-toggle="tab">' + gettext('Border') + '</a></li>';
	ui += '<li><a href="#rotation-tab" data-toggle="tab">' + gettext('Rotation') + '</a></li>';
	
	return ui;	
};

PointSymbolizer.prototype.getGraphicTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="graphic-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Select shape') + '</label>';
	ui += 			'<select id="shape" class="form-control">';
	for (var i=0; i < this.symbologyUtils.shapes.length; i++) {
		if (this.symbologyUtils.shapes[i].value == this.shape) {
			ui += '<option value="' + this.symbologyUtils.shapes[i].value + '" selected>' + this.symbologyUtils.shapes[i].title + '</option>';
		} else {
			ui += '<option value="' + this.symbologyUtils.shapes[i].value + '">' + this.symbologyUtils.shapes[i].title + '</option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Size') + '</label>';
	ui += 			'<input id="graphic-size" type="number" class="form-control" value="' + parseInt(this.size) + '">';					
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

PointSymbolizer.prototype.getFillTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane" id="fill-tab">';
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
	if (this.with_border) {
		ui += 	'<div id="border-div" style="display: block;">';
	} else {
		ui += 	'<div id="border-div" style="display: none;">';
	}
	ui += 		'<div class="row">';
	ui += 			'<div class="col-md-12 form-group">';
	ui += 				'<label>' + gettext('Border color') + '</label>';
	ui += 				'<input id="border-color-chooser" type="color" value="' + this.border_color + '" class="form-control color-chooser">';					
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 		'<div class="row">';
	ui += 			'<div class="col-md-12 form-group">';
	ui += 				'<label>' + gettext('Border size') + '</label>';
	ui += 				'<input id="border-size" type="number" class="form-control" value="' + parseInt(this.border_size) + '">';					
	ui += 			'</div>';
	ui += 		'</div>';
	ui += 		'<div class="row">';
	ui += 			'<div class="col-md-12 form-group">';
	ui += 				'<label style="display: block;">' + gettext('Border opacity') + '<span id="border-opacity-output" class="margin-l-15 gol-slider-output">' + (this.border_opacity * 100) + '%</span>' + '</label>';
	ui += 				'<div id="border-opacity-slider"></div>';
	ui += 			'</div>';					 
	ui += 		'</div>';
	ui += 		'<div class="row">';
	ui += 			'<div class="col-md-12 form-group">';
	ui += 				'<label>' + gettext('Border type') + '</label>';
	ui += 				'<select id="border-type" class="form-control">';
	ui += 					'<option value="solid">' + gettext('Solid') + '</option>';
	ui += 					'<option value="dotted">' + gettext('Dotted') + '</option>';
	ui += 					'<option value="stripped">' + gettext('Stripped') + '</option>';
	ui += 				'</select>';
	ui += 			'</div>';
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
	var sldBody = this.toSLDBody();
	var url = this.previewUrl + '&SLD_BODY=' + encodeURIComponent(sldBody);
	var ui = '<img id="symbolizer-preview-' + this.id + '" src="' + url + '" class="symbolizer-preview-' + this.id + '"></img>';
	$("#symbolizer-preview-div-" + this.id).empty();
	$("#symbolizer-preview-div-" + this.id).append(ui);
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
	xml += 		'<Opacity>1</Opacity>';
	xml += 		'<Size>' + this.size + '</Size>';
	xml += 		'<Rotation>0</Rotation>';
	xml += 	'</Graphic>';
	xml += '</PointSymbolizer>';
	
	return xml;
};

PointSymbolizer.prototype.toSLDBody = function(){
	
	var sld = '';
	sld += '<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" ';
	sld += 	'xmlns:sld=\"http://www.opengis.net/sld\"  xmlns:gml=\"http://www.opengis.net/gml\" '; 
	sld +=  'xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" ';
	sld +=  'xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">';
	sld += 	'<NamedLayer>';  
	sld +=  	'<Name>' + this.name + '</Name>';  
	sld +=      '<UserStyle>';
	sld +=          '<Name>' + this.name + '</Name>';
	sld +=          '<Title>' + this.name + '</Title>';
	sld +=          '<FeatureTypeStyle>';
	sld +=          	'<Rule>';
	sld +=          		'<Name>' + this.name + '</Name>';
	sld +=          		'<Title>' + this.name + '</Title>';
	sld += 					'<PointSymbolizer>';
	sld += 						'<Graphic>';
	sld += 							'<Mark>';
	sld += 								'<WellKnownName>' + this.shape + '</WellKnownName>';
	sld += 								'<Fill>';
	sld += 									'<CssParameter name="fill">' + this.fill_color + '</CssParameter>';
	sld += 									'<CssParameter name="fill-opacity">' + this.fill_opacity + '</CssParameter>';
	sld += 								'</Fill>';
	if (this.with_border) {
		sld += 							'<Stroke>';
		sld += 								'<CssParameter name="stroke">' + this.border_color + '</CssParameter>';
		sld += 								'<CssParameter name="stroke-width">' + this.border_size + '</CssParameter>';
		sld += 								'<CssParameter name="stroke-opacity">' + this.border_opacity + '</CssParameter>';
		sld += 							'</Stroke>';
	}
	sld += 							'</Mark>';
	sld += 							'<Opacity>1</Opacity>';
	sld += 							'<Size>' + this.size + '</Size>';
	sld += 							'<Rotation>0</Rotation>';
	sld += 						'</Graphic>';
	sld += 					'</PointSymbolizer>';
	sld +=          	'</Rule>';
	sld +=          '</FeatureTypeStyle>';
	sld +=      '</UserStyle>';
	sld += 	'</NamedLayer>';
	sld += '</StyledLayerDescriptor>';
	
	return sld;
};

PointSymbolizer.prototype.toJSON = function(){
	
	var object = {
		id: this.id,
		type: this.type,
		name: this.name,
		shape: this.shape,
		fill_color: this.fill_color,
		fill_opacity: this.fill_opacity,
		with_border: this.with_border,
		border_color: this.border_color,
		border_size: this.border_size,
		border_opacity: this.border_opacity,
		border_type: this.border_type,
		rotation: this.rotation,
		order: this.order,
		size: this.size,
	};
	
	return JSON.stringify(object);
};