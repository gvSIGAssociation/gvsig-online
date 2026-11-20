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
var InsertTextControl = function(drawBar, map, styleSettings) {
	var self = this;
	this.map = map;
	this.drawBar = drawBar;
	this.styleName = 'text_style_0';
	this.style = {
		font_size: 16,
		fill_color: '#f15511',
		fill_opacity: 1.0,
		stroke_color: '#ffffff',
		stroke_width: 4,
		text: gettext('Insert text')
	};
	
	this.source = new ol.source.Vector();
	this.drawLayer = new ol.layer.Vector({
		source: this.source
	});
	this.drawLayer.setZIndex(99999999);
	this.drawLayer.printable = true;
	this.drawLayer.drawType = 'text';
	map.addLayer(this.drawLayer);
	
	this.drawLayer.drawStyleSettings = styleSettings;
	 
	this.drawInteraction = new ol.interaction.Draw({
		source: this.drawLayer.getSource(),
		type: 'Point'
	});
	
	this.count = 0;
	this.drawInteraction.on('drawend',
		function(evt) {
			var drawed = evt.feature;
			drawed.setProperties({
				'style_name': this.styleName,
				'text': this.style.text
			});
			drawed.drawed = true;
			drawed.dtype = 'text';
			var style = self.getStyle(drawed);
			drawed.setStyle(style);
			drawed.setId('text_' + this.count);
			this.count++;
			
		}, this);
	
	this.control = new ol.control.Toggle({	
		html: '<i class="fa fa-text-width" ></i>',
		className: "edit",
		title: gettext('Insert text'),
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


InsertTextControl.prototype.active = false;

InsertTextControl.prototype.isActive = function(e) {
	return this.active;

};

InsertTextControl.prototype.activate = function(e) {
	this.active = true;
	this.map.addInteraction(this.drawInteraction);

};

InsertTextControl.prototype.deactivate = function() {
	this.active = false;
	this.map.removeInteraction(this.drawInteraction);
};

InsertTextControl.prototype.getStyle = function(feature) {
	var self = this;
	
	var style = new ol.style.Style({
		image: new ol.style.Circle({
	      radius: 8,
	      fill: new ol.style.Fill({color: 'rgba(0, 0, 0, 0.1)'}),
	      stroke: new ol.style.Stroke({color: 'rgba(0, 0, 0, 0.8)', width: 1})
	    }),
		text: this.getTextStyle()
    });
	
	return style;
};

InsertTextControl.prototype.setStyle = function(style, styleName) {
	this.styleName = styleName;
	this.style = style;
};

InsertTextControl.prototype.hexToRgb = function(hex) {
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

InsertTextControl.prototype.getTextStyle = function() {
	return new ol.style.Text({
		textAlign: 'center',
		font: 'normal ' + this.style.font_size + 'px/1 sans-serif',
		text: this.style.text,
		fill: new ol.style.Fill({color: this.style.fill_color}),
		stroke: new ol.style.Stroke({color: this.style.stroke_color, width: this.style.stroke_width}),
		offsetX: 0,
		offsetY: 0,
		placement: 'point',
		rotation: 0
	});
};

InsertTextControl.prototype.getLayer = function() {
	return this.drawLayer;
};