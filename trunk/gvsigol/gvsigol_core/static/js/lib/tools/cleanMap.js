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
var cleanMap = function(map, viewer) {

	this.map = map;
	this.viewer = viewer;

	this.id = "clean-map";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Clean map'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-eraser");
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
cleanMap.prototype.active = false;

/**
 * TODO
 */
cleanMap.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
cleanMap.prototype.handler = function(e) {
	e.preventDefault();
	var self = this;
	if (this.active) {
		this.deactivate();

	} else {
		this.$button.addClass('button-active');
		this.active = true;
		this.$button.trigger('control-active', [this]);

		var layers = this.map.getLayers().getArray();
		for (var i=0; i<layers.length; i++) {
			if (layers[i] instanceof ol.layer.Vector) {
				layers[i].getSource().clear();
			}
		}
		this.viewer.clearAllSelectedFeatures();

		this.deactivate();
	}
};

/**
 * TODO
 */
cleanMap.prototype.deactivate = function() {
	this.$button.removeClass('button-active');
	this.active = false;
};