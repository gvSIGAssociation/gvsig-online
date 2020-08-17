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
	this.selectionTable = viewer.core.getSelectionTable();

	this.distance = 10;
	
	this.interaction = new ol.interaction.DragBox({
        condition: ol.events.condition.platformModifierKeyOnly
	});

	this.interaction.on('boxend', function() {
        var extent = self.interaction.getGeometry().getExtent();
        var evt = {
        	'coordinate': extent
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
};