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
var ShowMeasureToolbar = function(map, viewer) {

	this.map = map;
	this.viewer = viewer;

	this.id = "show-measure-toolbar";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
    button.setAttribute("style", "display: none");
	button.setAttribute("title", gettext('Herramientas de medida'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "icon-measure-length");
	button.appendChild(icon);

	this.$button = $(button);

	$('#toolbar').append(button);

    this.toolBar = new ol.control.Bar({ toggleOne: true, group:true });
	
	this.toolBar.controlArray = new Array();
	this.measureLengthControl = new MeasureLengthControl(this.map, this.toolBar);
	this.measureAreaControl = new MeasureAreaControl(this.map, this.toolBar);
	this.measureAngleControl = new MeasureAngleControl(this.map, this.toolBar);
	this.toolBar.controlArray.push(this.measureLengthControl);
	this.toolBar.controlArray.push(this.measureAreaControl);
	this.toolBar.controlArray.push(this.measureAngleControl);
	this.closeMeasureControl = new CloseMeasureControl(this.map, this.toolBar);
	
	this.toolBar.closeControl = this.closeMeasureControl;

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
ShowMeasureToolbar.prototype.active = false;

/**
 * TODO
 */
ShowMeasureToolbar.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
ShowMeasureToolbar.prototype.handler = function(e) {
	e.preventDefault();
	var self = this;
	if (this.active) {
		this.deactivate();

	} else {
		this.$button.addClass('button-active');
		this.active = true;
		this.$button.trigger('control-active', [this]);

		if (self.viewer.getActiveToolbar() != null) {
			self.viewer.getActiveToolbar().closeControl.close();
		}
		self.map.addControl(self.toolBar);
		self.viewer.setActiveToolbar(self.toolBar);

		this.deactivate();
	}
};

/**
 * TODO
 */
ShowMeasureToolbar.prototype.deactivate = function() {
	this.$button.removeClass('button-active');
	this.active = false;
};