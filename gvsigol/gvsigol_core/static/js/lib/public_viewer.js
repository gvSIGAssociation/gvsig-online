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

var viewer = viewer || {};

/**
 * TODO
 */
viewer.core = {
		
	map: null,
	
	conf: null,
	
	toolbar: null,
	
	zoombar: null,
	
	tools: new Array(),
	
	legend: null,
	
	search: null,
	
	layerTree: null,
	
	layerCount: 0,
		
    initialize: function(conf) {
    	this.conf = conf;
    	this._createMap();
    	this._initToolbar();
    	this._loadLayers();
    	this._createWidgets();    	    	
    	this._loadTools();
    },
    
    _createMap: function() {
    	var self = this;
    	var blank = new ol.layer.Tile({
    		id: this._nextLayerId(),
    		label: gettext('Blank'),
          	visible: false,
    	    source: new ol.source.XYZ({
    	       url: "data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs="
    	    })
    	});
    	blank.baselayer = true;
    	
//    	var osm = new ol.layer.Tile({
//    		id: this._nextLayerId(),
//        	label: gettext('OpenStreetMap'),
//          	visible: true,
//          	source: new ol.source.OSM()
//        });
//		osm.baselayer = true;
		
		var mousePositionControl = new ol.control.MousePosition({
	        coordinateFormat: ol.coordinate.createStringXY(4),
	        projection: 'EPSG:4326',
	        className: 'custom-mouse-position-output',
	        target: document.getElementById('custom-mouse-position-output'),
	        undefinedHTML: '----------, ----------'
	    });
		
		this.zoombar = new ol.control.Zoom();
		
		var interactions = ol.interaction.defaults({altShiftDragRotate:false, pinchRotate:false});
		this.map = new ol.Map({
			interactions: interactions,
      		controls: [
				this.zoombar,
				new ol.control.ScaleLine(),					
      			new ol.control.OverviewMap({collapsed: false}),
      			mousePositionControl
      		],
      		renderer: 'canvas',
      		target: 'map',
      		layers: [blank],
			view: new ol.View({
        		center: ol.proj.transform([parseFloat(self.conf.view.center_lon), parseFloat(self.conf.view.center_lat)], 'EPSG:4326', 'EPSG:3857'),
        		minZoom: 0,
        		maxZoom: 22,
            	zoom: self.conf.view.zoom
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
    
    _loadLayers: function() {
    	this._loadBaseLayers();
    	this._loadOverlays();
    	this._loadLayerGroups();
    },
    
    _createWidgets: function() {   
    	this.layerTree = new layerTree(this.conf, this.map);
    	this.legend = new legend(this.conf, this.map);
    },
    
    _loadBaseLayers: function() {		
	    var self = this;
    	var base_layers = this.conf.base_layers;
    	
    	var layers = this.map.getLayers();
     	
    	for(var i=0; i<base_layers.length; i++){
    		var base_layer = base_layers[i];
	    	if (base_layer['type'] == 'WMS') {
				var wmsSource = new ol.source.TileWMS({
					url: base_layer['url'],
					params: {'LAYERS': base_layer['layers'], 'FORMAT': base_layer['format'], 'VERSION': base_layer['version']}
				});
				var wmsLayer = new ol.layer.Tile({
					id: this._nextLayerId(),
					source: wmsSource,
					visible: base_layer['active']
				});
				wmsLayer.baselayer = true;
				this.map.addLayer(wmsLayer);
				
			} 
	    	if (base_layer['type'] == 'WMTS') {				
	    		var parser = new ol.format.WMTSCapabilities();
	    		var capabilities_url = base_layer['url'] + '?request=GetCapabilities' + '&version=' + base_layer['version'];
	    	      fetch(capabilities_url).then(function(response) {
	    	        return response.text();
	    	      }).then(function(text) {
	    	        var result = parser.read(text);

	    	        var options = ol.source.WMTS.optionsFromCapabilities(result, {
	  		          matrixSet: base_layer['matrixset'],
	  		          layer: base_layer['layers']
	  		        });

	    	        var ignSource3 = new ol.source.WMTS((options));
			        var ignLayer3 = new ol.layer.Tile({
				 		id: self._nextLayerId(),
				 		source: ignSource3,
				 		visible: base_layer['active']
				 	});
				 	ignLayer3.baselayer = true;
				 	self.map.addLayer(ignLayer3);
	    	      });
			}
	    	
	    	if (base_layer['type'] == 'Bing') {
	    		var bingLayer = new ol.layer.Tile({
					id: this._nextLayerId(),
					visible: base_layer['active'],
					label: base_layer['layers'],
					preload: Infinity,
					source: new ol.source.BingMaps({
						key: base_layer['key'],
						imagerySet: base_layer['layers']
					})
				});
				bingLayer.baselayer = true;
				this.map.addLayer(bingLayer);
	    	}
	    	
	    	if (base_layer['type'] == 'OSM') {
	    		var osm_source = null;
	    		if('url' in base_layer && base_layer['url'].length > 0){
	    			osm_source = new ol.source.OSM({
	    				url: base_layer['url']
	    			})
	    		}else{
	    			osm_source = new ol.source.OSM();
	    		}
	    		var osm = new ol.layer.Tile({
	        		id: this._nextLayerId(),
	            	label: base_layer['title'],
	              	visible: base_layer['active'],
	              	source: osm_source
	            });
	    		osm.baselayer = true;
				this.map.addLayer(osm);
			}
	    	
	    	if (base_layer['type'] == 'XYZ') {
	    		var xyz = new ol.layer.Tile({
	    			id: this._nextLayerId(),
	    			label: base_layer['title'],
	    		  	visible: base_layer['active'],
	    		  	source: new ol.source.XYZ({
	    		  		url: base_layer['url']	
	    		    })
	    		});
	    		xyz.baselayer = true;
				this.map.addLayer(xyz);
			}
	    	
    	}
	},
	
	_loadOverlays: function() {
		var self = this;
		for (var i=0; i<this.conf.layerGroups.length; i++) {			
			var group = this.conf.layerGroups[i];
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
					var wmsParams = {
						'LAYERS': layerConf.workspace + ':' + layerConf.name, 
						'FORMAT': 'image/png', 
						'VERSION': '1.1.1'
					};
					if (layerConf.cached) {
						wmsParams['WIDTH'] = self.conf.tile_size;
						wmsParams['HEIGHT'] = self.conf.tile_size;
					}
					var wmsSource = new ol.source.TileWMS({
						url: url,
						visible: layerConf.visible,
						params: wmsParams,
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
				wmsLayer.order = layerConf.order;
				wmsLayer.styles = layerConf.styles;
				wmsLayer.setZIndex(parseInt(layerConf.order));
				wmsLayer.conf = JSON.parse(layerConf.conf);
				wmsLayer.parentGroup = group;
				
				this.map.addLayer(wmsLayer);
			}
		}
	},
	
	_loadLayerGroups: function() {
		var self = this;
		for (var i=0; i<this.conf.layerGroups.length; i++) {			
			var group = this.conf.layerGroups[i];
			var url = null;
			var cached = group.cached;
			
			if (cached) {
				url = this.conf.geoserver_base_url + '/gwc/service/wms';
			} else {
				url = this.conf.geoserver_base_url + '/wms';
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
			layerGroup.wms_url = this.conf.geoserver_base_url + '/wms';
			layerGroup.wfs_url = this.conf.geoserver_base_url + '/wfs';
			layerGroup.title = group.groupTitle;
			layerGroup.legend = this.conf.geoserver_base_url + '/wms' + '?SERVICE=WMS&VERSION=1.1.1&layer=' + group.groupName + '&REQUEST=getlegendgraphic&FORMAT=image/png';
			layerGroup.queryable = true;
			layerGroup.isLayerGroup = true;
			layerGroup.setZIndex(parseInt(group.groupOrder));
			this.map.addLayer(layerGroup);
		}
	},
	
	_loadTools: function() {
		this.tools.push(new projectZoom(this.map, this.conf));
    	this.tools.push(new getFeatureInfo(this.map, this.conf.tools.get_feature_info_control.private_fields_prefix));
    	this.tools.push(new measureLength(this.map));
    	this.tools.push(new measureArea(this.map));
    	this.tools.push(new exportToPDF(this.conf, this.map));
    	this.tools.push(new searchByCoordinate(this.conf, this.map));
    	this.tools.push(new geolocation(this.map));
    	this.tools.push(new cleanMap(this.map));
    	this.map.tools = this.tools;
    },
    
    loadTool: function(tool) {
    	this.tools.push(tool);
    	this.map.tools.push(tool);
    },
    
    getTool: function(id) {
    	var tool = null;
    	for (var i=0; i<this.tools.length; i++) {
    		if (this.tools[i].id == id) {
    			tool = this.tools[i];
    		}
    	}
    	return tool;
    },
    
    getMap: function(){
    	return this.map;
    },
    
    getConf: function(){
    	return this.conf;
    },
    
    _nextLayerId: function() {
    	return "gol-layer-" + this.layerCount++;
    }
}