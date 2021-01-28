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
	ui += 	'<div id="calc-errors" class="col-md-12 form-group" style="color: red;">';
	ui += 	'</div>';
	ui += '</div>'
	ui += '<div class="row">';
	ui += 	'<div class="col-md-9 form-group">';	
	ui += 		'<label>' + gettext('Origin coordinates') + '</label>';
	ui += 		'<select id="origin-coordinate-system" class="form-control">';
	ui += 			'<option value="" selected disabled>' + gettext('Select reference system') + '</option>';
	for (var key in this.conf.supported_crs) {
		ui += '<option data-units="' + this.conf.supported_crs[key].units + '" value="' + this.conf.supported_crs[key].code + '">' + this.conf.supported_crs[key].title + ' (' + this.conf.supported_crs[key].code + ')' + '</option>';
	}
	ui += 		'</select>';
	ui += 	'</div>';
	ui += 	'<div class="col-md-3 form-group">';	
	ui += 		'<label>' + gettext('Format') + '</label>';
	ui += 		'<select id="origin-format" class="form-control">';
	ui += 		'</select>';
	ui += 	'</div>';
	ui += '</div>';
	ui += '<div id="origin-inputs" class="row">';
	ui += '</div>';
	
	ui += '<div class="row">';
	ui += 	'<div class="col-md-9 form-group">';	
	ui += 		'<label>' + gettext('Destination coordinates') + '</label>';
	ui += 		'<select id="destination-coordinate-system" class="form-control">';
	ui += 			'<option value="" selected disabled>' + gettext('Select reference system') + '</option>';
	for (var key in this.conf.supported_crs) {
		ui += '<option data-units="' + this.conf.supported_crs[key].units + '" value="' + this.conf.supported_crs[key].code + '">' + this.conf.supported_crs[key].title + ' (' + this.conf.supported_crs[key].code + ')' + '</option>';
	}
	ui += 		'</select>';
	ui += 	'</div>';
	ui += 	'<div class="col-md-3 form-group">';	
	ui += 		'<label>' + gettext('Format') + '</label>';
	ui += 		'<select id="destination-format" class="form-control">';
	ui += 		'</select>';
	ui += 	'</div>';
	ui += '</div>';
	ui += '<div id="destination-inputs" class="row">';
	ui += '</div>';
	
	$('#float-modal .modal-body').empty();
	$('#float-modal .modal-body').append(ui);
	
	var buttons = '';
	buttons += '<button id="float-modal-cancel-coordcalc" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Cancel') + '</button>';
	buttons += '<button id="float-modal-accept-coordcalc" type="button" class="btn btn-default">' + gettext('Calculate') + '</button>';
	
	$('#float-modal .modal-footer').empty();
	$('#float-modal .modal-footer').append(buttons);
	
	$("#float-modal").modal('show');	
	
	$("#float-modal-accept-coordcalc").on('click', function(){
		self.calculate();
	});
	
	$("#origin-coordinate-system").on('change', function(){
		$('#origin-inputs').empty();
		
		var refSystem = $('option:selected', $(this)).val();
		var units = $('option:selected', $(this)).data('units');
		
		$('#origin-format').empty();
		if (units == 'degrees') {
			$('#origin-format').append($('<option>', {value: '', text: gettext('Select format'), selected: true, disabled: true}));
			$('#origin-format').append($('<option>', {value: 'GG', text: gettext('Decimal degrees'), selected: false}));
			$('#origin-format').append($('<option>', {value: 'DMS', text: gettext('Degrees, minutes and seconds'), selected: false}));
			
		} else if (units == 'meters'){
			$('#origin-format').append($('<option>', {value: '', text: gettext('Select format'), selected: true, disabled: true}));
			$('#origin-format').append($('<option>', {value: 'XY', text: gettext('X/Y'), selected: false}));
		}
	});
	
	$("#origin-format").on('change', function(){
		var format = $('option:selected', $(this)).val();
		
		var ui = '';
		if (format == 'DMS') {
			ui += '<div class="row">';
			ui += 	'<div class="col-md-2 form-group" style="padding: 20px; margin-left: 20px; font-weight: bold;">';
			ui += 		'<span style="margin-left:20px;">' + gettext('Longitude') + '</span>';
			ui += 	'</div>';
			ui += 	'<div class="col-md-3 form-group">';
			ui += 		'<label for="origin-lon-degrees">' + gettext('Degrees') + '</label>';
			ui += 		'<input placeholder="" name="origin-lon-degrees" id="origin-lon-degrees" type="number" step="0.1" class="form-control">';					
			ui += 	'</div>';
			ui += 	'<div class="col-md-3 form-group">';
			ui += 		'<label for="origin-lon-minutes">' + gettext('Minutes') + '</label>';
			ui += 		'<input placeholder="" name="origin-lon-minutes" id="origin-lon-minutes" type="number" step="0.1" class="form-control">';					
			ui += 	'</div>';
			ui += 	'<div class="col-md-3 form-group">';
			ui += 		'<label for="origin-lon-seconds">' + gettext('Seconds') + '</label>';
			ui += 		'<input placeholder="" name="origin-lon-seconds" id="origin-lon-seconds" type="number" step="0.1" class="form-control">';					
			ui += 	'</div>';
			//ui += 	'<div class="col-md-3 form-group">';
			//ui += 		'<label>(180E 180W)</label>';
			//ui += 		'<select id="origin-ew" class="form-control">';
			//ui += 			'<option value="origin-east" selected>' + gettext('EAST') + '</option>';
			//ui += 			'<option value="origin-west" selected>' + gettext('WEST') + '</option>';
			//ui += 		'</select>';
			//ui += 	'</div>';
			ui += '</div>';
			ui += '<div class="row">';
			ui += 	'<div class="col-md-2 form-group" style="padding: 20px; margin-left: 20px; font-weight: bold;">';
			ui += 		'<span style="margin-left:20px;">' + gettext('Latitude') + '</span>';
			ui += 	'</div>';
			ui += 	'<div class="col-md-3 form-group">';
			ui += 		'<label for="origin-lat-degrees">' + gettext('Degrees') + '</label>';
			ui += 		'<input placeholder="" name="origin-lat-degrees" id="origin-lat-degrees" type="number" step="0.1" class="form-control">';					
			ui += 	'</div>';
			ui += 	'<div class="col-md-3 form-group">';
			ui += 		'<label for="origin-lat-minutes">' + gettext('Minutes') + '</label>';
			ui += 		'<input placeholder="" name="origin-lat-minutes" id="origin-lat-minutes" type="number" step="0.1" class="form-control">';					
			ui += 	'</div>';
			ui += 	'<div class="col-md-3 form-group">';
			ui += 		'<label for="origin-lat-seconds">' + gettext('Seconds') + '</label>';
			ui += 		'<input placeholder="" name="origin-lat-seconds" id="origin-lat-seconds" type="number" step="0.1" class="form-control">';					
			ui += 	'</div>';
			//ui += 	'<div class="col-md-3 form-group">';
			//ui += 		'<label>(90N 90S)</label>';
			//ui += 		'<select id="origin-ns" class="form-control">';
			//ui += 			'<option value="origin-north" selected>' + gettext('NORTH') + '</option>';
			//ui += 			'<option value="origin-south" selected>' + gettext('SOUTH') + '</option>';
			//ui += 		'</select>';
			//ui += 	'</div>';
			ui += '</div>';
			
		} else if (format == 'GG'){
			ui += '<div class="col-md-6 form-group">';
			ui += 	'<label for="origin-longitude">' + gettext('Longitude') + '</label>';
			ui += 	'<input placeholder="" name="origin-longitude" id="origin-longitude" type="number" step="0.1" class="form-control">';					
			ui += '</div>';
			ui += '<div class="col-md-6 form-group">';
			ui += 	'<label for="origin-latitude">' + gettext('Latitude') + '</label>';
			ui += 	'<input placeholder="" name="origin-latitude" id="origin-latitude" type="number" step="0.1" class="form-control">';					
			ui += '</div>';
			
		} else if (format == 'XY'){
			ui += '<div class="col-md-6 form-group">';
			ui += 	'<label for="origin-x">X</label>';
			ui += 	'<input placeholder="" name="origin-x" id="origin-x" type="number" step="0.1" class="form-control">';					
			ui += '</div>';
			ui += '<div class="col-md-6 form-group">';
			ui += 	'<label for="origin-y">Y</label>';
			ui += 	'<input placeholder="" name="origin-y" id="origin-y" type="number" step="0.1" class="form-control">';					
			ui += '</div>';
			
		}
		
		$('#origin-inputs').empty();
		$('#origin-inputs').append(ui);
	});
	
	$("#destination-format").on('change', function(){
		var format = $('option:selected', $(this)).val();
		
		var ui = '';
		if (format == 'DMS') {
			ui += '<div class="row">';
			ui += 	'<div class="col-md-2 form-group" style="padding: 20px; margin-left: 20px; font-weight: bold;">';
			ui += 		'<span style="margin-left:20px;">' + gettext('Longitude') + '</span>';
			ui += 	'</div>';
			ui += 	'<div class="col-md-3 form-group">';
			ui += 		'<label for="destination-lon-degrees">' + gettext('Degrees') + '</label>';
			ui += 		'<input readonly placeholder="" name="destination-lon-degrees" id="destination-lon-degrees" type="number" step="0.1" class="form-control">';					
			ui += 	'</div>';
			ui += 	'<div class="col-md-3 form-group">';
			ui += 		'<label for="destination-lon-minutes">' + gettext('Minutes') + '</label>';
			ui += 		'<input readonly placeholder="" name="destination-lon-minutes" id="destination-lon-minutes" type="number" step="0.1" class="form-control">';					
			ui += 	'</div>';
			ui += 	'<div class="col-md-3 form-group">';
			ui += 		'<label for="destination-lon-seconds">' + gettext('Seconds') + '</label>';
			ui += 		'<input readonly placeholder="" name="destination-lon-seconds" id="destination-lon-seconds" type="number" step="0.1" class="form-control">';					
			ui += 	'</div>';
			//ui += 	'<div class="col-md-3 form-group">';
			//ui += 		'<label>(180E 180W)</label>';
			//ui += 		'<select id="destination-ew" class="form-control">';
			//ui += 			'<option value="destination-east" selected>' + gettext('EAST') + '</option>';
			//ui += 			'<option value="destination-west" selected>' + gettext('WEST') + '</option>';
			//ui += 		'</select>';
			//ui += 	'</div>';
			ui += '</div>';
			ui += '<div class="row">';
			ui += 	'<div class="col-md-2 form-group" style="padding: 20px; margin-left: 20px; font-weight: bold;">';
			ui += 		'<span style="margin-left:20px;">' + gettext('Latitude') + '</span>';
			ui += 	'</div>';
			ui += 	'<div class="col-md-3 form-group">';
			ui += 		'<label for="destination-lat-degrees">' + gettext('Degrees') + '</label>';
			ui += 		'<input readonly placeholder="" name="destination-lat-degrees" id="destination-lat-degrees" type="number" step="0.1" class="form-control">';					
			ui += 	'</div>';
			ui += 	'<div class="col-md-3 form-group">';
			ui += 		'<label for="destination-lat-minutes">' + gettext('Minutes') + '</label>';
			ui += 		'<input readonly placeholder="" name="destination-lat-minutes" id="destination-lat-minutes" type="number" step="0.1" class="form-control">';					
			ui += 	'</div>';
			ui += 	'<div class="col-md-3 form-group">';
			ui += 		'<label for="destination-lat-seconds">' + gettext('Seconds') + '</label>';
			ui += 		'<input readonly placeholder="" name="destination-lat-seconds" id="destination-lat-seconds" type="number" step="0.1" class="form-control">';					
			ui += 	'</div>';
			//ui += 	'<div class="col-md-3 form-group">';
			//ui += 		'<label>(90N 90S)</label>';
			//ui += 		'<select id="destination-ns" class="form-control">';
			//ui += 			'<option value="destination-north" selected>' + gettext('NORTH') + '</option>';
			//ui += 			'<option value="destination-south" selected>' + gettext('SOUTH') + '</option>';
			//ui += 		'</select>';
			//ui += 	'</div>';
			ui += '</div>';
			
		} else if (format == 'GG'){
			ui += '<div class="col-md-6 form-group">';
			ui += 	'<label for="destination-longitude">' + gettext('Longitude') + '</label>';
			ui += 	'<input readonly placeholder="" name="destination-longitude" id="destination-longitude" type="number" step="0.1" class="form-control">';					
			ui += '</div>';
			ui += '<div class="col-md-6 form-group">';
			ui += 	'<label for="destination-latitude">' + gettext('Latitude') + '</label>';
			ui += 	'<input readonly placeholder="" name="destination-latitude" id="destination-latitude" type="number" step="0.1" class="form-control">';					
			ui += '</div>';
			
		} else if (format == 'XY'){
			ui += '<div class="col-md-6 form-group">';
			ui += 	'<label for="destination-x">X</label>';
			ui += 	'<input readonly placeholder="" name="destination-x" id="destination-x" type="number" step="0.1" class="form-control">';					
			ui += '</div>';
			ui += '<div class="col-md-6 form-group">';
			ui += 	'<label for="destination-y">Y</label>';
			ui += 	'<input readonly placeholder="" name="destination-y" id="destination-y" type="number" step="0.1" class="form-control">';					
			ui += '</div>';
			
		}
		
		$('#destination-inputs').empty();
		$('#destination-inputs').append(ui);
	});
	
	$("#destination-coordinate-system").on('change', function(){
		$('#destination-inputs').empty();
		
		var refSystem = $('option:selected', $(this)).val();
		var units = $('option:selected', $(this)).data('units');
		
		$('#destination-format').empty();
		if (units == 'degrees') {
			$('#destination-format').append($('<option>', {value: '', text: gettext('Select format'), selected: true, disabled: true}));
			$('#destination-format').append($('<option>', {value: 'GG', text: gettext('Decimal degrees'), selected: false}));
			//$('#destination-format').append($('<option>', {value: 'DMS', text: gettext('Degrees, minutes and seconds'), selected: false}));
			
		} else if (units == 'meters'){
			$('#destination-format').append($('<option>', {value: '', text: gettext('Select format'), selected: true, disabled: true}));
			$('#destination-format').append($('<option>', {value: 'XY', text: gettext('X/Y'), selected: false}));
		}
	});

};

/**
 * TODO
 */
coordinateCalculator.prototype.calculate = function() {
	var originRefSystem = $('option:selected', $('#origin-coordinate-system')).val();
	var destinationRefSystem = $('option:selected', $('#destination-coordinate-system')).val();
	var originFormat = $('option:selected', $('#origin-format')).val();
	var destinationFormat = $('option:selected', $('#destination-format')).val();
	
	var originCoords = null;
	if (originFormat == 'DMS') {
		var lonDegrees = $('#origin-lon-degrees').val();
		var lonMinutes = $('#origin-lon-minutes').val();
		var lonSeconds = $('#origin-lon-seconds').val();
		var latDegrees = $('#origin-lat-degrees').val();
		var latMinutes = $('#origin-lat-minutes').val();
		var latSeconds = $('#origin-lat-seconds').val();
		
		if (lonDegrees == "" || lonMinutes == "" || lonSeconds == "" || latDegrees == "" || latMinutes == "" || latSeconds == "") {
			$('#calc-errors').append('<span>* ' + gettext('You must fill in all the values') + '</span><br />');
			
		} else {
			if (!this.inRange(Math.abs(lonDegrees), 0, 180) || 
					!this.inRange(Math.abs(lonMinutes), 0, 60) || 
						!this.inRange(Math.abs(lonSeconds), 0, 60) ||
							!this.inRange(Math.abs(latDegrees), 0, 180) || 
								!this.inRange(Math.abs(latMinutes), 0, 60) || 
									!this.inRange(Math.abs(latSeconds), 0, 60)) {
				
				$('#calc-errors').append('<span>* ' + gettext('Some value is out of range') + '</span><br />');
				
			} else {
				var lon = this.getDecimalDeg(parseFloat(lonDegrees), parseFloat(lonMinutes), parseFloat(lonSeconds));
				var lat = this.getDecimalDeg(parseFloat(latDegrees), parseFloat(latMinutes), parseFloat(latSeconds));
				originCoords = [lon, lat];
			}
			
		}
		
		
	} else if (originFormat == 'GG') {
		var lon = parseFloat($('#origin-longitude').val());
		var lat = parseFloat($('#origin-latitude').val());
		originCoords = [lon, lat];
		
	} else if (originFormat == 'XY') {
		var x = parseFloat($('#origin-x').val());
		var y = parseFloat($('#origin-y').val());
		originCoords = [x, y];
	}
	
	var destinationCoords = null;
	if (originRefSystem == destinationRefSystem) {
		destinationCoords = originCoords;
	} else {
		destinationCoords = ol.proj.transform([parseFloat(originCoords[0]), parseFloat(originCoords[1])], originRefSystem, destinationRefSystem);
	}
	
	if (destinationFormat == 'DMS') {

		
	} else if (destinationFormat == 'GG') {
		$('#destination-longitude').val(destinationCoords[0]);
		$('#destination-latitude').val(destinationCoords[1]);
		
	} else if (destinationFormat == 'XY') {
		$('#destination-x').val(destinationCoords[0]);
		$('#destination-y').val(destinationCoords[1]);
	}

	var centerCoords = ol.proj.transform([parseFloat(originCoords[0]), parseFloat(originCoords[1])], originRefSystem, 'EPSG:3857');
	this.map.getView().setCenter(centerCoords);
	this.map.getView().setZoom(12);
};

coordinateCalculator.prototype.getDecimalDeg = function(deg, min, sec) {
	var aux = Math.abs(deg) + (min / 60) + (sec / 3600);
	if (deg < 0) {
		return -aux;
	} else {
		return aux;
	}
	
};

coordinateCalculator.prototype.inRange = function(value, a, b) {
    return value >= a && value <= b;
};

coordinateCalculator.prototype.getProj = function(definition) {
	var proj = null;
	var definitionArray = definition.split(' ');
	for (var i=0; i<definitionArray.length; i++) {
		if (definitionArray[i].indexOf('+proj=') != -1) {
			proj = definitionArray[i].split('=')[1];
		}
	}
	return proj;
};

coordinateCalculator.prototype.getZone = function(definition) {
	var zone = {};
	var definitionArray = definition.split(' ');
	for (var i=0; i<definitionArray.length; i++) {
		if (definitionArray[i].indexOf('+zone=') != -1) {
			zone['zone'] = definitionArray[i].split('=')[1];
		}
	}
	
	var isSouth = false;
	for (var i=0; i<definitionArray.length; i++) {
		if (definitionArray[i].indexOf('+south') != -1) {
			isSouth = true;
		}
	}
	
	if (isSouth) {
		zone['hemisphere'] = 'S';
	} else {
		zone['hemisphere'] = 'N';
	}
	return zone;
};



/**
 * TODO
 */
coordinateCalculator.prototype.deactivate = function() {			
	this.$button.removeClass('button-active');
	this.active = false;
};