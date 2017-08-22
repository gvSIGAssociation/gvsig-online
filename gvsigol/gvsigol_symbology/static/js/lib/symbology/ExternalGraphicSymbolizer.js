/**
 * gvSIG Online.
 * Copyright (C) 2010-2017 SCOLAB.
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
 
 
var ExternalGraphicSymbolizer = function(name, format, size, online_resource) {
	this.id = name;
	this.type = 'ExternalGraphicSymbolizer';
	this.name = name;
	this.online_resource = online_resource;
	this.format = format;
	this.order = 0;
	this.size = size;
	this.opacity = 1;
	this.rotation = 0;
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
	ui += 	'<td id="symbolizer-preview"><img style="height: ' + this.size + 'px; width: auto;" src="' + this.online_resource + '" id="eg-preview-' + this.id + '" class="eg-preview-' + this.id + '"></img></td>';	
	ui += 	'<td><a disabled class="edit-eg-link" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-edit text-default"></i></a></td>';
	ui += 	'<td><a class="delete-symbolizer-link" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-times text-danger"></i></a></td>';
	ui += '</tr>';	
	
	return ui;
};

ExternalGraphicSymbolizer.prototype.toXML = function(){
	
	var xml = '';
	xml += '<PointSymbolizer>';
	xml += 	'<Graphic>';
	xml += 		'<ExternalGraphic>';
	xml += 			'<OnlineResource xlink:type="simple" xlink:href="' + this.online_resource + '" />';
	xml += 			'<Format>' + this.format + '</Format>';
	xml += 		'</ExternalGraphic>';
	xml += 		'<Size>' + this.size + '</Size>';
	xml += 	'</Graphic>';
	xml += '</PointSymbolizer>';
	
	return xml;
};

ExternalGraphicSymbolizer.prototype.toJSON = function(){
	
	var object = {
		type: this.type,
		name: this.name,
		online_resource: this.online_resource,
		format: this.format,
		order: this.order,
		size: this.size,
		opacity: this.opacity,
		rotation: this.rotation
	};
	
	return JSON.stringify(object);
};