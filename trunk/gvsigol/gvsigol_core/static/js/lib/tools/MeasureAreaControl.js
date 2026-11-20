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
var MeasureAreaControl = function(map, toolbar) {
	var self = this;
	this.map = map;
	this.toolbar = toolbar;
	
	this.sketch = null;
	this.lastSketch = null;
	this.helpTooltipElement = null;
	this.helpTooltip = null;
	this.measureTooltipElement = null;
	this.measureTooltip = null;
	this.lastMeasureTooltip = null;
	this.continuePolygonMsg = '';
	
	this.source = new ol.source.Vector();
	this.layer = new ol.layer.Vector({
		source: this.source,
		style: new ol.style.Style({
			fill: new ol.style.Fill({
				color: 'rgba(255, 255, 255, 0.2)'
	        }),
	        stroke: new ol.style.Stroke({
	        	color: '#ffcc33',
	            width: 2
	        }),
	        image: new ol.style.Circle({
	        	radius: 7,
	            fill: new ol.style.Fill({
	            	color: '#ffcc33'
	            })
	        })
		})
	});
	
	this.interaction = new ol.interaction.Draw({
		source: this.source,
	    type: ('Polygon'),
	    style: new ol.style.Style({
	    	fill: new ol.style.Fill({
	    		color: 'rgba(255, 255, 255, 0.2)'
            }),
            stroke: new ol.style.Stroke({
            	color: 'rgba(0, 0, 0, 0.5)',
            	lineDash: [10, 10],
            	width: 2
            }),
            image: new ol.style.Circle({
            	radius: 5,
            	stroke: new ol.style.Stroke({
            		color: 'rgba(0, 0, 0, 0.7)'
            	}),
            	fill: new ol.style.Fill({
            		color: 'rgba(255, 255, 255, 0.2)'
            	})
            })
	    })
	});
	
	var listener;
	this.interaction.on('drawstart',
		function(evt) {
	        this.sketch = evt.feature;
	    	if (this.lastMeasureTooltip){
	    		this.map.removeOverlay(this.lastMeasureTooltip);
	    	}
	    	if (this.lastSketch) {
	    		this.source.removeFeature(this.lastSketch);
	    	}
	    	
	    	/** @type {ol.Coordinate|undefined} */
            var tooltipCoord = evt.coordinate;

            listener = this.sketch.getGeometry().on('change', function(evt) {
              var geom = evt.target;
              var output;
              if (geom instanceof ol.geom.Polygon) {
                output = self.formatArea(geom);
                tooltipCoord = geom.getLastCoordinate();
              }
              self.measureTooltipElement.innerHTML = output;
              self.measureTooltip.setPosition(tooltipCoord);
            });
            
	    }, this);

	this.interaction.on('drawend',
	    function(evt) {
	    	this.measureTooltipElement.className = 'tooltip tooltip-static';
	        this.measureTooltip.setOffset([0, -7]);
	        this.lastSketch = this.sketch;
	        this.sketch = null;
	        this.lastMeasureTooltip = this.measureTooltip;
	        this.measureTooltipElement = null;			        
	        this.createMeasureTooltip();
	        ol.Observable.unByKey(listener);
	      }, this);
	
	this.control = new ol.control.Toggle({	
		html: '<i class="icon-measure-area" ></i>',
		className: "edit",
		title: gettext('Measure area and perimeter'),
		interaction: this.interaction,
		onToggle: function(active){
			if (active) {
				viewer.core.disableTools(this);
				self.activate();
			} else {
				self.deactivate();
			}
		}
	});
	this.toolbar.addControl(this.control);
};


MeasureAreaControl.prototype.active = false;

MeasureAreaControl.prototype.isActive = function(e) {
	return this.active;

};

MeasureAreaControl.prototype.activate = function(e) {
	for (var i=0; i<this.toolbar.controlArray.length; i++) {
		this.toolbar.controlArray[i].deactivate();
	}
	this.active = true;
	this.continuePolygonMsg = gettext('Click to continue measuring');
	this.addLayer();
	this.addInteraction();
	this.map.on('pointermove', this.pointerMoveHandler, this);
};

/**
 * Handle pointer move.
 * @param {ol.MapBrowserEvent} evt
 */
MeasureAreaControl.prototype.pointerMoveHandler = function(evt) {
	if (evt.dragging) {
    	return;
  	}
  	/** @type {string} */
  	var helpMsg = gettext('Click to start measuring');

  	if (this.sketch) {
    	var output;
    	var geom = (this.sketch.getGeometry());
    	if (geom instanceof ol.geom.Polygon) {
    	    helpMsg = this.continuePolygonMsg;
    	}
  	}

  	this.helpTooltipElement.innerHTML = helpMsg;
  	this.helpTooltip.setPosition(evt.coordinate);
};

MeasureAreaControl.prototype.addLayer = function() {
	this.map.addLayer(this.layer);
	this.layer.setZIndex(100000000);
	this.layer.printable = false;
};

MeasureAreaControl.prototype.addInteraction = function() {
	var self = this;
	this.map.addInteraction(this.interaction);

	this.createMeasureTooltip();
	this.createHelpTooltip();
};

/**
 * Creates a new help tooltip
 */
MeasureAreaControl.prototype.createHelpTooltip = function() {
	if (this.helpTooltipElement) {
    	this.helpTooltipElement.parentNode.removeChild(this.helpTooltipElement);
  	}
	this.helpTooltipElement = document.createElement('div');
	this.helpTooltipElement.className = 'tooltip hidden';
	this.helpTooltip = new ol.Overlay({
    	element: this.helpTooltipElement,
    	offset: [15, 0],
    	positioning: 'center-left'
  	});
	this.map.addOverlay(this.helpTooltip);
};


/**
 * Creates a new measure tooltip
 */
MeasureAreaControl.prototype.createMeasureTooltip = function() {
  	if (this.measureTooltipElement) {
	  	this.measureTooltipElement.parentNode.removeChild(this.measureTooltipElement);
  	}
  	this.measureTooltipElement = document.createElement('div');
  	this.measureTooltipElement.className = 'tooltip tooltip-measure';
  	this.measureTooltip = new ol.Overlay({
  		element: this.measureTooltipElement,
    	offset: [0, -15],
    	positioning: 'bottom-center'
  	});
  	this.map.addOverlay(this.measureTooltip);
};

/**
 * format length output
 * @param {ol.geom.Polygon} polygon
 * @return {string}
 */
MeasureAreaControl.prototype.formatArea = function(polygon) {
	
	var wgs84Sphere = new ol.Sphere(6378137);
	var sourceProj = this.map.getView().getProjection();
	var geom = /** @type {ol.geom.Polygon} */(polygon.clone().transform(sourceProj, 'EPSG:4326'));
	var coordinates = geom.getLinearRing(0).getCoordinates();
	var area = Math.abs(wgs84Sphere.geodesicArea(coordinates));

	var output;
	output = gettext('Area') + ': ' + (Math.round(area * 100) / 100) + ' ' + 'm<sup>2</sup><br />';
	output += gettext('Perimeter') + ': ' + this.formatLength(coordinates);
	return output;
};

MeasureAreaControl.prototype.formatLength = function(coordinates) {
	var length = 0;
	var wgs84Sphere = new ol.Sphere(6378137);
		
	for (var i = 0, ii = coordinates.length - 1; i < ii; ++i) {
		var c1 = coordinates[i];
	    var c2 = coordinates[i + 1];
	    length += wgs84Sphere.haversineDistance(c1, c2);
	}

	var output;
	if (length > 100) {
		output = (Math.round(length / 1000 * 100) / 100) + ' ' + 'km';
	} else {
	    output = (Math.round(length * 100) / 100) + ' ' + 'm';
	}
	return output;
};

/**
 * TODO
 */
MeasureAreaControl.prototype.removeOverlays = function(){
	console.log('removeOverlays')
	this.map.removeOverlay(this.helpTooltip);
	this.map.removeOverlay(this.measureTooltip);
	var overlays = this.map.getOverlays().getArray();
	for (var i=0; i<overlays.length; i++){
		this.map.removeOverlay(overlays[i]);
	}
	$('.ol-overlay-container').remove();
};

MeasureAreaControl.prototype.deactivate = function() {
	this.active = false;
	
	this.removeOverlays();
	this.map.removeLayer(this.layer);
	this.map.removeInteraction(this.interaction);
	this.source.clear();
	this.lastMeasureTooltip = null;
	this.lastSketch = null;
	this.map.un('pointermove', this.pointerMoveHandler, this);
};



MeasureAreaControl.prototype.getLayer = function() {
	return this.layer;
};