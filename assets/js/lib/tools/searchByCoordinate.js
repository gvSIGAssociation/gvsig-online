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


/**
 * TODO
 */
var searchByCoordinate = function(conf, map) {

	this.map = map;
	this.conf = conf;
	
	this.id = "search-by-coordinate";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Search by coordinate'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-map-marker");
	button.appendChild(icon);
	
	this.$button = $(button);
	
	$('#toolbar').append(button);

	var this_ = this;
  
	var handler = function(e) {
		this_.handler(e);
	};

	button.addEventListener('click', handler, false);
	button.addEventListener('touchstart', handler, false);

};

/**
 * TODO
 */
searchByCoordinate.prototype.active = false;

/**
 * TODO
 */
searchByCoordinate.prototype.deactivable = false;

/**
 * TODO
 */
searchByCoordinate.prototype.mapCoordinates = null;

/**
 * TODO
 */
searchByCoordinate.prototype.popup = null;


/**
 * @param {Event} e Browser event.
 */
searchByCoordinate.prototype.handler = function(e) {
	e.preventDefault();
	
	var body = '';
	body += '<div class="row">';
	body += 	'<div class="col-xs-12 form-group">';	
	body += 	'<label>' + gettext('Select projection') + '</label>';
	body += 	'<select id="projection-select" class="form-control">';
	body += 		'<option value="EPSG:4326" selected>WGS84 (EPSG:4326)</option>';
	for (var key in this.conf.supported_crs) {
		if (this.conf.supported_crs[key].code != 'EPSG:4326') {
			body += '<option value="' + this.conf.supported_crs[key].code + '">' + this.conf.supported_crs[key].title + ' (' + this.conf.supported_crs[key].code + ')' + '</option>';
		}
	}
	body += 	'</select>';
	body += 	'</div>';
	body += '</div>';
	body += '<div class="row">';
	body += 	'<div class="col-xs-6 form-group">';
	body += 		'<label for="latitude">' + gettext('Latitude') + '</label>';
	body += 		'<input placeholder="' + gettext('Latitude') + '" name="latitude" id="latitude" type="text" class="form-control">';					
	body += 	'</div>';
	body += 	'<div class="col-xs-6 form-group">';
	body += 		'<label for="longitude">' + gettext('Longitude') + '</label>';
	body += 		'<input placeholder="' + gettext('Longitude') + '" name="longitude" id="longitude" type="text" class="form-control">';					
	body += 	'</div>';
	body += '</div>';
	
	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').append(body);
	
	var buttons = '';
	buttons += '<button id="float-modal-cancel-coord" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Cancel') + '</button>';
	buttons += '<button id="float-modal-accept-coord" type="button" class="btn btn-primary">' + gettext('Find') + '</button>';
	
	$('#float-modal .modal-footer').empty();
	$('#float-modal .modal-footer').append(buttons);
	
	$("#float-modal").modal('show');
	
	var self = this;	
	$('#float-modal-accept-coord').on('click', function () {
		var projection = $('option:selected', $('#projection-select')).val();
		var latitude = $('#latitude').val();
		var longitude = $('#longitude').val();
		
		var coordinate = ol.proj.transform([parseFloat(longitude), parseFloat(latitude)], projection, 'EPSG:3857');	
		
		var popup = new ol.Overlay.Popup();
		self.map.addOverlay(popup);
		
		var popupContent = '';
		popupContent += '<p>' + projection + '</p>';
		popupContent += '<code>' + gettext('Latitude') + ': ' + latitude + ', ' + gettext('Longitude') + ': ' + longitude + '</code>';
		
		popup.show(coordinate, '<div class="popup-wrapper">' + popupContent + '</div>');
		
		self.map.getView().setCenter(coordinate);
		self.map.getView().setZoom(12);
		
		$('#float-modal').modal('hide');
		self.deactivate();
	});
};

/**
 * TODO
 */
searchByCoordinate.prototype.deactivate = function() {			
	this.$button.removeClass('button-active');
	this.active = false;
};