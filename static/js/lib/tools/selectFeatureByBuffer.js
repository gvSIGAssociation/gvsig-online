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
var selectFeatureByBuffer = function(map, viewer) {

	this.map = map;
	this.viewer = viewer;

	this.distance = 1000;

	this.id = "select-feature-by-buffer";

	this.selectedFeatures = [];
	this.interaction = null;
	this.interaction_dragBox = null;
	this.circleFeature = null;

	var button = document.createElement('button');
	button.setAttribute("id", this.id);
	button.setAttribute("class", "toolbar-button");
	button.setAttribute("title", gettext('Select Feature By Buffer'));
	var icon = document.createElement('i');
	icon.setAttribute("class", "fa fa-times-circle-o");
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
selectFeatureByBuffer.prototype.active = false;

/**
 * TODO
 */
selectFeatureByBuffer.prototype.deactivable = true;

/**
 * TODO
 */
selectFeatureByBuffer.prototype.resultPanelContent = null;

/**
 * TODO
 */
selectFeatureByBuffer.prototype.mapCoordinates = null;

/**
 * TODO
 */
selectFeatureByBuffer.prototype.popup = null;


/**
 * @param {Event} e Browser event.
 */
selectFeatureByBuffer.prototype.handler = function(e) {
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
			this.map.on('click', this.showPopup, self);

			this.source = new ol.source.Vector();
			this.resultLayer = new ol.layer.Vector({
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
			this.resultLayer.baselayer = false;
			this.resultLayer.setZIndex(9999999);
			this.map.addLayer(this.resultLayer);

//			this.interaction_dragBox = new ol.interaction.DragBox({
//		        condition: ol.events.condition.platformModifierKeyOnly
//		    });
//			this.interaction_dragBox.on('boxend', function() {
//		        var extent = self.interaction_dragBox.getGeometry().getExtent();
//		        var evt = {
//		        		'coordinate': extent
//		        }
//		        self.clickHandler(evt, true);
//		    });
//			this.map.addInteraction(this.interaction_dragBox);


		} else {
			messageBox.show('warning', gettext('No layers available.'));
		}

	}
};


selectFeatureByBuffer.prototype.showPopup =function(evt) {
	$("body").overlay();
	$("#jqueryEasyOverlayDiv").css("opacity", "0.5");
	$('#jqueryEasyOverlayDiv').hide().show(0);

	this.source.clear();
	var self = this;

	self.mapCoordinates = evt.coordinate;

	var html = "<span>"+gettext("Select buffer radius (meters)")+":</span><br/>"+
	"<input type=\"number\" min=\"0\" step=\"100\" id=\"select-buffer-radius\" value=\""+self.distance+"\">"+
	"<button id=\"select-buffer-button\">"+gettext("Search")+"</button>"
	self.popup.show(self.mapCoordinates, '<div class="popup-wrapper getfeatureinfo-popup">' + html + '</div>');


	var circle = new ol.geom.Circle(self.mapCoordinates, parseInt(self.distance));
    self.circleFeature = new ol.Feature(circle);
    self.source.clear();
    self.source.addFeature(self.circleFeature);

	self.map.getView().setCenter(self.mapCoordinates);
	$('#select-buffer-radius').change(function(){
		self.distance = $(this).val();
		var circle = new ol.geom.Circle(self.mapCoordinates, parseInt(self.distance));
        self.circleFeature = new ol.Feature(circle);

        self.source.clear();
        self.source.addFeature(self.circleFeature);
	});
	$('#select-buffer-button').click(function(){
		if(self.circleFeature != null){
			var polygon_geom = ol.geom.Polygon.fromCircle(self.circleFeature.getGeometry(), 16)
			self.clickHandler(polygon_geom.getCoordinates(), true);
		}
		self.source.clear();
	});

	$.overlayout();
	$("#jqueryEasyOverlayDiv").css("display", "none");
}

/**
 * TODO
 */
selectFeatureByBuffer.prototype.hasLayers = function() {

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

selectFeatureByBuffer.prototype.describeFeatureType = function(layer) {

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


selectFeatureByBuffer.prototype.getFeatureGeometryName = function(layer) {
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

selectFeatureByBuffer.prototype.clickHandler = function(coords, isArea) {

//	$("body").overlay();
//	$("#jqueryEasyOverlayDiv").css("opacity", "0.5");
//	$('#jqueryEasyOverlayDiv').hide().show(0);

	var self = this;
	this.showFirst = true;



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

		var coord_str = ""
		for(var j=0; j<coords[0].length; j++){
			var coord = coords[0][j];
			var coor_x = (""+coord[0]).match(/(-)?\d+(\.\d{1,2})?/)
			var coor_y = (""+coord[1]).match(/(-)?\d+(\.\d{1,2})?/)
			coord_str += coor_x[0]+','+coor_y[0]+' ';
		}

		for (var i=0; i<queryLayers.length; i++) {
			const qLayer = queryLayers[i];

			url = qLayer.wfs_url + '?service=WFS&' +
			'version=1.0.0&request=GetFeature&typename=' + qLayer.workspace + ':' + qLayer.layer_name +
			'&outputFormat=json&srsName=' + this.map.getView().getProjection().getCode();

//			if(evt.coordinate.length == 2){
//				var distance = this.distance;
//				var pixel_low = [evt.pixel[0]-distance, evt.pixel[1]+distance];
//				var point_low = self.map.getCoordinateFromPixel(pixel_low);
//
//				var pixel_high = [evt.pixel[0]+distance, evt.pixel[1]-distance];
//				var point_high = self.map.getCoordinateFromPixel(pixel_high);
//
////				var x = coordinate[0];
////				var y = coordinate[1];
////
////				var extent = [x-distance, y-distance, x+distance, y+distance];
////				evt.coordinate = extent;
//				evt.coordinate = point_low.concat(point_high)
//			}
			var geometryName = self.getFeatureGeometryName(qLayer);
			var href = new URL(url);
			var shape = '<Filter xmlns="http://www.opengis.net/owc" xmlns:gml="http://www.opengis.net/gml">'+
				'<Intersects>'+
					'<PropertyName>'+geometryName+'</PropertyName>'+
					'<gml:Polygon srsDimension="2" srsName="urn:ogc:def:crs:EPSG::3857">'+
						'<gml:outerBoundaryIs>'+
							'<gml:LinearRing>'+
								'<gml:coordinates>'+coord_str;
			shape +=			'</gml:coordinates>'+
							'</gml:LinearRing>'+
						'</gml:outerBoundaryIs>'+
					'</gml:Polygon>'+
				'</Intersects>'+
			'</Filter>';

			href.searchParams.set('filter', shape);
			url = href.toString()

			$.ajax({
				url: url,
				success: function(response) {
					var formatGeoJSON = new ol.format.GeoJSON({geometryName: geometryName});
					var features = formatGeoJSON.readFeatures(response);
					self.viewer.addSelectedFeaturesSource(qLayer.workspace+":"+qLayer.layer_name, features);
					if(self.popup) self.popup.hide();
				},
				error: function(jqXHR, textStatus) {
					console.log(textStatus);
				}
			});
		}

	}
};


selectFeatureByBuffer.prototype.isGeomType = function(type){
	if(type == 'POLYGON' || type == 'MULTIPOLYGON' || type == 'LINESTRING' || type == 'MULTILINESTRING' || type == 'POINT' || type == 'MULTIPOINT'){
		return true;
	}
	return false;
}


selectFeatureByBuffer.prototype.describeFeatureType = function(layer) {

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
selectFeatureByBuffer.prototype.deactivate = function() {
	this.$button.removeClass('button-active');
	if (this.source) this.source.clear();
	this.circleFeature = null;
	if (this.resultLayer) this.map.removeLayer(this.resultLayer);
	this.map.un('click', this.showPopup, this);
	this.active = false;
	if(this.popup) this.popup.hide();
	this.viewer.clearAllSelectedFeatures();
};

