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
 
 
var ExternalGraphicSymbolizer = function(id, rule, symbologyUtils, symbolizer_object) {
	this.id = id;
	this.type = 'ExternalGraphicSymbolizer';
	this.name = 'ExternalGraphicSymbolizer ' + id;
	this.online_resource = '';
	this.format = 'image/png';
	this.rule = rule;
	this.symbologyUtils = symbologyUtils;
	
	if (symbolizer_object) {
		this.name = symbolizer_object.name;
		this.online_resource = symbolizer_object.online_resource;
		this.format = symbolizer_object.format;
	}
};

ExternalGraphicSymbolizer.prototype.getTableUI = function() {
	var ui = '';
	ui += '<tr data-rowid="' + this.id + '">';
	ui += 	'<td>'
	ui += 		'<span class="handle"> ';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 			'<i class="fa fa-ellipsis-v"></i>';
	ui += 		'</span>';
	ui += 	'</td>';
	ui += 	'<td><span class="text-muted">' + this.name + '</span></td>';
	ui += 	'<td id="eg-preview-' + this.id + '"></td>';	
	ui += 	'<td><a class="edit-symbolizer-link" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-edit text-primary"></i></a></td>';
	ui += 	'<td><a class="delete-symbolizer-link" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-times text-danger"></i></a></td>';
	ui += '</tr>';	
	
	return ui;
};

ExternalGraphicSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#graphic-tab" data-toggle="tab">' + gettext('Graphic') + '</a></li>';
	
	return ui;	
};

ExternalGraphicSymbolizer.prototype.getGraphicTabUI = function() {
	var ui = '';
	ui += '<div class="tab-pane active" id="graphic-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Select image') + '</label>';
	ui +=			'<input id="eg-file" name="eg-file" type="file" class="file" data-show-preview="false">';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Select format') + '</label>';
	ui += 			'<select id="eg-format" class="form-control">';
	for (var i=0; i < this.symbologyUtils.external_graphic_formats.length; i++) {
		if (this.symbologyUtils.external_graphic_formats[i].value == this.format) {
			ui += '<option value="' + this.symbologyUtils.external_graphic_formats[i].value + '" selected>' + this.symbologyUtils.external_graphic_formats[i].title + '</option>';
		} else {
			ui += '<option value="' + this.symbologyUtils.external_graphic_formats[i].value + '">' + this.symbologyUtils.external_graphic_formats[i].title + '</option>';
		}
	}
	ui += 			'</select>';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	
	return ui;
};

LibrarySymbol.prototype.registerSymbolizerEvents = function() {
	var self = this;
	$("#eg-format").on('change', function(e) {
		this..format = this.value;
		this.updatePreview();	
	});
};

ExternalGraphicSymbolizer.prototype.updatePreview = function() {
	
	var preview = null;
	$("#eg-preview-" + this.id).empty();

	if (this.rule != null) {
		this.rule.updatePreview();
	}
};

ExternalGraphicSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	xml += '<PointSymbolizer>';
	xml += 	'<Graphic>';
	xml += 		'<ExternalGraphic>';
	xml += 			'<OnlineResource xlink:type="simple" xlink:href="' + this.online_resource + '" />';
	xml += 			'<Format>' + this.format + '</Format>';
	xml += 		'</ExternalGraphic>';
	xml += 	'</Graphic>';
	xml += '</PointSymbolizer>';
	
	return xml;
};

ExternalGraphicSymbolizer.prototype.toJSON = function(){
	
	var object = {
		id: this.id,
		type: this.type,
		name: this.name,
		online_resource: this.online_resource,
		format: this.format
	};
	
	return JSON.stringify(object);
};