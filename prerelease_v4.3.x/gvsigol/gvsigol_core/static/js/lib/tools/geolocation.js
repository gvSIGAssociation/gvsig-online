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
var geolocation = function(map) {

	this.map = map;
	
	this.id = "geolocation";
	var td = document.createElement('td');
	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Get current location'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-dot-circle-o");
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
geolocation.prototype.active = false;

/**
 * TODO
 */
geolocation.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
geolocation.prototype.handler = function(e) {
	e.preventDefault();
	var self = this;
	if (this.active) {
		this.deactivate();
		
	} else {
		this.$button.addClass('button-active');
		this.active = true;
		this.$button.trigger('control-active', [this]);
		
		var options = {
			enableHighAccuracy: true,
			timeout: 5000,
			maximumAge: 0
		};
		navigator.geolocation.getCurrentPosition(
			function(pos) {
				var crd = pos.coords;
				var transformedCoordinate = ol.proj.transform([parseFloat(crd.longitude), parseFloat(crd.latitude)], 'EPSG:4326', 'EPSG:3857');
				self.map.getView().setCenter(transformedCoordinate);
				self.map.getView().setZoom(18);
				
			}, 
			function(err) {
				console.warn('ERROR(' + err.code + '): ' + err.message);
			}, 
			options
		);
		
		this.deactivate();
	}
};

/**
 * TODO
 */
geolocation.prototype.deactivate = function() {
	this.$button.removeClass('button-active');
	this.active = false;
};