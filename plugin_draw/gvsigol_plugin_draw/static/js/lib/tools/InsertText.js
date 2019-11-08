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
var InsertText = function(map, drawLayer) {
	this.map = map;
	this.drawLayer = drawLayer;
	this.styleName = 'style_0';
	this.style = {};
	
	this.drawInteraction = new ol.interaction.Draw({
		source: this.drawLayer.getSource(),
		type: 'LineString'
	});

};


InsertText.prototype.active = false;

InsertText.prototype.isActive = function(e) {
	return this.active;

};

InsertText.prototype.activate = function(e) {
	this.active = true;
	this.map.addInteraction(this.drawInteraction);

};

InsertText.prototype.deactivate = function() {
	this.active = false;
	this.map.removeInteraction(this.drawInteraction);
};

InsertText.prototype.setStyle = function(style, styleName) {
	this.styleName = styleName;
	this.style = style;
};

InsertText.prototype.hexToRgb = function(hex) {
	// Expand shorthand form (e.g. "03F") to full form (e.g. "0033FF")
	var shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
	hex = hex.replace(shorthandRegex, function(m, r, g, b) {
		return r + r + g + g + b + b;
	});

	var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
	return result ? {
		r: parseInt(result[1], 16),
		g: parseInt(result[2], 16),
		b: parseInt(result[3], 16)
	} : null;
};