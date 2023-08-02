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
var projectZoom = function(map, conf) {

	this.map = map;
	this.conf = conf;
	
	this.id = "project-zoom";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Project zoom'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-arrows-alt");
	icon.setAttribute("aria-hidden", "true");
	button.appendChild(icon);
	
	this.$button = $(button);
	
	$('.ol-zoom').append(button);

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
projectZoom.prototype.drawLayer = null;

/**
 * TODO
 */
projectZoom.prototype.sketch = null;

/**
 * TODO
 */
projectZoom.prototype.lastSketch = null;

/**
 * TODO
 */
projectZoom.prototype.helpTooltipElement = null;

/**
 * TODO
 */
projectZoom.prototype.helpTooltip = null;

/**
 * TODO
 */
projectZoom.prototype.measureTooltipElement = null;

/**
 * TODO
 */
projectZoom.prototype.measureTooltip = null;

/**
 * TODO
 */
projectZoom.prototype.lastMeasureTooltip = null;

/**
 * TODO
 */
projectZoom.prototype.continuePolygonMsg = '';

/**
 * TODO
 */
projectZoom.prototype.draw = null;

/**
 * TODO
 */
projectZoom.prototype.source = null;

/**
 * TODO
 */
projectZoom.prototype.drawLayer = null;

/**
 * TODO
 */
projectZoom.prototype.active = false;

/**
 * TODO
 */
projectZoom.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
projectZoom.prototype.handler = function(e) {
	e.preventDefault();

	var transformedCoordinate = ol.proj.transform([parseFloat(this.conf.view.center_lon), parseFloat(this.conf.view.center_lat)], 'EPSG:4326', 'EPSG:3857');
	this.map.getView().setCenter(transformedCoordinate);
	this.map.getView().setZoom(this.conf.view.zoom);
	
	this.deactivate();
};

/**
 * TODO
 */
projectZoom.prototype.isActive = function() {
	return this.active;
};

/**
 * TODO
 */
projectZoom.prototype.addVectorLayerToMap = null;

/**
 * Handle pointer move.
 * @param {ol.MapBrowserEvent} evt
 */
projectZoom.prototype.pointerMoveHandler = null;

projectZoom.prototype.addInteraction = null;

/**
 * Creates a new help tooltip
 */
projectZoom.prototype.createHelpTooltip = null;


/**
 * Creates a new measure tooltip
 */
projectZoom.prototype.createMeasureTooltip = null;

/**
 * format length output
 * @param {ol.geom.Polygon} polygon
 * @return {string}
 */
projectZoom.prototype.formatArea = null;

/**
 * TODO
 */
projectZoom.prototype.deactivate = function() {			
//	this.removeOverlays();
//	this.map.removeLayer(this.drawLayer);
//	this.map.removeInteraction(this.draw);
//	this.source = null;
//	this.lastMeasureTooltip = null;
//	this.lastSketch = null;
	this.$button.removeClass('button-active');
	this.active = false;
//	this.map.un('pointermove', this.pointerMoveHandler, this);
};

/**
 * TODO
 */
projectZoom.prototype.removeOverlays = null;