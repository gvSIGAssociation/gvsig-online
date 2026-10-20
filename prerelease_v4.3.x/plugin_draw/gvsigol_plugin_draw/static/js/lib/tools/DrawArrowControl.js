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
var DrawArrow = function(map, drawLayer) {
	var self = this;
	this.map = map;
	this.drawLayer = drawLayer;
	this.styleName = 'arrow_style_0';
	this.style = {
		stroke_color: '#ffcc33',
		stroke_width: 2,
		//stroke_opacity: 1.0,
		stroke_dash_array: 'none'
	};
	
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

};


DrawArrow.prototype.active = false;

DrawArrow.prototype.isActive = function(e) {
	return this.active;

};

DrawArrow.prototype.activate = function(e) {
	this.active = true;
	this.map.addInteraction(this.drawInteraction);

};

DrawArrow.prototype.deactivate = function() {
	this.active = false;
	this.control.setActive(false);
	this.map.removeInteraction(this.drawInteraction);
};

DrawArrow.prototype.getStyle = function(feature) {
	var geometry = feature.getGeometry();
	var styles = [
	    // linestring
	    new ol.style.Style({
	    	stroke: new ol.style.Stroke({
	    		color: this.style.stroke_color,
	        	width: this.style.stroke_width
	      	})
	    })
	];
	
	geometry.forEachSegment(function(start, end) {
		var dx = end[0] - start[0];
	    var dy = end[1] - start[1];
	    var rotation = Math.atan2(dy, dx);
	    // arrows
	    styles.push(new ol.style.Style({
	    	geometry: new ol.geom.Point(end),
	      	image: new ol.style.Icon({
	        	src: IMG_PATH + 'arrow.png',
	        	anchor: [0.75, 0.5],
	        	rotateWithView: true,
	        	rotation: -rotation
	      	})
	    }));
	});
	
	return styles;
};

DrawArrow.prototype.setStyle = function(style, styleName) {
	this.styleName = styleName;
	this.style = style;
};

DrawArrow.prototype.hexToRgb = function(hex) {
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