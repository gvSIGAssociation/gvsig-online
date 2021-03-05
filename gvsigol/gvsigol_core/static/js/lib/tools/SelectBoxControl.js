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
var SelectBoxControl = function(map, toolbar) {
	var self = this;
	this.map = map;
	this.toolbar = toolbar;

	this.distance = 10;
	
	/*this.interaction = new ol.interaction.DragBox({
        condition: ol.events.condition.platformModifierKeyOnly
	});

	this.interaction.on('boxend', function() {
        var extent = self.interaction.getGeometry().getExtent();
        var evt = {
        	'coordinate': extent
        }
        self.clickHandler(evt);
	});*/

	this.drawSource = new ol.source.Vector();
	var lineStyle = new ol.style.Style({
		stroke: new ol.style.Stroke({
			color: '#ffcc33',
			width: 3
		}),
		fill: new ol.style.Fill({
			color: [255, 255, 255, 0.3]
		})
	});
	this.drawLayer = new ol.layer.Vector({
		source: self.drawSource,
		//style: [lineStyle],
		zIndex: 999999
	});
	this.map.addLayer(this.drawLayer);

	this.interaction = new ol.interaction.DragBox();
		
	this.interaction.on('boxstart', function (evt) {
		self.drawSource.clear();
	});

	this.interaction.on('boxend', function (evt) {
		var geom = evt.target.getGeometry();
		var epsg3857Bounds = [-20037508.34, -20037508.34, 20037508.34, 20037508.34];
		var normalizedExtent = self.getCanonicalExtent(geom.getExtent(), epsg3857Bounds);
		var selectedFeat = new ol.Feature({
			name: "selected_area",
			geometry: ol.geom.Polygon.fromExtent(normalizedExtent)
		});
		self.drawSource.addFeatures([selectedFeat]);

		//var extent = self.interaction.getGeometry().getExtent();
        var evt = {
        	'coordinate': normalizedExtent
        }
        self.clickHandler(evt);
	});
	
	this.control = new ol.control.Toggle({	
		html: '<i class="fa fa-object-group " ></i>',
		className: "edit",
		title: gettext('Select features'),
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


SelectBoxControl.prototype.active = false;

SelectBoxControl.prototype.isActive = function(e) {
	return this.active;

};

SelectBoxControl.prototype.activate = function(e) {
	this.selectionTable = viewer.core.getSelectionTable();
	if (this.selectionTable == null) {
		this.selectionTable = new SelectionTable(this.map);
		viewer.core.setSelectionTable(this.selectionTable);
	}
	this.selectionTable.removeTables();
	for (var i=0; i<this.toolbar.controlArray.length; i++) {
		this.toolbar.controlArray[i].deactivate();
	}
	this.active = true;
	this.addInteraction();
	this.map.on('click', this.clickHandler, this);
};

SelectBoxControl.prototype.addInteraction = function() {
	var self = this;
	this.map.addInteraction(this.interaction);
};

/**
 * Handle pointer click.
 * @param {ol.MapBrowserEvent} evt
 */

SelectBoxControl.prototype.clickHandler = function(evt) {
	var self = this;
	this.showFirst = true;

	this.mapCoordinates = evt.coordinate;

	if (this.active) {
		var layers = this.map.getLayers().getArray();
		var queryLayers = new Array();
		var url = null;
		var auxLayer = null;

		for (var i=0; i<layers.length; i++) {
			if (!layers[i].baselayer && !layers[i].external) {
				if (layers[i].wms_url && layers[i].getVisible()) {
					if( layers[i].isLayerGroup){
						var parent = layers[i];
						for (var j=0; j<layers.length; j++) {
							if (!layers[j].baselayer && !layers[j].external) {
								if (layers[j].wms_url) {
									if ((typeof layers[j].parentGroup === 'string' && layers[j].parentGroup == parent.layer_name) ||
											(layers[j].parentGroup != undefined && layers[j].parentGroup.groupName == parent.layer_name)){
										queryLayers.push(layers[j]);
									}
								}
							}
						}
					}else{
						queryLayers.push(layers[i]);
					}
				}
			}
		}

		var viewResolution = (this.map.getView().getResolution());
		var url = null;
		var ajaxRequests = new Array();
		var features = new Array();

		var layers_info = [];

		self.selectionTable.getSource().clear();
		self.selectionTable.removeTables();
		viewer.core.clearAllSelectedFeatures();
		for (var i=0; i<queryLayers.length; i++) {
			const qLayer = queryLayers[i];

			url = qLayer.wfs_url + '?service=WFS&' +
			'version=1.1.0&request=GetFeature&typename=' + qLayer.workspace + ':' + qLayer.layer_name +
			'&outputFormat=json&srsName=' + this.map.getView().getProjection().getCode();

			if(evt.coordinate.length == 2){
				var distance = this.distance;
				var pixel_low = [evt.pixel[0]-distance, evt.pixel[1]+distance];
				var point_low = self.map.getCoordinateFromPixel(pixel_low);

				var pixel_high = [evt.pixel[0]+distance, evt.pixel[1]-distance];
				var point_high = self.map.getCoordinateFromPixel(pixel_high);
				evt.coordinate = point_low.concat(point_high);
			}

			if (url.indexOf('http') == -1) {
				url = window.location.origin + url;
			}
			var href = new URL(url);
			href.searchParams.set('BBOX', evt.coordinate.join()+",urn:ogc:def:crs:EPSG:3857");
			url = href.toString();

			$.ajax({
				url: url,
				success: function(response) {
					var geometryName = self.getFeatureGeometryName(qLayer);
					var formatGeoJSON = new ol.format.GeoJSON({geometryName: geometryName});
					var features = formatGeoJSON.readFeatures(response);
					viewer.core.addSelectedFeaturesSource(qLayer.workspace + ":" + qLayer.layer_name, features);

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
						self.selectionTable.addTable(tableFeatures, qLayer.layer_name, qLayer.workspace, qLayer.wfs_url);
						self.selectionTable.show();
						self.selectionTable.registerEvents();
						
					}
				},
				error: function(jqXHR, textStatus) {
					console.log(textStatus);
				}
			});
		}

	}
};

SelectBoxControl.prototype.getCanonicalExtent = function(extent, crsBounds) {
	var crs_min_x = crsBounds[0];
	var crs_min_y = crsBounds[1];
	var crs_max_x = crsBounds[2];
	var crs_max_y = crsBounds[3];
	
	var min_x = extent[0];
	var min_y = extent[1];
	var max_x = extent[2];
	var max_y = extent[3];
	
	var bounds_width = crs_max_x - crs_min_x;
	var extent_width = max_x - min_x;
	if (extent_width > bounds_width) { // wrong extent
		min_x = crs_min_x;
		max_x = crs_max_x;
		extent_width = max_x - min_x;
	}
	
	var center_x = min_x + extent_width / 2.0;
	var center_xx = null;
	if (center_x < crs_min_x) {
		// we first move the extent to pure negative coordinates to ensure the module brings the center to
		// the "right" world, then we undo this movement to move the center to the right location
		center_xx = (center_x + crs_min_x) % (2* crs_min_x) - crs_min_x ;
	}
	else if (center_x > crs_max_x) {
		center_xx = (center_x + crs_max_x) % (2*crs_max_x) - crs_max_x;
	}
	if (center_xx) {
		// recalculate only when center was updated to avoid unnecessary rounding
		min_x = center_xx - extent_width / 2.0;
		max_x = center_xx + extent_width / 2.0;
	}
	
	var extent_height = max_y - min_y;
	var center_y = min_y + extent_height / 2.0;

	var center_yy = null;
	if (center_y < crs_min_y) {
		center_yy = (center_y + crs_min_y) % (2*crs_min_y) - crs_min_y;
	}
	else if (center_y > crs_max_y) {
		center_yy = (center_y + crs_max_y) % (2*crs_max_y) - crs_max_y;
	}
	if (center_yy) { // recalculate only when center was updated
		min_y = center_yy - extent_height / 2.0;
		max_y = center_yy + extent_height / 2.0;
	}
	return [min_x, min_y, max_x, max_y];
};

/**
 * TODO
 */
SelectBoxControl.prototype.hasLayers = function() {

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

SelectBoxControl.prototype.describeFeatureType = function(layer) {

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


SelectBoxControl.prototype.getFeatureGeometryName = function(layer) {
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

SelectBoxControl.prototype.isGeomType = function(type){
	if(type == 'POLYGON' || type == 'MULTIPOLYGON' || type == 'LINESTRING' || type == 'MULTILINESTRING' || type == 'POINT' || type == 'MULTIPOINT'){
		return true;
	}
	return false;
};

SelectBoxControl.prototype.deactivate = function() {
	this.active = false;

	this.map.un('click', this.clickHandler, this);
	this.map.removeInteraction(this.interaction);
	viewer.core.clearAllSelectedFeatures();
	this.drawSource.clear();
};