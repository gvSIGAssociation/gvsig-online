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
 
 
var ExternalGraphicSymbolizer = function(name, format, online_resource) {
	this.type = 'ExternalGraphicSymbolizer';
	this.name = name;
	this.online_resource = online_resource;
	this.format = format;
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
		type: this.type,
		name: this.name,
		online_resource: this.online_resource,
		format: this.format
	};
	
	return JSON.stringify(object);
};