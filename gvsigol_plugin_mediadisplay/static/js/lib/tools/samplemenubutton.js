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
 * @author: lsanjaime <lsanjaime@scolab.es>
 */

/**
 * TODO
 */
var SampleMenuButton = function(url, conf, map) {
	var self = this;
	this.url = url;
	this.conf = conf;
	this.map = map;

	this.id = "samplemenubutton";
	this.$button = $("#samplemenubutton");

	var this_ = this;
	var handler = function(e) {
		this_.handler(e);
	};

	this.$button.on('click', handler);
	this.$button.on('touchstart', handler);

};

/**
 * TODO
 */
SampleMenuButton.prototype.active = false;

/**
 * TODO
 */
SampleMenuButton.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
SampleMenuButton.prototype.handler = function(e) {
	e.preventDefault();
	var self = this;

	if (!this.active) {
		alert('Sample View');
		this.active = true;
	}
};

/**
 * TODO
 */
SampleMenuButton.prototype.deactivate = function() {
	this.$button.removeClass('button-active');
	this.active = false;
};