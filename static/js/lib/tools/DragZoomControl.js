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
var DragZoomControl = function(map, conf) {

	this.map = map;
	this.conf = conf;

	this.id = "drag-zoom-control";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Drag Zoom'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-search-plus");
	button.appendChild(icon);

	this.$button = $(button);

	$('.ol-zoom').append(button);

	var this_ = this;

	var handler = function(e) {
		this_.handler(e);
	};

	button.addEventListener('click', handler, false);
	button.addEventListener('touchstart', handler, false);

	this.interaction = new ol.interaction.DragZoom({
		condition: ol.events.condition.always
	});

};

/**
 * TODO
 */
DragZoomControl.prototype.active = false;

/**
 * TODO
 */
DragZoomControl.prototype.deactivable = true;


/**
 * @param {Event} e Browser event.
 */
DragZoomControl.prototype.handler = function(e) {
	var self = this;
	e.preventDefault();

	if (this.active) {
		this.deactivate();

	} else {
		this.$button.addClass('button-active');
		this.active = true;
		this.$button.trigger('control-active', [this]);

		this.map.addInteraction(this.interaction);

	}
};


/**
 * TODO
 */
DragZoomControl.prototype.deactivate = function() {
	this.$button.removeClass('button-active');
	this.map.removeInteraction(this.interaction);
	this.map.un('click', this.clickHandler, this);
	this.active = false;
};