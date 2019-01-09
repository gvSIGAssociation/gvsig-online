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

	overviewmap: null,

    initialize: function(conf, extraParams) {
    	this.conf = conf;
    	if (!conf.remote_auth) {
    		this._authenticate();
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
    	$.ajax({
			url: self.conf.geoserver_frontend_url + '/wms',
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
		//this.overviewmap = new ol.control.OverviewMap({collapsed: false, layers:default_layers});
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

		/*var highlight = new ol.interaction.Select({
	        condition: ol.events.condition.pointerMove,
	        style: function(feature, resolution){
	            var layer_name = feature.getId().split('.')[0];
	            var wfsLayer = self._getWfsLayer(layer_name);
	            var style = new ol.style.Style({
	                stroke: new ol.style.Stroke({
	                    color: wfsLayer.getStyle().getStroke().getColor(),
	                    width: wfsLayer.getStyle().getStroke().getWidth() + 3
	                }),
	                fill: wfsLayer.getStyle().getFill(),
	                zIndex: 999999
	            });
	            return style;
	        }
	    });

		this.map.addInteraction(highlight);*/

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

		/*this.wfsLayers = new Array();
		this.map.getView().once('change:resolution', function(evt) {
			self.map.once('moveend', function(evt) {
				self._handleWfsLayers(evt);
			});
		});*/
    },

    /*_wfsLayerExists: function (lname) {
    	var exists = false;
    	for (var k=0; k<this.wfsLayers.length; k++) {
    		if (this.wfsLayers[k] == lname) {
    			exists = true;
    		}
    	}
    	return exists;
    },*/

    /*_getWfsLayer: function(lname) {
    	var layers = this.map.getLayers().getArray();
    	for (var i=0; i<layers.length; i++) {
    		if (layers[i].getSource() instanceof ol.source.Vector) {
    			if (layers[i].layer_name == lname){
    				return layers[i];
    			}
    		}
    	}
    },*/

    /*_getCurrentScale: function () {
        var view = this.map.getView();
        var resolution = view.getResolution();
        var units = this.map.getView().getProjection().getUnits();
        var dpi = 25.4 / 0.28;
        var mpu = ol.proj.METERS_PER_UNIT[units];
        var scale = resolution * mpu * 39.37 * dpi;
        return scale;
    },*/

    /*_handleWfsLayers: function(evt){
    	var self = this;
    	this._refreshWfsLayers();
    	var layers = this.map.getLayers().getArray();
    	for (var i=0; i<layers.length; i++) {
    		var l = layers[i];
    		if (!l.baselayer) {
    			if (l.is_vector && (l.highlight == true)) {
    				if (l.highlight_scale >= 0) {
    					if (!this._wfsLayerExists(l.layer_name)){
    	    				if (this._getCurrentScale() < l.highlight_scale) {
    	    					if (l.getVisible()) {
    	    						this._addWfsLayer(l);
    	    					}
        					}

        				} else if (this._getCurrentScale() > l.highlight_scale) {
        					if (l.getSource() instanceof ol.source.Vector) {
        						if (this._wfsLayerExists(l.layer_name)){
        							this._removeWfsLayer(l);
        							var i = this.wfsLayers.indexOf(l.layer_name);
        							if(i != -1) {
        								this.wfsLayers.splice(i, 1);
        							}
        		    			}
        					}
        				}
    				}
    			}
    		}
    	}
    	evt.map.once('moveend', function(evt) {
    		self._handleWfsLayers(evt);
    	});
    },*/

    /*_addWfsLayer: function(layer) {
    	var vectorSource = new ol.source.Vector({
	        format: new ol.format.GeoJSON(),
	        url: function(extent) {
	            var geomExtent = self.map.getView().calculateExtent([900, 600]);
	        	var wfsUrl = layer.wfs_url + '?service=WFS&version=2.0.0&request=GetFeature&typename=' + layer.layer_name + '&maxFeatures=100&outputFormat=application/json&srsname=EPSG:3857&bbox=' + geomExtent.join(',') + ',EPSG:3857';
	        	return wfsUrl;
	        },
	        strategy: ol.loadingstrategy.bbox
		});

    	var style = this._getWfsStyle(layer.layer_name);

		var wfsLayer = new ol.layer.Vector({
			source: vectorSource,
			visible: true,
	        style: style
		});

		wfsLayer.baselayer = false;
		wfsLayer.layer_name = layer.layer_name;
		wfsLayer.wfs_url = layer.wfs_url;
		wfsLayer.wfs_url_no_auth = layer.wfs_url_no_auth;
		wfsLayer.highlight = layer.highlight;
		wfsLayer.highlight_scale = layer.highlight_scale;
		wfsLayer.is_vector = layer.is_vector;
		wfsLayer.namespace = layer.namespace;
		wfsLayer.workspace = layer.workspace;
		wfsLayer.crs = layer.crs;
		wfsLayer.order = layer.order;
		wfsLayer.setZIndex(999999);
		wfsLayer.conf = layer.conf;
		wfsLayer.parentGroup = layer.parentGroup;

		this.map.addLayer(wfsLayer);
		this.wfsLayers.push(layer.layer_name);
    },*/

    /*_removeWfsLayer: function(layer) {
    	this.map.removeLayer(layer);
    },*/

    /*_refreshWfsLayers: function() {
    	var layers = this.map.getLayers().getArray();
    	for (var i=0; i<layers.length; i++) {
    		if (layers[i].getSource() instanceof ol.source.Vector) {
    			if (this._wfsLayerExists(layers[i].layer_name)){
    				layers[i].getSource().clear();
        			layers[i].getSource().refresh();
    			}
    		}
    	}
    },*/

    /*_hexToRGB: function(hex, alpha) {
        var r = parseInt(hex.slice(1, 3), 16),
            g = parseInt(hex.slice(3, 5), 16),
            b = parseInt(hex.slice(5, 7), 16);

        if (alpha) {
            return "rgba(" + r + ", " + g + ", " + b + ", " + alpha + ")";
        } else {
            return "rgb(" + r + ", " + g + ", " + b + ")";
        }
    },*/

    /*_getWfsStyle: function(layer_name) {
    	var self = this;
    	var style = null;
    	$.ajax({
    		type: 'POST',
    		async: false,
    	  	url: '/gvsigonline/symbology/get_wfs_style/',
    	  	data: {
    	  		'layer_name': layer_name
    		},
    	  	success	:function(response){
    	  		var jsonStyle = JSON.parse(response.style.json);

    	  		var fillColor = self._hexToRGB(jsonStyle[0].fields.fill, jsonStyle[0].fields.fill_opacity);
    	  		var fill = new ol.style.Stroke({
	        		color: fillColor
	        	});

    	  		var strokeColor = self._hexToRGB(jsonStyle[0].fields.stroke, jsonStyle[0].fields.stroke_opacity);
    	  		var stroke = new ol.style.Stroke({
	        		color: strokeColor,
	        		width: jsonStyle[0].fields.stroke_width
	        	});

    	  		style = new ol.style.Style({
    	        	stroke: stroke,
    	        	fill: fill
    	        })
    		},
    	  	error: function(){}
    	});

    	return style;
    },*/

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
						if("crs" in layerConf && "crs" in layer.crs){
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
				url = this.conf.geoserver_frontend_url + '/gwc/service/wms';
				params = {'LAYERS': group.groupName, 'FORMAT': 'image/png', 'VERSION': '1.1.1'};
			} else {
				url = this.conf.geoserver_frontend_url + '/wms';
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
			layerGroup.wms_url = this.conf.geoserver_frontend_url + '/wms';
			layerGroup.wms_url_no_auth = this.conf.geoserver_frontend_url + '/wms';
			layerGroup.wfs_url = this.conf.geoserver_frontend_url + '/wfs';
			layerGroup.title = group.groupTitle;
			layerGroup.legend = this.conf.geoserver_frontend_url + '/wms' + '?SERVICE=WMS&VERSION=1.1.1&layer=' + group.groupName + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on';
			layerGroup.legend_no_auth = this.conf.geoserver_frontend_url + '/wms' + '?SERVICE=WMS&VERSION=1.1.1&layer=' + group.groupName + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on';
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

    getLayerTree: function() {
    	return this.layerTree;
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
    }

}