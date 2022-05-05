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
var selectFeature = function(map, viewer) {

	this.map = map;
	this.viewer = viewer;

	this.distance = 10;

	this.id = "select-feature";

	this.selectedFeatures = [];
	this.interaction = null;
	this.interaction_dragBox = null;

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Select Feature'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-object-group");
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
selectFeature.prototype.active = false;

/**
 * TODO
 */
selectFeature.prototype.deactivable = true;

/**
 * TODO
 */
selectFeature.prototype.resultPanelContent = null;

/**
 * TODO
 */
selectFeature.prototype.mapCoordinates = null;

/**
 * TODO
 */
selectFeature.prototype.popup = null;


/**
 * @param {Event} e Browser event.
 */
selectFeature.prototype.handler = function(e) {
	e.preventDefault();

	var self = this;
	if (this.active) {
		this.deactivate();

	} else {

			for (var i=0; i<this.map.tools.length; i++){
			  if (this.id != this.map.tools[i].id) {
				  if (this.map.tools[i].deactivable == true) {
  					  this.map.tools[i].deactivate();
				  }
			  }
		  }


		if (this.hasLayers()) {
			this.popup = new ol.Overlay.Popup();
			this.map.addOverlay(this.popup);

			this.$button.addClass('button-active');
			this.active = true;
			this.$button.trigger('control-active', [this]);

	    	var self = this;
			this.map.on('click', this.clickHandler, self);

			this.interaction_dragBox = new ol.interaction.DragBox({
		        condition: ol.events.condition.platformModifierKeyOnly
		    });
			this.interaction_dragBox.on('boxend', function() {
		        var extent = self.interaction_dragBox.getGeometry().getExtent();
		        var evt = {
		        		'coordinate': extent
		        }
		        self.clickHandler(evt, true);
		    });
			this.map.addInteraction(this.interaction_dragBox);


		} else {
			messageBox.show('warning', gettext('No layers available.'));
		}

	}
};

/**
 * TODO
 */
selectFeature.prototype.hasLayers = function() {

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

selectFeature.prototype.describeFeatureType = function(layer) {

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


selectFeature.prototype.getFeatureGeometryName = function(layer) {
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

/**
 * Handle pointer click.
 * @param {ol.MapBrowserEvent} evt
 */

selectFeature.prototype.clickHandler = function(evt, isArea) {

//	$("body").overlay();
//	$("#jqueryEasyOverlayDiv").css("opacity", "0.5");
//	$('#jqueryEasyOverlayDiv').hide().show(0);

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

		var viewResolution = /** @type {number} */ (this.map.getView().getResolution());
		var url = null;
		var ajaxRequests = new Array();
		var features = new Array();

		var layers_info = [];

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

//				var x = coordinate[0];
//				var y = coordinate[1];
//
//				var extent = [x-distance, y-distance, x+distance, y+distance];
//				evt.coordinate = extent;
				evt.coordinate = point_low.concat(point_high)
			}

			var href = new URL(url);
			href.searchParams.set('BBOX', evt.coordinate.join()+",urn:ogc:def:crs:EPSG:3857");
			url = href.toString()

			$.ajax({
				url: url,
				success: function(response) {
					var geometryName = self.getFeatureGeometryName(qLayer);
					var formatGeoJSON = new ol.format.GeoJSON({geometryName: geometryName});
					var features = formatGeoJSON.readFeatures(response);
					self.viewer.addSelectedFeaturesSource(qLayer.workspace+":"+qLayer.layer_name, features);
				},
				error: function(jqXHR, textStatus) {
					console.log(textStatus);
				}
			});
		}

	}
};


selectFeature.prototype.isGeomType = function(type){
	if(type == 'POLYGON' || type == 'MULTIPOLYGON' || type == 'LINESTRING' || type == 'MULTILINESTRING' || type == 'POINT' || type == 'MULTIPOINT'){
		return true;
	}
	return false;
}


selectFeature.prototype.describeFeatureType = function(layer) {

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


/**
 * TODO
 */
selectFeature.prototype.deactivate = function() {
	this.$button.removeClass('button-active');
	this.map.un('click', this.clickHandler, this);
	this.map.removeInteraction(this.interaction_dragBox);
	this.active = false;
	if(this.popup) this.popup.hide();
	this.viewer.clearAllSelectedFeatures();
};

