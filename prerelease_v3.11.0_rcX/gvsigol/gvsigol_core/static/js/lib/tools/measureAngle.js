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
var measureAngle = function(map) {

	this.map = map;
	
	this.id = "measure-angle";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Measure angle'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "icon-measure-angle");
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
measureAngle.prototype.drawLayer = null;

/**
 * TODO
 */
measureAngle.prototype.sketch = null;

/**
 * TODO
 */
measureAngle.prototype.lastSketch = null;

/**
 * TODO
 */
measureAngle.prototype.helpTooltipElement = null;

/**
 * TODO
 */
measureAngle.prototype.helpTooltip = null;

/**
 * TODO
 */
measureAngle.prototype.measureTooltipElement = null;

/**
 * TODO
 */
measureAngle.prototype.measureTooltip = null;

/**
 * TODO
 */
measureAngle.prototype.lastMeasureTooltip = null;

/**
 * TODO
 */
measureAngle.prototype.continuePolygonMsg = '';

/**
 * TODO
 */
measureAngle.prototype.draw = null;

/**
 * TODO
 */
measureAngle.prototype.source = null;

/**
 * TODO
 */
measureAngle.prototype.drawLayer = null;

/**
 * TODO
 */
measureAngle.prototype.active = false;

/**
 * TODO
 */
measureAngle.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
measureAngle.prototype.handler = function(e) {
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
measureAngle.prototype.isActive = function() {
	return this.active;
};

/**
 * TODO
 */
measureAngle.prototype.addVectorLayerToMap = function() {

	this.drawLayer = new ol.layer.Vector({
		source: this.source,
		style: [new ol.style.Style({
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
		}),
		new ol.style.Style({
			image: new ol.style.Circle({
            	radius: 50,
            	stroke: new ol.style.Stroke({
            		color: 'rgba(0, 0, 0, 0.7)'
            	}),
            	fill: new ol.style.Fill({
            		color: 'rgba(255, 255, 255, 0.2)'
            	})
            }),
	        geometry: function(feature) {
	            // return the coordinates of the first ring of the polygon
	            var coordinates = [feature.getGeometry().getCoordinates()[0][1]];
	            return new ol.geom.MultiPoint(coordinates);
	          }
	       	})]
	});
	this.map.addLayer(this.drawLayer);
	this.drawLayer.setZIndex(100000000);
};

/**
 * Handle pointer move.
 * @param {ol.MapBrowserEvent} evt
 */
measureAngle.prototype.pointerMoveHandler = function(evt) {
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

measureAngle.prototype.addInteraction = function() {
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
	    }),
	    maxPoints: 3
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
	    	
            listener = this.sketch.getGeometry().on('change', function(evt) {
              self.geom = evt.target;
              var output;
              if (self.geom instanceof ol.geom.Polygon) {
                output = self.formatArea(self.geom);
              }
              self.measureTooltipElement.innerHTML = output;
              
            });
            
	    }, this);

	this.draw.on('drawend',
	    function(evt) {
			this.measureTooltip.setPosition(this.geom.getCoordinates()[0][1]);
			this.geom = null;
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
measureAngle.prototype.createHelpTooltip = function() {
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
measureAngle.prototype.createMeasureTooltip = function() {
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
measureAngle.prototype.formatArea = function(polygon) {
	
	var coordinates = polygon.getLinearRing(0).getCoordinates();
	
	if (this.geom.getCoordinates()[0].length == 4) {
		var p2={
			x:coordinates[0][0],
			y:coordinates[0][1]
		};

		var p1={
			x:coordinates[1][0],
			y:coordinates[1][1]
		};

		var p3={
			x:coordinates[2][0],
			y:coordinates[2][1]	
		};

		var p12 = Math.sqrt(Math.pow((p1.x - p2.x),2) + Math.pow((p1.y - p2.y),2));
		var p13 = Math.sqrt(Math.pow((p1.x - p3.x),2) + Math.pow((p1.y - p3.y),2));
		var p23 = Math.sqrt(Math.pow((p2.x - p3.x),2) + Math.pow((p2.y - p3.y),2));

		//angle in radians
		var resultRadian = Math.acos(((Math.pow(p12, 2)) + (Math.pow(p13, 2)) - (Math.pow(p23, 2))) / (2 * p12 * p13));

		//angle in degrees
		var resultDegree = Math.acos(((Math.pow(p12, 2)) + (Math.pow(p13, 2)) - (Math.pow(p23, 2))) / (2 * p12 * p13)) * 180 / Math.PI;
		
		var output;
		output = gettext('Interior angle') + ': ' + parseInt(resultDegree) + ' ' + '<sup>o</sup><br />';
		output += gettext('Exterior angle') + ': ' + (360 - parseInt(resultDegree)).toString() + ' ' + '<sup>o</sup>';
		return output;
	} 
	
	
};

measureAngle.prototype.formatLength = function(coordinates) {
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
measureAngle.prototype.deactivate = function() {			
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
measureAngle.prototype.removeOverlays = function(){
	this.map.removeOverlay(this.helpTooltip);
	this.map.removeOverlay(this.measureTooltip);
	var overlays = this.map.getOverlays().getArray();
	for (var i=0; i<overlays.length; i++){
		this.map.removeOverlay(overlays[i]);
	}
	$('.ol-overlay-container').remove();
};