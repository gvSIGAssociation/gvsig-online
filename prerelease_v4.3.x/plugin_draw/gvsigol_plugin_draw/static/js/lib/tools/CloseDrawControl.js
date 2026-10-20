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
var CloseDrawControl = function(map, drawBar, pointLayer, lineLayer, polygonLayer, textLayer, select) {
	var self = this;
	
	this.map = map;
	this.drawBar = drawBar;
	this.pointLayer = pointLayer;
	this.lineLayer = lineLayer;
	this.polygonLayer = polygonLayer;
	this.textLayer = textLayer;
	this.select = select;
	
	this.control = new ol.control.Toggle({	
		html: '<i class="fa fa-times" ></i>',
		className: "edit",
		title: gettext('Close draw bar'),
		onToggle: function(active){
			self.pointLayer.getSource().clear();
			self.lineLayer.getSource().clear();
			self.polygonLayer.getSource().clear();
			self.textLayer.getSource().clear();
			self.select.getFeatures().clear();
			self.map.removeControl(self.drawBar);
			$('#get-feature-info').attr("disabled", false);
			$('#get-feature-info').css("cursor", "pointer");
			this.toggle();
			viewer.core.setActiveToolbar(null);
		}
	});
	drawBar.addControl(this.control);

};

CloseDrawControl.prototype.close = function(e) {
	this.pointLayer.getSource().clear();
	this.lineLayer.getSource().clear();
	this.polygonLayer.getSource().clear();
	this.textLayer.getSource().clear();
	this.select.getFeatures().clear();
	this.map.removeControl(this.drawBar);
	
	$('#get-feature-info').attr("disabled", false);
	$('#get-feature-info').css("cursor", "pointer");
	viewer.core.setActiveToolbar(null);

};