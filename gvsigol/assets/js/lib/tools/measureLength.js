/**
 * gvSIG Online.
 * Copyright (C) 2007-2015 gvSIG Association.
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
var measureLength = function(map) {

	this.map = map;
	
	this.id = "measure-length";

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Measure length'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "icon-measure-length");
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
measureLength.prototype.drawLayer = null;

/**
 * TODO
 */
measureLength.prototype.sketch = null;

/**
 * TODO
 */
measureLength.prototype.lastSketch = null;

/**
 * TODO
 */
measureLength.prototype.helpTooltipElement = null;

/**
 * TODO
 */
measureLength.prototype.helpTooltip = null;

/**
 * TODO
 */
measureLength.prototype.measureTooltipElement = null;

/**
 * TODO
 */
measureLength.prototype.measureTooltip = null;

/**
 * TODO
 */
measureLength.prototype.lastMeasureTooltip = null;

/**
 * TODO
 */
measureLength.prototype.continueLineMsg = '';

/**
 * TODO
 */
measureLength.prototype.draw = null;

/**
 * TODO
 */
measureLength.prototype.source = null;

/**
 * TODO
 */
measureLength.prototype.drawLayer = null;

/**
 * TODO
 */
measureLength.prototype.active = false;

/**
 * TODO
 */
measureLength.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
measureLength.prototype.handler = function(e) {
	e.preventDefault();
		
	if (this.active) {
		this.deactivate();
		
	} else {
		this.$button.addClass('button-active');
		this.continueLineMsg = gettext('Click to continue measuring');
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
measureLength.prototype.isActive = function() {
	return this.active;
};

/**
 * TODO
 */
measureLength.prototype.addVectorLayerToMap = function() {

	this.drawLayer = new ol.layer.Vector({
		source: this.source,
	  	style: new ol.style.Style({
	    	fill: new ol.style.Fill({
	      		color: 'rgba(255, 255, 255, 0.2)'
	    	}),
	    	stroke: new ol.style.Stroke({
	      		color: '#0099ff',
	      		width: 2
	    	}),
	    	image: new ol.style.Circle({
	      		radius: 7,
	      		fill: new ol.style.Fill({
	        		color: '#0099ff'
	      		})
	    	})
	  	})
	});
	this.map.addLayer(this.drawLayer);
};

/**
 * Handle pointer move.
 * @param {ol.MapBrowserEvent} evt
 */
measureLength.prototype.pointerMoveHandler = function(evt) {
  	if (evt.dragging) {
    	return;
  	}
  	/** @type {string} */
  	var helpMsg = gettext('Click to start measuring');
  	/** @type {ol.Coordinate|undefined} */
  	var tooltipCoord = evt.coordinate;

  	if (this.sketch) {
    	var output;
    	var geom = (this.sketch.getGeometry());
    	if (geom instanceof ol.geom.LineString) {
      		output = this.formatLength( /** @type {ol.geom.LineString} */ (geom));
      		helpMsg = this.continueLineMsg;
      		tooltipCoord = geom.getLastCoordinate();
    	}
    	this.measureTooltipElement.innerHTML = output;
    	this.measureTooltip.setPosition(tooltipCoord);
  	}

  	this.helpTooltipElement.innerHTML = helpMsg;
  	this.helpTooltip.setPosition(evt.coordinate);
};

measureLength.prototype.addInteraction = function() {
	
	this.draw = new ol.interaction.Draw({
		source: this.source,
	    type: /** @type {ol.geom.GeometryType} */ ('LineString')
	});
	this.map.addInteraction(this.draw);

	this.createMeasureTooltip();
	this.createHelpTooltip();

	this.draw.on('drawstart',
		function(evt) {
	    	// set sketch
	        this.sketch = evt.feature;
	    	if (this.lastMeasureTooltip){
	    		this.map.removeOverlay(this.lastMeasureTooltip);
	    	}
	    	if (this.lastSketch) {
	    		this.source.removeFeature(this.lastSketch);
	    	}
	    }, this);

	this.draw.on('drawend',
	    function(evt) {
	    	this.measureTooltipElement.className = 'tooltip tooltip-static';
	        this.measureTooltip.setOffset([0, -7]);
	        this.lastSketch = this.sketch;
	        // unset sketch
	        this.sketch = null;
	        // unset tooltip so that a new one can be created
	        this.lastMeasureTooltip = this.measureTooltip;
	        this.measureTooltipElement = null;			        
	        this.createMeasureTooltip();
	      }, this);
};

/**
 * Creates a new help tooltip
 */
measureLength.prototype.createHelpTooltip = function() {
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
measureLength.prototype.createMeasureTooltip = function() {
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
 * @param {ol.geom.LineString} line
 * @return {string}
 */
measureLength.prototype.formatLength = function(line) {
  	var length = Math.round(line.getLength() * 100) / 100;
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
measureLength.prototype.deactivate = function() {			
	this.removeOverlays();
	this.map.removeLayer(this.drawLayer);
	this.map.removeInteraction(this.draw);
	this.source = null;
	this.lastMeasureTooltip = null;
	this.lastSketch = null;
	this.$button.removeClass('button-active');
	this.active = false;
	this.map.un('pointermove', this.pointerMoveHandler, this);
};

/**
 * TODO
 */
measureLength.prototype.removeOverlays = function(){
	this.map.removeOverlay(this.helpTooltip);
	this.map.removeOverlay(this.measureTooltip);
	var overlays = this.map.getOverlays().getArray();
	for (var i=0; i<overlays.length; i++){
		this.map.removeOverlay(overlays[i]);
	}
	$('.ol-overlay-container').remove();
};