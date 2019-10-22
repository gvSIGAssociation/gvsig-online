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

CatalogMap.prototype.refreshData = function(features){
//	this.map.removeLayer(this.vector_layer);
//	var feats = [];
//	
//	for(var i=0; i<features.length; i++){
//		var feature = new ol.Feature({
//		    geometry: lineString,
//		    name: 'Polygon'
//		});
//		feats.push(feature);
//	}
//
//	var lineStyle = new ol.style.Style({
//	    stroke: new ol.style.Stroke({
//	        color: '#ffcc33',
//	        width: 3
//	    }),
//        fill: new ol.style.Fill({
//            color: [0, 0, 255, 0]
//        })
//	});
//	
//	this.vector_source = new ol.source.Vector({
//		features: feats
//	});
//	this.vector_layer = new ol.layer.Vector({
//		source: this.vector_source,
//		style: [lineStyle]
//	});
//	
//	this.map.addLayer(this.vector_layer);
}

CatalogMap.prototype.getSelectedArea = function(){
	if (document.getElementById("chck_mapareaoverlap").checked) {
		var extent = this.map.getView().calculateExtent();
		var geom = ol.geom.Polygon.fromExtent(extent);
		var format =  new ol.format.WKT();
		return format.writeGeometry(geom, {dataProjection: 'EPSG:4326', featureProjection: this.map.getView().getProjection()});
	}
	return null;
}


CatalogMap.prototype.getDrawnArea = function(){
	if (document.getElementById("chck_mapareaoverlap").checked && this.selected_feat != null){
		var geom = this.selected_feat.getGeometry();
		var format =  new ol.format.WKT();
		return format.writeGeometry(geom, {dataProjection: 'EPSG:4326', featureProjection: this.map.getView().getProjection()});
	}
	return null;
}

CatalogMap.prototype.initialization = function(container_id){
	var self = this;
	this.vector_source = new ol.source.Vector();
	this.vector_layer = new ol.layer.Vector({
        source: this.vector_source
    });
	
	this.interaction = new ol.interaction.DragBox({
	    condition: ol.events.condition.platformModifierKeyOnly
	});
	
	this.interaction.on('boxstart', function (evt) {
		self.vector_source.clear();
	});
	
	this.interaction.on('boxend', function (evt) {
	    var geom = evt.target.getGeometry();
	    console.log(geom);
	    self.selected_feat = new ol.Feature({
	    	name: "selected_area",
	        geometry: geom
	    });
	    self.vector_source.addFeatures([self.selected_feat]);
	    
	    self.catalog.filterCatalog();
	});

	var mainMapView = viewer.core.map.getView();
	var baselayers = [];
	viewer.core.map.getLayers().forEach(function(l) {
		if (l.baselayer) {
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
	var mainMapExtent = mainMapView.calculateExtent();
	// apply a similar extent to the new map
	var resolution = ol.extent.getHeight(mainMapExtent) / size[1];
	this.map = new ol.Map({
	    target: container_id,
	    layers: baselayers,
	    view: new ol.View({
	        center: mainMapView.getCenter(),
	        resolution: resolution,
	        constrainResolution: true,
	        projection: 'EPSG:3857',
	    })
	});
	
	this.map.addInteraction(this.interaction);
}