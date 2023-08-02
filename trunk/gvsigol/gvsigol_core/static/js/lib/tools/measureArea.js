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
var measureArea = function(map) {

	this.map = map;
	
	this.id = "measure-area";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Measure area'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "icon-measure-area");
	button.appendChild(icon);
	
	this.$button = $(button);
	
	$('#toolbar').append(button);

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
measureArea.prototype.drawLayer = null;

/**
 * TODO
 */
measureArea.prototype.sketch = null;

/**
 * TODO
 */
measureArea.prototype.lastSketch = null;

/**
 * TODO
 */
measureArea.prototype.helpTooltipElement = null;

/**
 * TODO
 */
measureArea.prototype.helpTooltip = null;

/**
 * TODO
 */
measureArea.prototype.measureTooltipElement = null;

/**
 * TODO
 */
measureArea.prototype.measureTooltip = null;

/**
 * TODO
 */
measureArea.prototype.lastMeasureTooltip = null;

/**
 * TODO
 */
measureArea.prototype.continuePolygonMsg = '';

/**
 * TODO
 */
measureArea.prototype.draw = null;

/**
 * TODO
 */
measureArea.prototype.source = null;

/**
 * TODO
 */
measureArea.prototype.drawLayer = null;

/**
 * TODO
 */
measureArea.prototype.active = false;

/**
 * TODO
 */
measureArea.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
measureArea.prototype.handler = function(e) {
	e.preventDefault();
	
	
	if (this.active) {
		this.deactivate();
		
	} else {
		this.$button.addClass('button-active');
		this.continuePolygonMsg = gettext('Click to continue measuring');
		this.active = true;
		this.$button.trigger('control-active', [this]);
		this.source = new ol.source.Vector();
		this.addVectorLayerToMap();
		this.addInteraction();
		this.map.on('pointermove', this.pointerMoveHandler, this);				
	}
};

/**
 * TODO
 */
measureArea.prototype.isActive = function() {
	return this.active;
};

/**
 * TODO
 */
measureArea.prototype.addVectorLayerToMap = function() {

	this.drawLayer = new ol.layer.Vector({
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
	this.map.addLayer(this.drawLayer);
	this.drawLayer.setZIndex(100000000);
};

/**
 * Handle pointer move.
 * @param {ol.MapBrowserEvent} evt
 */
measureArea.prototype.pointerMoveHandler = function(evt) {
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

measureArea.prototype.addInteraction = function() {
	var self = this;
	
	this.draw = new ol.interaction.Draw({
		source: this.source,
	    type: /** @type {ol.geom.GeometryType} */ ('Polygon'),
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
	this.map.addInteraction(this.draw);

	this.createMeasureTooltip();
	this.createHelpTooltip();

	var listener;
	this.draw.on('drawstart',
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

	this.draw.on('drawend',
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
};

/**
 * Creates a new help tooltip
 */
measureArea.prototype.createHelpTooltip = function() {
	if (this.helpTooltipElement) {
    	this.helpTooltipElement.parentNode.removeChild(this.helpTooltipElement);
  	}
	this.helpTooltipElement = document.createElement('div');
	this.helpTooltipElement.className = 'tooltip';
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
measureArea.prototype.createMeasureTooltip = function() {
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
measureArea.prototype.formatArea = function(polygon) {
	
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

measureArea.prototype.formatLength = function(coordinates) {
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
measureArea.prototype.deactivate = function() {			
	this.removeOverlays();
	this.map.removeLayer(this.drawLayer);
	this.map.removeInteraction(this.draw);
	this.source = null;
	this.lastMeasureTooltip = null;
	this.lastSketch = null;
	this.$button.removeClass('button-active');
	this.active = false;
	this.map.un('pointermove', this.pointerMoveHandler, this);
	
	/*var layers = this.map.getLayers().getArray();
	for (var i=0; i<layers.length; i++) {
		if (layers[i] instanceof ol.layer.Vector) {		
			layers[i].getSource().clear();
		}
	}*/
};

/**
 * TODO
 */
measureArea.prototype.removeOverlays = function(){
	this.map.removeOverlay(this.helpTooltip);
	this.map.removeOverlay(this.measureTooltip);
	var overlays = this.map.getOverlays().getArray();
	for (var i=0; i<overlays.length; i++){
		this.map.removeOverlay(overlays[i]);
	}
	$('.ol-overlay-container').remove();
};