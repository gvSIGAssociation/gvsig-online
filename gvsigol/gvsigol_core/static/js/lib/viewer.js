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

	selectedFeatures: {},

	selectedFeatureIds: {},

	selectedFeatureSource: null,

	overviewmap: null,

    initialize: function(conf, extraParams) {
    	this.conf = conf;
    	if (conf.user) {
    		if (!conf.remote_auth) {
        		this._authenticate();
        	}
    	}
    	this.extraParams = extraParams;
    	this._createMap();
    	this._initToolbar();
    	this._loadLayers();
    	this._createWidgets();
    	this._loadTools();
    },

    _authenticate: function() {
    	var self = this;
    	for (var i=0; i<self.conf.auth_urls.length; i++) {
    		$.ajax({
    			url: self.conf.auth_urls[i],
    			params: {
    				'SERVICE': 'WMS',
    				'VERSION': '1.1.1',
    				'REQUEST': 'GetCapabilities'
    			},
    			async: false,
    			method: 'GET',
    			headers: {
    				"Authorization": "Basic " + btoa(self.conf.user.credentials.username + ":" + self.conf.user.credentials.password)
    			},
    			error: function(jqXHR, textStatus, errorThrown){},
    			success: function(){
    				console.log('Authenticated');
    			}
    		});
    	}
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
    	var default_layers = [blank]

		var mousePositionControl = new ol.control.MousePosition({
	        coordinateFormat: ol.coordinate.createStringXY(4),
	        projection: 'EPSG:4326',
	        className: 'custom-mouse-position-output',
	        target: document.getElementById('custom-mouse-position-output'),
	        undefinedHTML: '----------, ----------'
	    });

		this.zoombar = new ol.control.Zoom();

		var osm = new ol.layer.Tile({
    		source: new ol.source.OSM()
    	});

		var interactions = ol.interaction.defaults({altShiftDragRotate:false, pinchRotate:false});
		this.overviewmap = new ol.control.OverviewMap({collapsed: false, layers: [osm]});
		this.map = new ol.Map({
			interactions: interactions,
      		controls: [
      			this.zoombar,
				new ol.control.ScaleLine(),
      			this.overviewmap,
      			mousePositionControl
      		],
      		renderer: 'canvas',
      		target: 'map',
      		layers: default_layers,
			view: new ol.View({
        		center: ol.proj.transform([parseFloat(self.conf.view.center_lon), parseFloat(self.conf.view.center_lat)], 'EPSG:4326', 'EPSG:3857'),
        		minZoom: 0,
        		maxZoom: self.conf.view.max_zoom_level,
            	zoom: self.conf.view.zoom
        	})
		});

		this.extentLayer = new ol.layer.Vector({
			source: new ol.source.Vector()
		});
		this.map.addLayer(this.extentLayer);

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
    	this.layerTree = new layerTree(this.conf, this.map, this);
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
					crossOrigin: 'anonymous',
					params: {'LAYERS': base_layer['layers'], 'FORMAT': base_layer['format'], 'VERSION': base_layer['version']}
				});
				var wmsLayer = new ol.layer.Tile({
					id: "gol-layer-" + (i+1),
					source: wmsSource,
					visible: base_layer['active']
				});
				wmsLayer.baselayer = true;
				this.map.addLayer(wmsLayer);
				base_layer['id'] = this.layerCount;
				this._nextLayerId();
			}
	    	if (base_layer['type'] == 'WMTS') {
	    		var parser = new ol.format.WMTSCapabilities();
	    		var capabilities_url = base_layer['url'] + '?request=GetCapabilities' + '&version=' + base_layer['version']  + '&service=' + base_layer['type'];
	    	      fetch(capabilities_url).then(function(response) {
	    	    	  return response.text();
	    	      }).then(function(text) {
	    	        var result = parser.read(text);
	    	        for(var j=0; j<base_layers.length; j++){
	    	    		var base_layer2 = base_layers[j];
	    		    	if (base_layer2['type'] == 'WMTS') {
	    		    		try{
	    		    		 var options = ol.source.WMTS.optionsFromCapabilities(result, {
	    		  		          matrixSet: base_layer2['matrixset'],
	    		  		          layer: base_layer2['layers']
	    		  		        });
	    		    		 if(options && options.urls && options.urls.length > 0){
	    		    			 if(!base_layer2['url'].endsWith('?')){
	    		    				 options.urls[0] = base_layer2['url'] + '?';
	    		    			 }
	    		    		 }
	    		    		 var is_baselayer = false;
	    		    		 for(var k=0; k<options.urls.length; k++){
	    		    			 if(base_layer2['url'].replace("https://", "http://")+'?' == options.urls[k].replace("https://", "http://")){
	    		    				 is_baselayer = true;
	    		    			 }
	    		    		 }
	    		    		 options.crossOrigin = 'anonymous';
	    		    		 if(is_baselayer){
				    	        var ignSource3 = new ol.source.WMTS((options));
						        var ignLayer3 = new ol.layer.Tile({
							 		id: "gol-layer-" + (j+1),
							 		source: ignSource3,
							 		visible: base_layer2['active']
							 	});
							 	ignLayer3.baselayer = true;
							 	self.map.addLayer(ignLayer3);
	    		    		 }
	    		    		}catch(err){
	    		    			//console.log("error loading wmts '" + base_layer2['url']+"':" + err)
	    		    		}
	    		    	}
	    	        }
	    	      });
	    	      this._nextLayerId();
			}

	    	if (base_layer['type'] == 'Bing') {
	    		var bingLayer = new ol.layer.Tile({
					id: "gol-layer-" + (i+1),
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
				base_layer['id'] = this.layerCount;
				this._nextLayerId();
	    	}

	    	if (base_layer['type'] == 'OSM') {
	    		var osm_source = null;
	    		if('url' in base_layer && base_layer['url'].length > 0){
	    			osm_source = new ol.source.OSM({
	    				url: base_layer['url'],
	    				crossOrigin: 'anonymous'
	    			})
	    		}else{
	    			osm_source = new ol.source.OSM();
	    		}
	    		var osm = new ol.layer.Tile({
	        		id: "gol-layer-" + (i+1),
	            	label: base_layer['title'],
	              	visible: base_layer['active'],
	              	source: osm_source
	            });
	    		osm.baselayer = true;
				this.map.addLayer(osm);
				base_layer['id'] = this.layerCount;
				this._nextLayerId();
			}

	    	if (base_layer['type'] == 'XYZ') {
	    		var xyz = new ol.layer.Tile({
	    			id: "gol-layer-" + (i+1),
	    			label: base_layer['title'],
	    		  	visible: base_layer['active'],
	    		  	source: new ol.source.XYZ({
	    		  		url: base_layer['url'],
	    		  		crossOrigin: 'anonymous'
	    		    })
	    		});
	    		xyz.baselayer = true;
				this.map.addLayer(xyz);
				base_layer['id'] = this.layerCount;
				this._nextLayerId();
			}

    	}
	},

	_loadOverlays: function() {
		var self = this;
		var ajaxRequests = new Array();
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

				var visible = layerConf.visible;
				if(group.visible){
					visible = false;
				}
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
						visible: visible
					});

				} else {
					if(url.endsWith('/gwc/service/wmts')){
						var default_srs = 'EPSG:3857';
						if("crs" in layerConf && "crs" in layerConf.crs){
							default_srs = layerConf.crs.crs;
						}

						var projection = new ol.proj.get(default_srs);
						var projectionExtent = projection.getExtent();
						var size = ol.extent.getWidth(projectionExtent) / 256;
						var resolutions = new Array(21);
						var matrixIds = new Array(21);
						for (var z = 0; z < 21; ++z) {
						    resolutions[z] = size / Math.pow(2, z);
						    matrixIds[z] = default_srs+':'+z;
						}

						var tileGrid = new ol.tilegrid.WMTS(
						        {
						            origin: ol.extent.getTopLeft(projectionExtent),
						            resolutions: resolutions,
						            matrixIds: matrixIds
						        }
						);


						var ignSource3 = new ol.source.WMTS({
							layer: layerConf.workspace + ':' + layerConf.name,
							url: url,
							projection: projection,
							matrixSet: default_srs,
							format:'image/png',
							tileGrid: tileGrid,
							crossOrigin: 'anonymous',
				            wrapX: true
						});
				        var wmsLayer = new ol.layer.Tile({
					 		id: layerId,
					 		source: ignSource3,
					 		visible: visible
					 	});
				        wmsLayer.baselayer = false;
				        wmsLayer.layer_name=layerConf.workspace + ':' + layerConf.name;

					}else{
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
							visible: visible
						});
					}
				}

				if(wmsLayer){
					wmsLayer.on('change:visible', function(){
						self.legend.reloadLegend();
					});
					wmsLayer.baselayer = false;
					wmsLayer.layer_name = layerConf.name;
					wmsLayer.wms_url = layerConf.wms_url;
					wmsLayer.wms_url_no_auth = layerConf.wms_url_no_auth;
					wmsLayer.wfs_url = layerConf.wfs_url;
					wmsLayer.wfs_url_no_auth = layerConf.wfs_url_no_auth;
					wmsLayer.cache_url = layerConf.cache_url;
					wmsLayer.title = layerConf.title;
					wmsLayer.abstract = layerConf.abstract;
					wmsLayer.metadata = layerConf.metadata;
					wmsLayer.legend = layerConf.legend;
					wmsLayer.legend_no_auth = layerConf.legend_no_auth;
					wmsLayer.legend_graphic = layerConf.legend_graphic;
					wmsLayer.legend_graphic_no_auth = layerConf.legend_graphic_no_auth;
					wmsLayer.queryable = layerConf.queryable;
					wmsLayer.highlight = layerConf.highlight;
					wmsLayer.highlight_scale = layerConf.highlight_scale;
					wmsLayer.is_vector = layerConf.is_vector;
					wmsLayer.write_roles = layerConf.write_roles;
					wmsLayer.namespace = layerConf.namespace;
					wmsLayer.workspace = layerConf.workspace
					wmsLayer.crs = layerConf.crs;
					wmsLayer.order = layerConf.order;
					wmsLayer.styles = layerConf.styles;
					wmsLayer.setZIndex(parseInt(layerConf.order));
					wmsLayer.conf = JSON.parse(layerConf.conf);
					wmsLayer.parentGroup = group.groupName;

					wmsLayer.time_resolution = layerConf.time_resolution;

					wmsLayer.setOpacity(layerConf.opacity);
					this.map.addLayer(wmsLayer);
				}
			}
		}
	},

	_loadLayerGroups: function() {
		var self = this;
		for (var i=0; i<this.conf.layerGroups.length; i++) {
			var group = this.conf.layerGroups[i];
			var url = null;
			var params = null;
			var cached = group.cached;

			if (cached) {
				url = group.cache_endpoint;
				params = {'LAYERS': group.groupName, 'FORMAT': 'image/png', 'VERSION': '1.1.1'};
			} else {
				url = group.wms_endpoint;
				params = {'LAYERS': group.groupName, 'FORMAT': 'image/png', 'VERSION': '1.1.0'};
			}

			var layerGroupSource = new ol.source.TileWMS({
				url: url,
				params: params,
				serverType: 'geoserver'
			});
			var layerGroup = new ol.layer.Tile({
				id: group.groupName,
				source: layerGroupSource,
				visible: group.visible
			});

			layerGroup.on('change:visible', function(){
				self.legend.reloadLegend();
			});
			layerGroup.baselayer = false;
			layerGroup.layer_name = group.groupName;
			layerGroup.wms_url = group.wms_endpoint;
			layerGroup.wms_url_no_auth = group.wms_endpoint;
			layerGroup.wfs_url = group.wfs_endpoint;
			layerGroup.title = group.groupTitle;
			layerGroup.legend = group.wms_endpoint + '?SERVICE=WMS&VERSION=1.1.1&layer=' + group.groupName + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on';
			layerGroup.legend_no_auth = group.wms_endpoint + '?SERVICE=WMS&VERSION=1.1.1&layer=' + group.groupName + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on';
			layerGroup.queryable = true;
			layerGroup.isLayerGroup = true;
			layerGroup.setZIndex(parseInt(group.groupOrder));
			this.map.addLayer(layerGroup);
		}
	},

	_loadTools: function() {
		if (this.ifToolInConf('gvsigol_tool_zoom')) {
			this.tools.push(new projectZoom(this.map, this.conf));
		}
		if (this.ifToolInConf('gvsigol_tool_info')) {
			this.tools.push(new getFeatureInfo(this.map, this.conf.tools.get_feature_info_control.private_fields_prefix));
		}
		if (this.ifToolInConf('gvsigol_tool_measure')) {
			this.tools.push(new measureLength(this.map));
			this.tools.push(new measureArea(this.map));
		}
		if (this.ifToolInConf('gvsigol_tool_export')) {
			this.tools.push(new exportToPDF(this.conf, this.map));
		}
		if (this.ifToolInConf('gvsigol_tool_location')) {
			this.tools.push(new geolocation(this.map));
		}
		if (this.ifToolInConf('gvsigol_tool_coordinate')) {
			this.tools.push(new searchByCoordinate(this.conf, this.map));
		}
		if (this.ifToolInConf('gvsigol_tool_coordinatecalc')) {
			this.tools.push(new coordinateCalculator(this.conf, this.map));
		}
		if (this.ifToolInConf('gvsigol_tool_shareview')) {
			this.tools.push(new shareView(this.conf, this.map, this.layerTree));
		}
		if (this.ifToolInConf('gvsigol_tool_selectfeature')) {
			this.tools.push(new selectFeature(this.map, this));
		}

		this.tools.push(new cleanMap(this.map, this));

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

    ifToolInConf: function(toolId) {
    	var toolInConf = false;
    	var tools = this.conf.project_tools;
    	for (var i=0; i < tools.length; i++) {
    		if (tools[i].name == toolId) {
    			toolInConf = tools[i].checked
    		}
    	}
    	return toolInConf;
    },

    getLayerTree: function() {
    	return this.layerTree;
    },

    getLegend: function() {
    	return this.legend;
    },

    getMap: function(){
    	return this.map;
    },

    getExtraParams: function(){
    	return this.extraParams;
    },

    getConf: function(){
    	return this.conf;
    },

    _nextLayerId: function() {
    	return "gol-layer-" + this.layerCount++;
    },

    addSelectedFeaturesSource: function(layer, features){
    	if(features.length == 0){
    		return;
    	}

    	if(!(layer in this.selectedFeatures)){
    		this.selectedFeatures[layer] = features;
    		this.getSelectedFeaturesSource();
        	if(this.selectedFeatureSource != null){
        		this.getSelectedFeaturesSource().addFeatures(features);
        	}
    	}else{
    		var featuresToAdd = [];
    		for(var j=0; j<features.length; j++){
    			var founded = false;
	    		for(var i=this.selectedFeatures[layer].length-1; i>=0; i--){
	    			if(this.selectedFeatures[layer][i].getId() == features[j].getId()){
	    				this.getSelectedFeaturesSource().removeFeature(this.selectedFeatures[layer][i]);
	    				this.selectedFeatures[layer].splice(i, 1);
	    				founded = true;
	    			}
	    		}
	    		if(!founded){
	    			featuresToAdd.push(features[j]);
	    		}
    		}
    		if(this.selectedFeatures[layer].length == 0){
    			this.selectedFeatures[layer] = featuresToAdd;
    		}else{
    			this.selectedFeatures[layer] = this.selectedFeatures[layer].concat(featuresToAdd);
    		}
    		this.getSelectedFeaturesSource();
        	if(this.selectedFeatureSource != null){
        		this.getSelectedFeaturesSource().addFeatures(featuresToAdd);
        	}
    	}

    	document.dispatchEvent(new Event("selectionChange"));

    },

    clearSelectedFeatures: function(layer){
    	if(this.selectedFeatures[layer] != null){
    		for(var i=0; i<this.selectedFeatures[layer].length; i++){
    			var feature = this.selectedFeatures[layer][i];
    			self.getSelectedFeaturesSource().removeFeature(feature);
    		}
    	}
    	this.selectedFeatures[layer] = [];

    	document.dispatchEvent(new Event("selectionChange"));
    },

    clearAllSelectedFeatures: function(){
    	this.selectedFeatures = {};
    	this.getSelectedFeaturesSource().clear();

    	document.dispatchEvent(new Event("selectionChange"));
    },

    getSelectedFeaturesForLayer: function(layer){
    	if(!(layer in this.selectedFeatures)){
    		return [];
    	}
    	return this.selectedFeatures[layer];
    },

    getSelectedFeaturesSource: function(){
    	if(this.selectedFeatureSource == null){
    		this.selectedFeatureSource = new ol.source.Vector();
    		var selectLayer = new ol.layer.Vector({
				source: this.selectedFeatureSource,
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
			this.map.addLayer(selectLayer);
			selectLayer.setZIndex(100000);
    	}

    	return this.selectedFeatureSource;
    }

}