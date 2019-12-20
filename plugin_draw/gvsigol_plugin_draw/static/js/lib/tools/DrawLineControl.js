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
var DrawLineControl = function(drawBar, map, styleSettings) {
	var self = this;
	this.map = map;
	this.drawBar = drawBar;
	this.styleName = 'line_style_0';
	this.style = {
		stroke_color: '#f15511',
		stroke_width: 2,
		stroke_dash_array: 'none'
	};
	
	this.source = new ol.source.Vector();
	this.drawLayer = new ol.layer.Vector({
		source: this.source
	});
	this.drawLayer.setZIndex(99999999);
	this.drawLayer.printable = true;
	this.drawLayer.drawType = 'line';
	map.addLayer(this.drawLayer);
	
	this.drawLayer.drawStyleSettings = styleSettings;
	
	this.drawInteraction = new ol.interaction.Draw({
		source: this.drawLayer.getSource(),
		type: 'LineString'
	});

	this.drawInteraction.on('drawend',
		function(evt) {
			var drawed = evt.feature;
			drawed.setProperties({'style_name': this.styleName});
			var style = self.getStyle(drawed);
			drawed.setStyle(style);
			
		}, this);
	
	this.control = new ol.control.Toggle({	
		html: '<i class="fa fa-code-fork" ></i>',
		className: "edit",
		title: gettext('Draw line'),
		interaction: this.drawInteraction,
		onToggle: function(active){
			if (active) {
				viewer.core.disableTools(this);
				self.activate();
			} else {
				self.deactivate();
			}
		}
	});
	this.drawBar.addControl(this.control);

};


DrawLineControl.prototype.active = false;

DrawLineControl.prototype.isActive = function(e) {
	return this.active;

};

DrawLineControl.prototype.activate = function(e) {
	this.active = true;
	this.map.addInteraction(this.drawInteraction);

};

DrawLineControl.prototype.deactivate = function() {
	this.active = false;
	this.control.setActive(false);
	this.map.removeInteraction(this.drawInteraction);
};

DrawLineControl.prototype.getStyle = function(feature) {
	var style = new ol.style.Style({
    	stroke: new ol.style.Stroke({
        	color: this.style.stroke_color,
        	width: this.style.stroke_width
      	})
    });
	
	return style;
};

DrawLineControl.prototype.setStyle = function(style, styleName) {
	this.styleName = styleName;
	this.style = style;
};

DrawLineControl.prototype.hexToRgb = function(hex) {
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

DrawLineControl.prototype.getLayer = function() {
	return this.drawLayer;
};