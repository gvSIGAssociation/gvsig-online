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
var DrawPointControl = function(drawBar, map, styleSettings) {
	var self = this;
	this.map = map;
	this.drawBar = drawBar;
	this.styleName = 'point_style_0';
	this.style = {
		well_known_name: 'circle',
		size: 8,
		fill_color: '#f15511',
		fill_opacity: 1.0,
		stroke_color: '#f15511',
		stroke_width: 2
	};
	
	this.source = new ol.source.Vector();
	this.drawLayer = new ol.layer.Vector({
		source: this.source
	});
	this.drawLayer.setZIndex(99999999);
	this.drawLayer.printable = true;
	this.drawLayer.drawType = 'point';
	map.addLayer(this.drawLayer);
	
	this.drawLayer.drawStyleSettings = styleSettings;
	
	this.drawInteraction = new ol.interaction.Draw({
		source: this.drawLayer.getSource(),
		type: 'Point'
	});
	this.drawInteraction.on('drawend',
		function(evt) {
			var drawed = evt.feature;
			drawed.setProperties({'style_name': this.styleName});
			var style = self.getStyle(drawed);
			drawed.setStyle(style);
			
		}, this);
	
	
	this.control = new ol.control.Toggle({	
		html: '<i class="fa fa-map-marker" ></i>',
		className: "edit",
		title: gettext('Draw point'),
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

DrawPointControl.prototype.isActive = function(e) {
	return this.active;

};

DrawPointControl.prototype.activate = function(e) {
	this.active = true;
	this.map.addInteraction(this.drawInteraction);

};

DrawPointControl.prototype.deactivate = function() {
	this.active = false;
	this.control.setActive(false);
	this.map.removeInteraction(this.drawInteraction);
};

DrawPointControl.prototype.getStyle = function(feature) {
	var self = this;
	
	var fillColor = this.hexToRgb(this.style.fill_color);
	var style = new ol.style.Style({
		fill: new ol.style.Fill({
      		color: 'rgba(' + fillColor.r + ',' + fillColor.g + ',' + fillColor.b + ',' + self.style.fill_opacity + ')'
    	}),
    	stroke: new ol.style.Stroke({
      		color: self.style.stroke_color,
      		width: self.style.stroke_width
    	}),
    	image: self.getImageStyle()
    });
	
	return style;
};

DrawPointControl.prototype.setStyle = function(style, styleName) {
	this.styleName = styleName;
	this.style = style;
};

DrawPointControl.prototype.hexToRgb = function(hex) {
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

DrawPointControl.prototype.getImageStyle = function() {
	var fillColor = this.hexToRgb(this.style.fill_color);
	
	var fill = new ol.style.Fill({
		color: 'rgba(' + fillColor.r + ',' + fillColor.g + ',' + fillColor.b + ',' + this.style.fill_opacity + ')'
	});
	var stroke = new ol.style.Stroke({
  		color: this.style.stroke_color,
  		width: this.style.stroke_width
	})
	
	var wkn = this.style.well_known_name;
	
	var style = new ol.style.Circle({
  		radius: this.style.size,
  		fill: fill
	});
	if (wkn == 'square') {
		style = new ol.style.RegularShape({
			fill: fill,
			stroke: stroke,
			points: 4,
			radius: this.style.size,
			angle: Math.PI / 4
	    });
		
	} else if (wkn == 'triangle') {
		style = new ol.style.RegularShape({
			fill: fill,
			stroke: stroke,
			points: 3,
			radius: this.style.size,
			rotation: Math.PI / 4,
			angle: 0
	    });
		
	} else if (wkn == 'star') {
		style = new ol.style.RegularShape({
			fill: fill,
		    stroke: stroke,
		    points: 5,
		    radius: this.style.size,
		    radius2: 4,
		    angle: 0
	    });
		
	} else if (wkn == 'cross') {
		style = new ol.style.RegularShape({
			fill: fill,
			stroke: stroke,
			points: 4,
			radius: this.style.size,
			radius2: 0,
			angle: 0
	    });
		
	} else if (wkn == 'x') {
		style = new ol.style.RegularShape({
			fill: fill,
		    stroke: stroke,
		    points: 4,
		    radius: this.style.size,
		    radius2: 0,
		    angle: Math.PI / 4
	    });
		
	}
	
	return style;
};

DrawPointControl.prototype.getLayer = function() {
	return this.drawLayer;
};