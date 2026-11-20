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
	var deleteClass = 'delete-symbolizer-link';
	if (this.rule) {
		deleteClass += '-' + this.rule.id;
	}
	ui += 	'<td><a class="edit-eg-link" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-edit text-primary"></i></a></td>';
	ui += 	'<td><a class="' + deleteClass + '" data-symbolizerid="' + this.id + '" href="javascript:void(0)"><i class="fa fa-times text-danger"></i></a></td>';
	ui += '</tr>';	
	
	return ui;
};

ExternalGraphicSymbolizer.geoserverHref = function(url) {
	if (!url) {
		return url;
	}
	if (/^(https?:|file:)/i.test(url)) {
		return url;
	}
	var mediaUrl = window.GVSIGOL_MEDIA_URL || '';
	var mediaRoot = (window.GVSIGOL_MEDIA_ROOT || '').replace(/\/$/, '');
	if (mediaUrl && mediaRoot && url.indexOf(mediaUrl) === 0) {
		return 'file://' + mediaRoot + '/' + url.substring(mediaUrl.length);
	}
	return url;
};

ExternalGraphicSymbolizer.prototype.getTabMenu = function() {
	var ui = '';
	ui += '<li class="active"><a href="#eg-size-tab" data-toggle="tab">' + gettext('Size') + '</a></li>';
	return ui;
};

ExternalGraphicSymbolizer.prototype.getSizeTabUI = function() {
	var size = parseInt(this.size, 10);
	if (isNaN(size) || size < 1) {
		size = 1;
	}
	var ui = '';
	ui += '<div class="tab-pane active" id="eg-size-tab">';
	ui += 	'<div class="row">';
	ui += 		'<div class="col-md-12 form-group">';
	ui += 			'<label>' + gettext('Size') + '</label>';
	ui += 			'<input id="eg-size" type="number" min="1" class="form-control" value="' + size + '">';
	ui += 		'</div>';
	ui += 	'</div>';
	ui += '</div>';
	return ui;
};

ExternalGraphicSymbolizer.prototype.registerEvents = function() {
	var self = this;
	$('#eg-size').on('change', function() {
		var size = parseInt(this.value, 10);
		if (isNaN(size) || size < 1) {
			size = 1;
			this.value = size;
		}
		self.size = size;
		self.updatePreview();
		if (self.rule && typeof self.rule.preview === 'function') {
			self.rule.preview();
		}
	});
};

ExternalGraphicSymbolizer.prototype.updatePreview = function() {
	var size = parseInt(this.size, 10);
	if (isNaN(size) || size < 1) {
		size = this.size;
	}
	var preview = document.getElementById('eg-preview-' + this.id);
	if (!preview) {
		return;
	}
	preview.style.height = size + 'px';
	if (this.online_resource) {
		preview.src = this.online_resource;
	}
};

ExternalGraphicSymbolizer.prototype.toXML = function(){
	var href = ExternalGraphicSymbolizer.geoserverHref(this.online_resource);
	href = String(href).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');

	var xml = '';
	xml += '<PointSymbolizer>';
	xml += 	'<Graphic>';
	xml += 		'<ExternalGraphic>';
	xml += 			'<OnlineResource xlink:type="simple" xlink:href="' + href + '" />';
	xml += 			'<Format>' + this.format + '</Format>';
	xml += 		'</ExternalGraphic>';
	xml += 		'<Size>' + this.size + '</Size>';
	xml += 		'<Rotation>' + this.rotation + '</Rotation>';
	xml += 		'<Opacity>' + this.opacity + '</Opacity>';
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