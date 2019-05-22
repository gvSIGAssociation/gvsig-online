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


/**
 * TODO
 */
var coordinateCalculator = function(conf, map) {

	this.map = map;
	this.conf = conf;
	
	this.id = "coordinate-calculator";

	var td = document.createElement('td');
	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Coordinate calculator'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-calculator");
	button.appendChild(icon);
	td.appendChild(button);
	
	this.$button = $(button);
	
	document.getElementById('mouse-position').children[0].children[0].appendChild(td);

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
coordinateCalculator.prototype.active = false;

/**
 * TODO
 */
coordinateCalculator.prototype.deactivable = false;

/**
 * TODO
 */
coordinateCalculator.prototype.mapCoordinates = null;

/**
 * TODO
 */
coordinateCalculator.prototype.popup = null;


/**
 * @param {Event} e Browser event.
 */
coordinateCalculator.prototype.handler = function(e) {
	var self = this;
	e.preventDefault();
	
	var ui = '';
	ui += '<div class="row">';
	ui += 	'<div class="col-md-12 form-group">';	
	ui += 	'<label>' + gettext('Origin coordinates') + '</label>';
	ui += 	'<select id="origin-coordinate-system" class="form-control">';
	ui += 		'<option value="EPSG:4326" selected>WGS84 (EPSG:4326)</option>';
	ui += 		'<option value="degrees">' + gettext('Degrees, minutes, seconds') + '</option>';
	for (var key in this.conf.supported_crs) {
		if (this.conf.supported_crs[key].code != 'EPSG:4326') {
			ui += '<option value="' + this.conf.supported_crs[key].code + '">' + this.conf.supported_crs[key].title + ' (' + this.conf.supported_crs[key].code + ')' + '</option>';
		}
	}
	ui += 	'</select>';
	ui += 	'</div>';
	ui += '</div>';
	ui += '<div id="origin-inputs" class="row">';
	ui += 	'<div class="col-md-6 form-group">';
	ui += 		'<label for="origin-longitude">' + gettext('Longitude') + '/X</label>';
	ui += 		'<input placeholder="" name="origin-longitude" id="origin-longitude" type="text" class="form-control">';					
	ui += 	'</div>';
	ui += 	'<div class="col-md-6 form-group">';
	ui += 		'<label for="origin-latitude">' + gettext('Latitude') + '/Y</label>';
	ui += 		'<input placeholder="" name="origin-latitude" id="origin-latitude" type="text" class="form-control">';					
	ui += 	'</div>';
	ui += '</div>';
	
	ui += '<div class="row">';
	ui += 	'<div class="col-md-12 form-group">';	
	ui += 	'<label>' + gettext('Destination coordinates') + '</label>';
	ui += 	'<select id="destination-coordinate-system" class="form-control">';
	ui += 		'<option value="EPSG:4326">WGS84 (EPSG:4326)</option>';
	ui += 		'<option value="degrees" selected>' + gettext('Degrees, minutes, seconds') + '</option>';
	for (var key in this.conf.supported_crs) {
		if (this.conf.supported_crs[key].code != 'EPSG:4326') {
			ui += '<option value="' + this.conf.supported_crs[key].code + '">' + this.conf.supported_crs[key].title + ' (' + this.conf.supported_crs[key].code + ')' + '</option>';
		}
	}
	ui += 	'</select>';
	ui += 	'</div>';
	ui += '</div>';
	ui += '<div id="destination-inputs" class="row">';
	ui += 	'<div class="col-md-3 form-group">';
	ui += 		'<label for="destination-degrees">' + gettext('Degrees') + '</label>';
	ui += 		'<input placeholder="" name="destination-degrees" id="destination-degrees" type="text" class="form-control">';					
	ui += 	'</div>';
	ui += 	'<div class="col-md-3 form-group">';
	ui += 		'<label for="destination-minutes">' + gettext('Minutes') + '</label>';
	ui += 		'<input placeholder="" name="destination-minutes" id="destination-minutes" type="text" class="form-control">';					
	ui += 	'</div>';
	ui += 	'<div class="col-md-3 form-group">';
	ui += 		'<label for="destination-seconds">' + gettext('Seconds') + '</label>';
	ui += 		'<input placeholder="" name="destination-seconds" id="destination-seconds" type="text" class="form-control">';					
	ui += 	'</div>';
	ui += '</div>';
	
	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').append(ui);
	
	var buttons = '';
	buttons += '<button id="float-modal-cancel-coordcalc" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Cancel') + '</button>';
	buttons += '<button id="float-modal-accept-coordcalc" type="button" class="btn btn-default">' + gettext('Calculate') + '</button>';
	
	$('#float-modal .modal-footer').empty();
	$('#float-modal .modal-footer').append(buttons);
	
	$("#float-modal").modal('show');	
	
	$("#origin-coordinate-system").on('change', function(){
		var selected = $('option:selected', $(this)).val();
		
		var ui = '';
		if (selected != 'degrees') {
			ui += '<div class="col-md-6 form-group">';
			ui += 	'<label for="origin-longitude">' + gettext('Longitude') + '/X</label>';
			ui += 	'<input placeholder="" name="origin-longitude" id="origin-longitude" type="text" class="form-control">';					
			ui += '</div>';
			ui += '<div class="col-md-6 form-group">';
			ui += 	'<label for="origin-latitude">' + gettext('Latitude') + '/Y</label>';
			ui += 	'<input placeholder="" name="origin-latitude" id="origin-latitude" type="text" class="form-control">';					
			ui += '</div>';
		} else {
			ui += '<div class="col-md-3 form-group">';
			ui += 	'<label for="origin-degrees">' + gettext('Degrees') + '/X</label>';
			ui += 	'<input placeholder="" name="origin-degrees" id="origin-degrees" type="text" class="form-control">';					
			ui += '</div>';
			ui += '<div class="col-md-3 form-group">';
			ui += 	'<label for="origin-minutes">' + gettext('Minutes') + '/Y</label>';
			ui += 	'<input placeholder="" name="origin-minutes" id="origin-minutes" type="text" class="form-control">';					
			ui += '</div>';
			ui += '<div class="col-md-3 form-group">';
			ui += 	'<label for="origin-seconds">' + gettext('Seconds') + '/Y</label>';
			ui += 	'<input placeholder="" name="origin-seconds" id="origin-seconds" type="text" class="form-control">';					
			ui += '</div>';
			
		}
		
		$('#origin-inputs').empty();
		$('#origin-inputs').append(ui);
	});
	
	$("#destination-coordinate-system").on('change', function(){
		var selected = $('option:selected', $(this)).val();
		
		var ui = '';
		if (selected != 'degrees') {
			ui += '<div class="col-md-6 form-group">';
			ui += 	'<label for="destination-longitude">' + gettext('Longitude') + '/X</label>';
			ui += 	'<input placeholder="" name="destination-longitude" id="destination-longitude" type="text" class="form-control">';					
			ui += '</div>';
			ui += '<div class="col-md-6 form-group">';
			ui += 	'<label for="destination-latitude">' + gettext('Latitude') + '/Y</label>';
			ui += 	'<input placeholder="" name="destination-latitude" id="destination-latitude" type="text" class="form-control">';					
			ui += '</div>';
			
		} else {
			ui += '<div class="col-md-3 form-group">';
			ui += 	'<label for="destination-degrees">' + gettext('Degrees') + '</label>';
			ui += 	'<input placeholder="" name="destination-degrees" id="destination-degrees" type="text" class="form-control">';					
			ui += '</div>';
			ui += '<div class="col-md-3 form-group">';
			ui += 	'<label for="destination-minutes">' + gettext('Minutes') + '</label>';
			ui += 	'<input placeholder="" name="destination-minutes" id="destination-minutes" type="text" class="form-control">';					
			ui += '</div>';
			ui += '<div class="col-md-3 form-group">';
			ui += 	'<label for="destination-seconds">' + gettext('Seconds') + '</label>';
			ui += 	'<input placeholder="" name="destination-seconds" id="destination-seconds" type="text" class="form-control">';					
			ui += '</div>';
		}
		
		$('#destination-inputs').empty();
		$('#destination-inputs').append(ui);
	});
	
	$('#float-modal-accept-coord').on('click', function () {
		var projection = $('option:selected', $('#projection-select')).val();
		var latitude = $('#latitude').val();
		var longitude = $('#longitude').val();
		
		var coordinate = ol.proj.transform([parseFloat(longitude), parseFloat(latitude)], projection, 'EPSG:3857');	
		
		var popup = new ol.Overlay.Popup();
		self.map.addOverlay(popup);
		
		var popupContent = '';
		popupContent += '<p style="font-weight:bold">' + projection + '</p>';
		popupContent += '<code>' + gettext('Longitude') + ' - X: ' + longitude + '<br />' + gettext('Latitude') + ' - Y: ' + latitude + '</code>';
		
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
coordinateCalculator.prototype.deactivate = function() {			
	this.$button.removeClass('button-active');
	this.active = false;
};