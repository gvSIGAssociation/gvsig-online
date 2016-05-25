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
 
 
var LineSymbolizer = function(id, rule, symbolizer_object, previewUrl) {
	this.id = 'linesymbolizer' + id;
	this.type = 'LineSymbolizer';
	this.name = 'LineSymbolizer ' + id;
	this.fill_color = "#000000";
	this.fill_opacity = 0.5;
	this.border_color = "#000000";
	this.border_size = 1;
	this.border_opacity = 1;
	this.border_type = "solid";
	this.order = 0;
	this.rule = rule;
	this.previewUrl = previewUrl;
	
	if (symbolizer_object) {
		this.name = symbolizer_object.name;
		this.fill_color = symbolizer_object.fill_color;
		this.fill_opacity = symbolizer_object.fill_opacity;
		this.border_color = symbolizer_object.border_color;
		this.border_size = symbolizer_object.border_size;
		this.border_opacity = symbolizer_object.border_opacity;
		this.border_type = symbolizer_object.border_type;
		this.order = symbolizer_object.order;
	}
};

LineSymbolizer.prototype.getTableUI = function() {
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

LineSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#border-tab" data-toggle="tab">' + gettext('Border') + '</a></li>';
	
	return ui;	
};

LineSymbolizer.prototype.getBorderTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="border-tab">';
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

LineSymbolizer.prototype.updatePreview = function() {	
	var sldBody = this.toSLDBody();
	var url = this.previewUrl + '&SLD_BODY=' + encodeURIComponent(sldBody);
	var ui = '<img id="symbolizer-preview-' + this.id + '" src="' + url + '" class="symbolizer-preview-' + this.id + '"></img>';
	$("#symbolizer-preview-div-" + this.id).empty();
	$("#symbolizer-preview-div-" + this.id).append(ui);
};

LineSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	xml += '<LineSymbolizer>';
	xml += 	'<Stroke>';
	xml += 		'<CssParameter name="stroke">' + this.border_color + '</CssParameter>';
	xml += 		'<CssParameter name="stroke-width">' + this.border_size + '</CssParameter>';
	xml += 		'<CssParameter name="stroke-opacity">' + this.border_opacity + '</CssParameter>';
	xml += 	'</Stroke>';
	xml += '</LineSymbolizer>';
	
	return xml;
};

LineSymbolizer.prototype.toSLDBody = function(){
	
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
	sld += 					'<LineSymbolizer>';
	sld += 						'<Stroke>';
	sld += 							'<CssParameter name="stroke">' + this.border_color + '</CssParameter>';
	sld += 							'<CssParameter name="stroke-width">' + this.border_size + '</CssParameter>';
	sld += 							'<CssParameter name="stroke-opacity">' + this.border_opacity + '</CssParameter>';
	sld += 						'</Stroke>';
	sld += 					'</LineSymbolizer>';
	sld +=          	'</Rule>';
	sld +=          '</FeatureTypeStyle>';
	sld +=      '</UserStyle>';
	sld += 	'</NamedLayer>';
	sld += '</StyledLayerDescriptor>';
	
	return sld;
};

LineSymbolizer.prototype.toJSON = function(){
	
	var object = {
		id: this.id,
		type: this.type,
		name: this.name,
		fill_color: this.fill_color,
		fill_opacity: this.fill_opacity,
		border_color: this.border_color,
		border_size: this.border_size,
		border_opacity: this.border_opacity,
		border_type: this.border_type,
		order: this.order
	};
	
	return JSON.stringify(object);
};