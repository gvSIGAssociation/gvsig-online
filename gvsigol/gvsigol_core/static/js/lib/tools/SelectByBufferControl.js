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
var SelectByBufferControl = function(map, toolbar) {
	var self = this;
	this.map = map;
	this.toolbar = toolbar;
	this.popup = null;
	
	this.distance = 1000;
	this.circleFeature = null;
	
	this.source = new ol.source.Vector();
	this.layer = new ol.layer.Vector({
		source: this.source,
	  	style: new ol.style.Style({
	    	fill: new ol.style.Fill({
	      		color: 'rgba(0, 153, 255, 0.2)'
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
	
	this.control = new ol.control.Toggle({	
		html: '<i class="fa fa-dot-circle-o" ></i>',
		className: "edit",
		title: gettext('Select by buffer'),
		onToggle: function(active){
			if (active) {
				viewer.core.disableTools(this);
				self.activate();
			} else {
				self.deactivate();
			}
		}
	});
	this.control.on('change:active', function(evt) {
		if (!evt.active) {
			self._disableClickEvent();
		}
	});
	this.toolbar.addControl(this.control);
};


SelectByBufferControl.prototype.active = false;

SelectByBufferControl.prototype.isActive = function(e) {
	return this.active;

};

SelectByBufferControl.prototype.activate = function(e) {
	this.selectionTable = viewer.core.getSelectionTable();
	if (this.selectionTable == null) {
		this.selectionTable = new SelectionTable(this.map);
		viewer.core.setSelectionTable(this.selectionTable);
	}
	for (var i=0; i<this.toolbar.controlArray.length; i++) {
		this.toolbar.controlArray[i].deactivate();
	}
	this.active = true;
	this.addLayer();
	this.map.un('click', this.showPopup, this);
	this.map.on('click', this.showPopup, this);
	this.addPopup();
};

SelectByBufferControl.prototype.addLayer = function() {
	this.layer.baselayer = false;
	this.layer.setZIndex(9999999);
	this.map.addLayer(this.layer);
};

SelectByBufferControl.prototype.addPopup = function() {
	this.popup = new ol.Overlay.Popup ({	
		popupClass: "default",
		closeBox: true,
		onshow: function(){ console.log("You opened the box"); },
		onclose: function(){ console.log("You close the box"); },
		positioning: 'auto',
		//autoPan: true,
		autoPanAnimation: { duration: 250 }
	});
	this.map.addOverlay(this.popup);
};

SelectByBufferControl.prototype.showPopup =function(evt) {
	var self = this;
	
	$("body").overlay();
	$("#jqueryEasyOverlayDiv").css("opacity", "0.5");
	$('#jqueryEasyOverlayDiv').hide().show(0);

	this.source.clear();
	self.mapCoordinates = evt.coordinate;

	var html = '';
	html += '<span>' + gettext('Select buffer radius (meters)') + ':</span><br/>';
	html += '<input type="number" min="0" step="100" id="select-buffer-radius" value="' + self.distance + '">';
	html += '<button id="select-buffer-button">' + gettext("Search") + '</button>';
	
	self.popup.show(self.mapCoordinates, '<div class="popup-wrapper getfeatureinfo-popup">' + html + '</div>');

	// Apply latitude correction to radius
	var correctedRadius = self.getCorrectedRadius(self.mapCoordinates, self.distance);
	var circle = new ol.geom.Circle(self.mapCoordinates, correctedRadius);
    self.circleFeature = new ol.Feature(circle);
    self.source.clear();
    self.source.addFeature(self.circleFeature);

	self.map.getView().setCenter(self.mapCoordinates);
	$('#select-buffer-radius').change(function(){
		self.distance = $(this).val();
		// Apply latitude correction to radius
		var correctedRadius = self.getCorrectedRadius(self.mapCoordinates, self.distance);
		var circle = new ol.geom.Circle(self.mapCoordinates, correctedRadius);
        self.circleFeature = new ol.Feature(circle);

        self.source.clear();
        self.source.addFeature(self.circleFeature);
	});
	$('#select-buffer-button').click(function(){
		if(self.circleFeature != null){
			var polygon_geom = ol.geom.Polygon.fromCircle(self.circleFeature.getGeometry(), 16);
			self.clickHandler(polygon_geom, true);
		}
		self.source.clear();
	});

	$.overlayout();
	$("#jqueryEasyOverlayDiv").css("display", "none");
};

/**
 * Calculate corrected radius for a given point and distance in meters
 * considering latitude distortion in Web Mercator projection
 * @param {Array} mapCoordinates - Coordinates in EPSG:3857
 * @param {Number} distanceInMeters - Distance in meters
 * @returns {Number} Corrected radius for the circle
 */
SelectByBufferControl.prototype.getCorrectedRadius = function(mapCoordinates, distanceInMeters) {
	// Convert to geographic coordinates to work with real distances
	var geographicCoords = ol.proj.transform(mapCoordinates, 'EPSG:3857', 'EPSG:4326');
	var longitude = geographicCoords[0];
	var latitude = geographicCoords[1];
	
	// Earth's radius in meters
	var earthRadius = 6378137;
	
	// Calculate the angular distance in radians
	var angularDistance = distanceInMeters / earthRadius;
	
	// Calculate the radius in degrees for longitude at this latitude
	var latRad = latitude * Math.PI / 180;
	var radiusInDegreesLon = angularDistance * 180 / Math.PI / Math.cos(latRad);
	
	// Create a point at the specified distance to the east
	var eastPoint = [longitude + radiusInDegreesLon, latitude];
	
	// Transform both points back to Web Mercator
	var centerInWebMercator = ol.proj.transform([longitude, latitude], 'EPSG:4326', 'EPSG:3857');
	var eastPointInWebMercator = ol.proj.transform(eastPoint, 'EPSG:4326', 'EPSG:3857');
	
	// Calculate the distance between these two points in Web Mercator coordinates
	var dx = eastPointInWebMercator[0] - centerInWebMercator[0];
	var dy = eastPointInWebMercator[1] - centerInWebMercator[1];
	var correctedRadius = Math.sqrt(dx * dx + dy * dy);
	
	return correctedRadius;
};

/**
 * Handle pointer click.
 * @param {ol.MapBrowserEvent} evt
 */

SelectByBufferControl.prototype.clickHandler = function(geom, isArea) {
	var self = this;
	this.showFirst = true;
	this.source.clear();
	if (this.active) {
		var layers = this.map.getLayers().getArray();
		var queryLayers = new Array();
		var url = null;
		var auxLayer = null;

		for (var i=0; i<layers.length; i++) {
			if (!layers[i].baselayer && !layers[i].external && !layers[i].isLayerGroup) {
				if (layers[i].wms_url && layers[i].getVisible()) {
					queryLayers.push(layers[i]);
				}
			}
		}
		var viewResolution = (this.map.getView().getResolution());
		var url = null;
		var ajaxRequests = new Array();
		var features = new Array();

		var layers_info = [];
		for (var i=0; i<queryLayers.length; i++) {
			const qLayer = queryLayers[i];
			var geometryName = self.getFeatureGeometryName(qLayer);
			var f = ol.format.filter;
			var ftype = qLayer.workspace + ':' + qLayer.layer_name;
			var featureRequest = new ol.format.WFS().writeGetFeature({
				srsName: 'EPSG:3857',
				featureTypes: [ftype],
				outputFormat: 'application/json',
				filter: f.intersects(geometryName, geom, 'EPSG:3857')
			});

			var wfsURL = qLayer.wfs_url;
			if (wfsURL.indexOf('http') == -1) {
				wfsURL = window.location.origin + wfsURL;
			}
			var headers = {};
			if (viewer.core.conf.user && viewer.core.conf.user.token) {
				// FIXME: this is just an OIDC test. We must properly deal with refresh tokens etc
				headers["Authorization"] = 'Bearer ' + viewer.core.conf.user.token;
			};
			fetch(wfsURL, {
				method: 'POST',
				headers: headers,
				mode: 'cors',
				body: new XMLSerializer().serializeToString(featureRequest)
			}).then(function(response) {
				return response.json();
			}).then(function(json) {
				var format = new ol.format.GeoJSON();
				var features = format.readFeatures(json);
				viewer.core.addSelectedFeaturesSource(qLayer.workspace + ":" + qLayer.layer_name, features);
				if(self.popup) self.popup.hide();

				var tableFeatures = [];
				for (var i=0; i<features.length; i++) {
					var row = {};
					for (p in features[i].getProperties()) {
						if (p != 'wkb_geometry') {
							row[p] = features[i].getProperties()[p];
						}
						
					}
					row['featureid'] = features[i].getId();
					tableFeatures.push(row)
				}

				if (tableFeatures.length > 0) {
					if (!self.selectionTable) {
						self.selectionTable = new SelectionTable(self.map);
					}
					self.selectionTable.addTable(tableFeatures, qLayer.layer_name, qLayer.workspace, qLayer.wfs_url, qLayer.conf);
					self.selectionTable.show();
					self.selectionTable.registerEvents();
					
				}
			});
		}

	}
};

/**
 * TODO
 */
SelectByBufferControl.prototype.hasLayers = function() {

	var hasLayers = false;

	var layers = this.map.getLayers().getArray();
	var queryLayers = new Array();
	for (var i=0; i<layers.length; i++) {
		if (!layers[i].baselayer && !layers[i].external) {
			if (layers[i].queryable) {
				if (layers[i].getVisible()) {
					queryLayers.push(layers[i]);
				}
			}
		}
	}

	if (queryLayers.length > 0) {
		hasLayers = true;
	}

	return hasLayers;
};

SelectByBufferControl.prototype.describeFeatureType = function(layer) {

	var featureType = new Array();

	$.ajax({
		type: 'POST',
		async: false,
	  	url: '/gvsigonline/services/describeFeatureType/',
	  	data: {
	  		'layer': layer.layer_name,
			'workspace': layer.workspace
		},
	  	success	:function(response){
	  		if("fields" in response){
	  			featureType = response['fields'];
	  		}
		},
	  	error: function(){}
	});

	return featureType;
};


SelectByBufferControl.prototype.getFeatureGeometryName = function(layer) {
	var featureType = this.describeFeatureType(layer);

	for (var i=0; i<featureType.length; i++) {
		if (this.isGeomType(featureType[i].type)) {
			if (featureType[i].type == "POLYGON") {
				this.geometryType = 'Polygon';
				this.geometryName = featureType[i].name;
			} else if (featureType[i].type == "MULTIPOLYGON") {
				this.geometryType = 'MultiPolygon';
				this.geometryName = featureType[i].name;
			} else if (featureType[i].type == "LINESTRING") {
				this.geometryType = 'LineString';
				this.geometryName = featureType[i].name;
			} else if (featureType[i].type == "MULTILINESTRING") {
				this.geometryType = 'MultiLineString';
				this.geometryName = featureType[i].name;
			} else if (featureType[i].type == "POINT") {
				this.geometryType = 'Point';
				this.geometryName = featureType[i].name;
			} else if (featureType[i].type == "MULTIPOINT") {
				this.geometryType = 'MultiPoint';
				this.geometryName = featureType[i].name;
			}
		}
	}

	return this.geometryName;
};

SelectByBufferControl.prototype.isGeomType = function(type){
	if(type == 'POLYGON' || type == 'MULTIPOLYGON' || type == 'LINESTRING' || type == 'MULTILINESTRING' || type == 'POINT' || type == 'MULTIPOINT'){
		return true;
	}
	return false;
};

SelectByBufferControl.prototype._disableClickEvent = function() {
	this.active = false;

	if (this.source) this.source.clear();
	this.circleFeature = null;
	if (this.layer) this.map.removeLayer(this.layer);
	this.map.un('click', this.showPopup, this);
	if(this.popup) {
		this.popup.hide();
		this.popup = null;
	}
}

SelectByBufferControl.prototype.deactivate = function() {
	this._disableClickEvent();
	viewer.core.clearAllSelectedFeatures();
};
