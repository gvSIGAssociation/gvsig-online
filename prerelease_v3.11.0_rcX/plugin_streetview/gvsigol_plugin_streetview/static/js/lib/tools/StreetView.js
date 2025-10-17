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
var StreetView = function(conf, map, apiKey) {
	this.map = map;
	this.conf = conf;
	this.apiKey = apiKey;

	this.id = "streetview";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Google Street View'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-google");
	button.appendChild(icon);

	this.$button = $(button);

	$('#toolbar').append(button);

	var this_ = this;

	var handler = function(e) {
		this_.handler(e);
	};
	
	this.createModal();

	button.addEventListener('click', handler, false);
	button.addEventListener('touchstart', handler, false);

};

/**
 * TODO
 */
StreetView.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
StreetView.prototype.handler = function(e) {
	e.preventDefault();
	if (this.active) {
		this.deactivate();

	} else {
		viewer.core.disableTools(this.id);
		
		this.$button.addClass('button-active');
		this.active = true;
		this.$button.trigger('control-active', [this]);

    	var self = this;

		this.map.on('click', this.clickHandler, self);

	}
};

/**
 * Handle pointer click.
 * @param {ol.MapBrowserEvent} evt
 */

StreetView.prototype.clickHandler = function(evt) {
	this.showStreetView(evt.coordinate);
	
};

StreetView.prototype.createModal = function() {
	var self = this; 
	
	self.modal = '';
	self.modal += '<div class="modal fade" id="modal-streetview" tabindex="-1" role="dialog" aria-labelledby="myModalLabel">';
	self.modal += 	'<div class="modal-dialog" role="document">';
	self.modal += 		'<div class="modal-content">';
	self.modal += 			'<div class="modal-header">';
	self.modal += 				'<h4 class="modal-title" id="myModalLabel">' + gettext('Google Street View') + '</h4>';
	self.modal += 			'</div>';
	self.modal += 			'<div id="modal-streetview-body" class="modal-body">';
	self.modal += 			'</div>';
	self.modal += 			'<div class="modal-footer">';
	self.modal += 				'<button id="button-streetview-close" type="button" class="btn btn-default" data-dismiss="modal">' + gettext('Close') + '</button>';
	self.modal += 			'</div>';
	self.modal += 		'</div>';
	self.modal += 	'</div>';
	self.modal += '</div>';
	$('body').append(self.modal);
};

/**
 * TODO
 */
StreetView.prototype.showStreetView = function(coords) {
	var tCoords = ol.proj.transform(coords, 'EPSG:3857', 'EPSG:4326');
	$("#modal-streetview-body").empty();
	//$("#modal-streetview-body").append('<iframe width="600" height="450" frameborder="0" style="border:0" src="https://www.google.com/maps/embed/v1/streetview?location=' + tCoords[0] + ',' + tCoords[1] + '&key=' + this.apiKey + '" allowfullscreen></iframe>');
	$("#modal-streetview-body").append('<img width="575" height="450" style="border:0" src="https://www.google.com/maps/embed/v1/streetview?location=' + tCoords[0] + ',' + tCoords[1] + '&key=' + this.apiKey + '"></img>');
	//$("#modal-streetview-body").append('<img width="575" height="450" style="border:0" src="https://www.google.com/maps/api/streetview?size=400x400&location=51.398734,-2.3936212&fov=80&heading=70&pitch=0&key=' + this.apiKey + '"></img>');
	$("#modal-streetview").modal('show');
};

/**
 * TODO
 */
StreetView.prototype.deactivate = function() {
	this.$button.removeClass('button-active');
	this.map.un('click', this.clickHandler, this);
	this.active = false;
};