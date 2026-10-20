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
 * @author: José Badía <jbadia@scolab.es>
 * @author: César Martinez <cmartinez@scolab.es>
 */

/**
 * TODO
 */
var CatalogMap = function(catalog, container_id) {
	this.catalog = catalog;
	this.map = null;	
	this.vector_layer = null;
	this.selected_feat = null;
	this.interaction = null;
	this.initialization(container_id);
};

CatalogMap.prototype.cleanData = function(){
	this.vector_source.clear();
	this.selected_feat = null;
}

CatalogMap.prototype.getSelectedArea = function(format){
	if (this.selected_feat != null){
		return this.selected_feat.getGeometry();
	}
	return null;
}

CatalogMap.prototype.setSpatialFilter = function(geom, filterType) {
	if (geom!=null) {
		this.selected_feat = new ol.Feature({
			name: "selected_area",
			geometry: geom
		});
		this.vector_source.clear();
		this.vector_source.addFeatures([this.selected_feat]);
	}
}

CatalogMap.prototype.zoomToSelection = function() {
	if (this.selected_feat!=null) {
		var geom = this.selected_feat.getGeometry(); 
		if (geom!=null) {
			if (geom.getType()=='Point' || geom.getType()=='MultiPoint') {
				var extent = geom.getExtent();
				var x = extent[0] + (extent[2]-extent[0])/2;
				var y = extent[1] + (extent[3]-extent[1])/2;
				this.map.getView().setCenter([x, y]);
			}
			else {
				this.map.getView().fit(geom);
			}
		}
	}
}

/**
 * This method should not be necessary in newer OL versions
 */
CatalogMap.prototype.getZoomForResolution = function(resolution) {
	var view = this.map.getView();
	var offset = 0;
	var max, zoomFactor;
	if (view.getResolutions()) {
		var nearest = ol.array.linearFindNearest(view.getResolutions(), resolution, 1);
		offset = nearest;
		max = view.view.getResolutions()[nearest];
		if (nearest == view.getResolutions().length - 1) {
			zoomFactor = 2;
		} else {
			zoomFactor = max / view.getResolutions()[nearest + 1];
		}
	 } else {
		 max = view.getMaxResolution();
		 zoomFactor = 2;
	}
	return offset + Math.log(max / resolution) / Math.log(zoomFactor);
};

CatalogMap.prototype.getDrawRectangleControl = function(toolbar, map){
	var self = this;
	this.drawRectangleInteraction = new ol.interaction.DragBox();
	
	this.drawRectangleInteraction.on('boxstart', function (evt) {
		self.vector_source.clear();
	});
	
	this.drawRectangleInteraction.on('boxend', function (evt) {
		var geom = evt.target.getGeometry();
		self.selected_feat = new ol.Feature({
			name: "selected_area",
			geometry: geom
		});
		self.vector_source.addFeatures([self.selected_feat]);
		self.catalog.filterCatalog();
	});

	return new ol.control.Toggle({	
		html: '<i class="fa fa-object-group" ></i>',
		active: false,
		className: "edit",
		title: gettext('Draw rectangle'),
		interaction: self.drawRectangleInteraction,
		onToggle: function(active){
			if (active) {
				self.map.removeInteraction(self.drawPolygonInteraction);
				self.map.addInteraction(self.drawRectangleInteraction);
			} else {
				self.map.removeInteraction(self.drawRectangleInteraction);
				self.map.addInteraction(self.drawPolygonInteraction);
			}
		}
	});
}

CatalogMap.prototype.getDrawPolygonControl = function(toolbar, map){
	var self = this;
	this.drawPolygonInteraction = new ol.interaction.Draw({
		type: 'Polygon'
	});

	this.drawPolygonInteraction.on('drawstart', function (evt) {
		self.vector_source.clear();
	});
	
	this.drawPolygonInteraction.on('drawend',
		function(evt) {
			self.selected_feat = evt.feature;
			self.vector_source.addFeatures([self.selected_feat]);
			self.catalog.filterCatalog();
		}, this);
	
	
	return new ol.control.Toggle({	
		html: '<i class="fa fa-code-fork" ></i>',
		active: false,
		title: gettext('Draw polygon'),
		interaction: self.drawPolygonInteraction,
		onToggle: function(active){
			if (active) {
				self.map.removeInteraction(self.drawRectangleInteraction);
				self.map.addInteraction(self.drawPolygonInteraction);
			} else {
				self.map.removeInteraction(self.drawPolygonInteraction);
				self.map.addInteraction(self.drawRectangleInteraction);
			}
		}
	});
}

CatalogMap.prototype.getClearControl = function(map){
	var self = this;
	return new ol.control.Button ({	html: '<i class="fa fa-eraser"></i>',
		title: gettext("Clear selected area"),
		handleClick: function() {
			self.cleanData();
			self.catalog.filterCatalog();
		}
	});
}

CatalogMap.prototype.isSpatialFilterEnabled = function() {
	return document.getElementById("chck_mapareaoverlap").checked;
}

CatalogMap.prototype.initialization = function(container_id){
	var self = this;
	this.vector_source = new ol.source.Vector();
	var lineStyle = new ol.style.Style({
		stroke: new ol.style.Stroke({
			color: '#ffcc33',
			width: 3
		}),
		fill: new ol.style.Fill({
			color: [0, 0, 255, 0]
		})
	});

	this.vector_layer = new ol.layer.Vector({
		source: this.vector_source,
		style: [lineStyle],
		zIndex: 999999
	});
	var mainMapView = viewer.core.getMap().getView();
	var baselayers = [];
	viewer.core.map.getLayers().forEach(function(l) {
		if (l.baselayer && !(l instanceof ol.layer.Vector)) {
			// required by layer switcher
			l.base = true;
			if (!l.title) {
				l.title = l.getProperties().label;
			}
			baselayers.push(l);
		}
	});
	if (baselayers.lenght == 0) {
		baseLayers.push(new ol.layer.Tile({
			source: new ol.source.OSM()
		}));
	}

	this.map = new ol.Map({
		target: container_id,
		layers: baselayers,
		view: new ol.View({
			center: mainMapView.getCenter(),
			zoom: 0,
			constrainResolution: true,
			projection: 'EPSG:3857',
		})
	});
	this.map.addLayer(this.vector_layer);

	// apply to the new map a similar extent compared to the main map
	var mainMapExtent = mainMapView.calculateExtent(viewer.core.getMap().getSize());
	var height = $('#' + container_id).height();
	var resolution = ol.extent.getHeight(mainMapExtent) / height;
	var zoom = Math.round(this.getZoomForResolution(resolution)) - 2;
	if (zoom < 0) {
		zoom = 0;
	}
	this.map.getView().setZoom(Math.floor(zoom));
	
	var mainBar = new ol.control.Bar();
	var groupBar = new ol.control.Bar({ toggleOne: true, group:true });
	mainBar.addControl(groupBar);
	var drawRectangleControl = this.getDrawRectangleControl(groupBar, this.map);
	groupBar.addControl(drawRectangleControl);
	var drawPolygonControl = this.getDrawPolygonControl(groupBar, this.map);
	groupBar.addControl(drawPolygonControl);
	var clearControl = this.getClearControl(this.map);
	mainBar.addControl(clearControl);
	this.map.addControl(mainBar);
}
