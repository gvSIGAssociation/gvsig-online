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

var viewer = viewer || {};

/**
 * TODO
 */
viewer.core = {
		
	map: null,
	
	toolbar: null,
	
	tools: new Array(),
	
	legend: null,
	
	search: null,
	
	layerTree: null,
	
	layerCount: 0,
		
    initialize: function(conf) {
    	this._createMap(conf);
    	this._initToolbar();
    	this._loadLayers(conf);
    	this._createWidgets(conf);    	    	
    	this._loadTools(conf);
    },
    
    _createMap: function(conf) {
    	
    	var blank = new ol.layer.Tile({
    		id: this._nextLayerId(),
    		label: gettext('Blank'),
          	visible: false,
    	    source: new ol.source.XYZ({
    	       url: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWNgYGD4DwABBAEAHnOcQAAAAABJRU5ErkJggg=="
    	    })
    	});
    	
    	var osm = new ol.layer.Tile({
    		id: this._nextLayerId(),
        	label: gettext('OpenStreetMap'),
          	visible: true,
          	source: new ol.source.OSM()
        });
		osm.baselayer = true;
		
		var mousePositionControl = new ol.control.MousePosition({
	        coordinateFormat: ol.coordinate.createStringXY(4),
	        projection: 'EPSG:4326',
	        className: 'custom-mouse-position-output',
	        target: document.getElementById('custom-mouse-position-output'),
	        undefinedHTML: '----------, ----------'
	    });
		
		this.map = new ol.Map({
			interactions: ol.interaction.defaults().extend([
			    new ol.interaction.DragRotateAndZoom()
			]),
      		controls: [
				new ol.control.Zoom(),
				new ol.control.ScaleLine(),					
      			new ol.control.OverviewMap({collapsed: false}),
      			mousePositionControl
      		],
      		renderer: 'canvas',
      		target: 'map',
      		layers: [blank, osm],
			view: new ol.View({
        		center: ol.proj.transform([parseFloat(conf.view.center_lon), parseFloat(conf.view.center_lat)], 'EPSG:4326', 'EPSG:3857'),
        		minZoom: 0,
        		maxZoom: 19,
            	zoom: conf.view.zoom
        	})
		});
		
		var projectionSelect = document.getElementById('custom-mouse-position-projection');
	    projectionSelect.addEventListener('change', function(event) {
	    	mousePositionControl.setProjection(ol.proj.get(event.target.value));
	    });
		
		$(document).on('sidebar:opened', function(){
			$('.ol-scale-line').css('left', '408px');
			$('.custom-mouse-position').css('left', '580px');
		});
		
		$(document).on('sidebar:closed', function(){
			$('.ol-scale-line').css('left', '8px');
			$('.custom-mouse-position').css('left', '180px');
		});
    },
    
    _initToolbar: function() {
    	var self = this;
    	
    	if (ol.has.TOUCH) {
    		$(".toolbar-button").css("font-size", "1.5em");
    	}
    	
    	$('#toolbar').on( "control-active", function(e) {
    		  for (var i=0; i<self.tools.length; i++){
    			  if (e.target.id != self.tools[i].id) {
    				  if (self.tools[i].deactivable == true) {
    					  if (self.tools[i].active) {
        					  self.tools[i].deactivate();
        				  }
    				  }
    			  }
    		  }
    		  if (self.layerTree.getEditionBar()) {
    			  self.layerTree.getEditionBar().deactivateControls(); 
    		  }   		  
    	});
    },
    
    _loadLayers: function(conf) {
    	this._loadBaseLayers(conf);
    	this._loadOverlays(conf);
    	this._loadLayerGroups(conf);
    },
    
    _createWidgets: function(conf) {   
    	this.layerTree = new layerTree(conf, this.map, false);
    	this.legend = new legend(conf, this.map);
    },
    
    _loadBaseLayers: function(conf) {		
		//BING LAYERS
    	if (conf.base_layers.bing.active) {
    		var bingTypes = [
    		    'Road',
    		    'Aerial',
    		    'AerialWithLabels'
    		];
    		var i, ii;
    		for (i = 0, ii = bingTypes.length; i < ii; ++i) {
    			var bingLayer = new ol.layer.Tile({
    				id: this._nextLayerId(),
    				visible: false,
    				label: bingTypes[i],
    				preload: Infinity,
    				source: new ol.source.BingMaps({
    					key: conf.base_layers.bing.key,
    					imagerySet: bingTypes[i]
    				})
    			});
    			bingLayer.baselayer = true;
    			this.map.addLayer(bingLayer);
    		}
    	}
	},
	
	_loadOverlays: function(conf) {
		var self = this;
		for (var i=0; i<conf.layerGroups.length; i++) {			
			var group = conf.layerGroups[i];
			for (var k=0; k<group.layers.length; k++) {
				var layerConf = group.layers[k];
				var layerId = this._nextLayerId();
				layerConf.id = layerId;
				var url = layerConf.wms_url;
				if (layerConf.cached) {
					url = layerConf.cache_url;
				}
				
				var wmsLayer = null;
				if (layerConf.single_image) {
					var wmsSource = new ol.source.ImageWMS({
						url: url,
						visible: layerConf.visible,
						params: {'LAYERS': layerConf.workspace + ':' + layerConf.name, 'FORMAT': 'image/png', 'VERSION': '1.1.1'},
						serverType: 'geoserver'
					});
					wmsLayer = new ol.layer.Image({
						id: layerId,
						source: wmsSource,
						visible: layerConf.visible
					});
					
				} else {
					var wmsSource = new ol.source.TileWMS({
						url: url,
						visible: layerConf.visible,
						params: {'LAYERS': layerConf.workspace + ':' + layerConf.name, 'FORMAT': 'image/png', 'VERSION': '1.1.1'},
						serverType: 'geoserver'
					});
					wmsLayer = new ol.layer.Tile({
						id: layerId,
						source: wmsSource,
						visible: layerConf.visible
					});
				}
				
				wmsLayer.on('change:visible', function(){
					self.legend.reloadLegend();
				});
				wmsLayer.baselayer = false;
				wmsLayer.layer_name = layerConf.name;
				wmsLayer.wms_url = layerConf.wms_url;
				wmsLayer.wfs_url = layerConf.wfs_url;
				wmsLayer.cache_url = layerConf.cache_url;
				wmsLayer.title = layerConf.title;
				wmsLayer.abstract = layerConf.abstract;
				wmsLayer.metadata = layerConf.metadata;
				wmsLayer.legend = layerConf.legend;
				wmsLayer.queryable = layerConf.queryable;
				wmsLayer.is_vector = layerConf.is_vector;
				wmsLayer.write_roles = layerConf.write_roles;
				wmsLayer.namespace = layerConf.namespace;
				wmsLayer.workspace = layerConf.workspace
				wmsLayer.crs = layerConf.crs;
				wmsLayer.order = layerConf.order;
				wmsLayer.setZIndex(parseInt(layerConf.order));
				this.map.addLayer(wmsLayer);
			}
		}
	},
	
	_loadLayerGroups: function(conf) {
		var self = this;
		for (var i=0; i<conf.layerGroups.length; i++) {			
			var group = conf.layerGroups[i];
			var url = null;
			var cached = group.cached;
			
			if (cached) {
				url = conf.geoserver_base_url + '/gwc/service/wms';
			} else {
				url = conf.geoserver_base_url + '/wms';
			}
			
			var layerGroupSource = new ol.source.TileWMS({
				url: url,
				params: {'LAYERS': group.groupName, 'FORMAT': 'image/png', 'VERSION': '1.1.1'},
				//crossOrigin: '*',
				serverType: 'geoserver'
			});
			var layerGroup = new ol.layer.Tile({			
				id: group.groupName,
				source: layerGroupSource,
				visible: false
			});
				
			layerGroup.on('change:visible', function(){
				self.legend.reloadLegend();
			});
			layerGroup.baselayer = false;
			layerGroup.layer_name = group.groupName;
			layerGroup.wms_url = conf.geoserver_base_url + '/wms';
			layerGroup.wfs_url = conf.geoserver_base_url + '/wfs';
			layerGroup.title = group.groupTitle;
			layerGroup.legend = conf.geoserver_base_url + '/wms' + '?SERVICE=WMS&VERSION=1.1.1&layer=' + group.groupName + '&REQUEST=getlegendgraphic&FORMAT=image/png';
			layerGroup.queryable = true;
			layerGroup.isLayerGroup = true;
			layerGroup.setZIndex(parseInt(group.groupOrder));
			this.map.addLayer(layerGroup);
		}
	},
	
	_loadTools: function(conf) {
    	this.tools.push(new getFeatureInfo(this.map, conf.tools.get_feature_info_control.private_fields_prefix));
    	this.tools.push(new measureLength(this.map));
    	this.tools.push(new measureArea(this.map));
    	this.tools.push(new exportToPDF(conf, this.map));
    	this.tools.push(new searchByCoordinate(conf, this.map));
    	this.tools.push(new geolocation(this.map));
    	this.map.tools = this.tools;
    },
    
    loadTool: function(tool) {
    	this.tools.push(tool);
    	this.map.tools.push(tool);
    },
    
    getMap: function(){
    	return this.map;
    },
    
    _nextLayerId: function() {
    	return "gol-layer-" + this.layerCount++;
    }
}