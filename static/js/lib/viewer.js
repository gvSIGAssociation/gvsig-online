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
	
	activeToolbar: null,

	layerCount: 0,

	selectedFeatures: {},

	selectedFeatureIds: {},

	selectedFeatureSource: null,

	overviewmap: null,

	//Lista de botones para la tabla de atributos que se pueden registrar desde los plugins haciendo push
	attributeTableButtons: new Array(), 
	//Eventos de la tabla registrables desde plugins
	tableEvent: {
		'rowCallback': new Array()
	}, 

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
		if (self.conf.user && self.conf.user.credentials) {
			var headers;
			headers = {
				"Authorization": "Basic " + btoa(self.conf.user.credentials.username + ":" + self.conf.user.credentials.password)
			};
			for (var i=0; i<self.conf.auth_urls.length; i++) {
				$.ajax({
					url: self.conf.auth_urls[i] + "/wms",
					params: {
						'SERVICE': 'WMS',
						'VERSION': '1.1.1',
						'REQUEST': 'GetCapabilities'
					},
					async: true,
					xhrFields: {
						withCredentials: true
					},
					method: 'GET',
					headers: headers,
					error: function(jqXHR, textStatus, errorThrown){},
					success: function(resp){
						console.log('Authenticated');
					}
				});
			}
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
    	var default_layers = [blank];

		var mousePositionControl = new ol.control.MousePosition({
	        coordinateFormat: ol.coordinate.createStringXY(4),
	        projection: 'EPSG:4326',
	        className: 'custom-mouse-position-output',
	        target: document.getElementById('custom-mouse-position-output'),
	        undefinedHTML: '--------,--------'
	    });

		this.zoombar = new ol.control.Zoom();

		var osm = new ol.layer.Tile({
    		source: new ol.source.OSM({
    			url: 'https://{a-c}.tile.openstreetmap.de/{z}/{x}/{y}.png'
    		})
    	});

		var interactions = ol.interaction.defaults({altShiftDragRotate:false, pinchRotate:false, shiftDragZoom: false});
		this.overviewmap = new ol.control.OverviewMap({
			collapsed: false, 
			layers: [osm],
			collapseLabel: '»',
			label: '«'
		});
		
		var view = new ol.View({
    		center: ol.proj.transform([parseFloat(self.conf.view.center_lon), parseFloat(self.conf.view.center_lat)], 'EPSG:4326', 'EPSG:3857'),
    		minZoom: 0,
    		maxZoom: self.conf.view.max_zoom_level,
			zoom: self.conf.view.zoom/*,
			zoomFactor: 1.5*/
    	});
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
			view: view
		});
		
		if (self.conf.view.restricted_extent) {
			this.map.setView(
				new ol.View({
					extent: this.map.getView().calculateExtent(this.map.getSize()),   
					center: ol.proj.transform([parseFloat(self.conf.view.center_lon), parseFloat(self.conf.view.center_lat)], 'EPSG:4326', 'EPSG:3857'),
		    		minZoom: self.conf.view.zoom + 1,
		    		maxZoom: self.conf.view.max_zoom_level,
		        	zoom: self.conf.view.zoom + 1
				})
			);
		}
		if (self.conf.view.extent) {
			var view = self.map.getView();
			view.fit(self.conf.view.extent);
		}

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
			//$('.ol-bar').css('left', '408px');
			$('.custom-mouse-position').css('left', '580px');
		});

		$(document).on('sidebar:closed', function(){
			$('.ol-scale-line').css('left', '8px');
			//$('.ol-bar').css('left', '8px');
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
    	var self = this;
		var ajaxRequests = new Array();
		for (var i=0; i<this.conf.layerGroups.length; i++) {
			var group = this.conf.layerGroups[i];
			for (var k=0; k<group.layers.length; k++) {
				var layerConf = group.layers[k];
				var checkTileLoadError = this.conf.check_tileload_error;
				if (layerConf.external) {
					this._loadExternalLayer(layerConf, group, checkTileLoadError);
				} else {
					this._loadInternalLayer(layerConf, group, checkTileLoadError);
				}

			}
		}
    	this._loadLayerGroups();
    },

    _createWidgets: function() {
    	this.layerTree = new layerTree(this.conf, this.map, this);
    	this.legend = new legend(this.conf, this.map);
		this.rawFilter = new RawFilter(this.conf, this.map);
		this.selectionTable = new SelectionTable(this.map);
    },

    _loadExternalLayer: function(externalLayer, group, checkTileLoadError) {
	    var self = this;

	    var visible = false;
	    var baselayer = false;
	    if (externalLayer['baselayer']) {
	    	baselayer = true;
	    	if (externalLayer['default_baselayer']) {
	    		visible = true;
	    	}
	    } else {
	    	visible = externalLayer['visible'];
	    }
	    if(group.visible){ visible = false; }

	    var layerId = this._nextLayerId();
	    externalLayer.id = layerId;

    	if (externalLayer['type'] == 'WMS') {
			var wmsSource = new ol.source.TileWMS({
				url: externalLayer['url'],
				crossOrigin: 'anonymous',
				params: {'LAYERS': externalLayer['layers'], 'FORMAT': externalLayer['format'], 'VERSION': externalLayer['version'], 'SRS': 'EPSG:3857', 'TRANSPARENT': 'TRUE'}
			});
			wmsSource.layer_name = externalLayer['name'];
			if (checkTileLoadError) {
				wmsSource.loadend = false;
				wmsSource.on('tileloadstart', function() {
					var time = 0;
					var pid;
					var _this = this;
					
					var eLayer = null;
					self.map.getLayers().forEach(function(layer){
						if (layer.layer_name == _this.layer_name) {
							eLayer = layer;
						}						
					}, _this);

					self._setTileLoadError(false, eLayer);
					pid = setInterval(function() {
						if (time < externalLayer['timeout']) {
							time += 1000;
						} else {
							if (!_this.loadend) {
								clearInterval(pid);
								if (eLayer) {
									self._setTileLoadError(true, eLayer);
								}
							}
		
						}
					}, 1000);
				
				});
				wmsSource.on('tileloadend', function() {
					this.loadend = true;
				
				});
				wmsSource.on('tileloaderror', function(e){
					var eLayer = null;
					self.map.getLayers().forEach(function(layer){
						if (layer.layer_name == this.layer_name) {
							eLayer = layer;
						}						
					}, this);
					
					if (eLayer) {
						if (this.getUrls()[0] == eLayer.cached_url) {
							self._setTileLoadError(true, eLayer);
							
						} else {
							if (eLayer.cached && eLayer.cached_url) {
								this.setUrl(eLayer.cached_url);
								this.updateParams({'LAYERS': eLayer.layer_name, 'FORMAT': eLayer.format, 'VERSION': eLayer.version, 'SRS': 'EPSG:3857', 'TRANSPARENT': 'TRUE'});
								
							} else {
								self._setTileLoadError(true, eLayer);
							}
						}
					}
					
					
				});
			}
			var wmsLayer = new ol.layer.Tile({
				id: layerId,
				source: wmsSource,
				visible: visible
			});
			
			wmsLayer.id = layerId;
			wmsLayer.wms_url = externalLayer['url'];
			wmsLayer.cached = externalLayer['cached'];
			wmsLayer.cached_url = externalLayer['cache_url'];
			wmsLayer.title = externalLayer['title'];
			wmsLayer.baselayer = baselayer;
			wmsLayer.queryable = true;
			wmsLayer.external = true;
			wmsLayer.imported = false;
			wmsLayer.detailed_info_enabled = externalLayer['detailed_info_enabled'];
			wmsLayer.detailed_info_button_title = externalLayer['detailed_info_button_title'];
			wmsLayer.detailed_info_html = externalLayer['detailed_info_html'];
			wmsLayer.layer_name = externalLayer['name'];			
			wmsLayer.setZIndex(parseInt(externalLayer.order));
			wmsLayer.infoFormat = externalLayer['infoformat'];
			wmsLayer.format = externalLayer['format'];
			wmsLayer.version = externalLayer['version'];
			if (!externalLayer['cached']) {
				wmsLayer.legend = externalLayer['url'] + '?SERVICE=WMS&VERSION=1.1.1&layer=' + externalLayer['layers'] + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on';
				wmsLayer.legend_no_auth = externalLayer['url'] + '?SERVICE=WMS&VERSION=1.1.1&layer=' + externalLayer['layers'] + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on';
			}
			wmsLayer.on('change:visible', function(){
				self.legend.reloadLegend();
			});

			this.map.addLayer(wmsLayer);
		}
    	
    	if (externalLayer['type'] == 'WMTS') {
    		
    		var xmlDoc = null;
    		try {
    			xmlDoc = jQuery.parseXML(JSON.parse(externalLayer['capabilities']));
    		} catch(err){
    			xmlDoc = jQuery.parseXML(externalLayer['capabilities']);
    			
    		}
    		
    		try {
    			var parser = new ol.format.WMTSCapabilities();
	    		var result = parser.read(xmlDoc);
	    		
	    		var options = ol.source.WMTS.optionsFromCapabilities(result, {
					matrixSet: externalLayer['matrixset'],
			        layer: externalLayer['layers']
			    });
				var is_baselayer = false;
				for(var k=0; k<options.urls.length; k++){
					if(externalLayer['url'].replace("https://", "http://")+'?' == options.urls[k].replace("https://", "http://")){
						is_baselayer = true;
					}
				}
				options.crossOrigin = 'anonymous';
	    		
				var wmtsSource = new ol.source.WMTS((options));
				wmtsSource.layer_name = externalLayer['name'];
				if (checkTileLoadError) {
					wmtsSource.loadend = false;
					wmtsSource.on('tileloadstart', function() {
						var time = 0;
						var pid;
						var _this = this;

						var eLayer = null;
						self.map.getLayers().forEach(function(layer){
							if (layer.layer_name == _this.layer_name) {
								eLayer = layer;
							}						
						}, _this);

						self._setTileLoadError(false, eLayer);

						pid = setInterval(function() {
							if (time < externalLayer['timeout']) {
								time += 1000;
							} else {
								if (!_this.loadend) {
									clearInterval(pid);
									if (eLayer) {
										self._setTileLoadError(true, eLayer);
									}
								}
			
							}
						}, 1000);
					
					});
					wmtsSource.on('tileloadend', function() {
						this.loadend = true;
					
					});
					wmtsSource.on('tileloaderror', function(e){
						var eLayer = null;
						self.map.getLayers().forEach(function(layer){
							if (layer.layer_name == this.layer_name) {
								eLayer = layer;
							}						
						}, this);
						
						if (eLayer) {
							self._setTileLoadError(true, eLayer);
						}
						
						
					});
				}
	    		var wmtsLayer = new ol.layer.Tile({
	    			id: layerId,
					source: wmtsSource,
					visible: visible
	    		});
	    		wmtsLayer.id = layerId;
	    		wmtsLayer.baselayer = externalLayer['baselayer'];
	    		wmtsLayer.external = true;
	    		wmtsLayer.queryable = false;
	    		wmtsLayer.imported = false;
				wmtsLayer.layer_name = externalLayer['name'];
				wmtsLayer.title = externalLayer['title'];
	    		wmtsLayer.infoFormat = externalLayer['infoformat'];
	    		wmtsLayer.detailed_info_enabled = externalLayer['detailed_info_enabled'];
	    		wmtsLayer.detailed_info_button_title = externalLayer['detailed_info_button_title'];
	    		wmtsLayer.detailed_info_html = externalLayer['detailed_info_html'];
	    		wmtsLayer.setZIndex(parseInt(externalLayer.order));
				self.map.addLayer(wmtsLayer);
			
    		} catch(err){
    			console.log(err);
    			
    		}
		}

    	if (externalLayer['type'] == 'Bing') {
    		var bingLayer = new ol.layer.Tile({
				id: layerId,
				visible: visible,
				label: externalLayer['layers'],
				preload: Infinity,
				source: new ol.source.BingMaps({
					key: externalLayer['key'],
					imagerySet: externalLayer['layers']
				})
			});
			bingLayer.baselayer = baselayer;
			bingLayer.layer_name = externalLayer['name'];
			bingLayer.setZIndex(parseInt(externalLayer.order));
			bingLayer.external = true;
			bingLayer.imported = false;
			this.map.addLayer(bingLayer);
    	}

    	if (externalLayer['type'] == 'OSM') {
    		var osm_source = null;
    		if('url' in externalLayer && externalLayer['url'].length > 0){
    			osm_source = new ol.source.OSM({
    				url: externalLayer['url'],
    				crossOrigin: 'anonymous'
    			})
    		}else{
    			osm_source = new ol.source.OSM();
    		}
    		var osm = new ol.layer.Tile({
        		id: layerId,
            	label: externalLayer['title'],
              	visible: visible,
              	source: osm_source
            });
    		osm.baselayer = baselayer;
    		osm.external = true;
    		osm.imported = false;
			osm.layer_name = externalLayer['name'];
    		osm.setZIndex(parseInt(externalLayer.order));
			this.map.addLayer(osm);
		}

    	if (externalLayer['type'] == 'XYZ') {
    		key = externalLayer['key']
			
			if (key){
				url = externalLayer['url'] + '?apikey=' + key
			}else{
				url = externalLayer['url']
			}
			
			var xyz = new ol.layer.Tile({
    			id: layerId,
    			label: externalLayer['title'],
    		  	visible: visible,
    		  	source: new ol.source.XYZ({
    		  		url: url,
    		  		crossOrigin: 'anonymous'
    		    })
    		});
    		xyz.baselayer = baselayer;
    		xyz.external = true;
    		xyz.imported = false;
			xyz.layer_name = externalLayer['name'];
    		xyz.setZIndex(parseInt(externalLayer.order));
			this.map.addLayer(xyz);
		}

	},

	_loadInternalLayer: function(internalLayer, group, checkTileLoadError) {
		var self = this;

		var layerConf = internalLayer;
		var layerId = this._nextLayerId();
		layerConf.id = layerId;
		var url = layerConf.wms_url;
		if (layerConf.cached) {
			url = layerConf.cache_url;
		}
		var wmsLayer = null;

		var visible = false;
	    var baselayer = false;
	    if (internalLayer['baselayer']) {
	    	baselayer = true;
	    	if (internalLayer['default_baselayer']) {
	    		visible = true;
	    	}
	    } else {
	    	visible = internalLayer['visible'];
	    }
	    if(group.visible){ visible = false; }

	    var format = 'image/png';
	    if (layerConf.format) {
	    	format = internalLayer['format'];
	    }
		var customLoadFunction = function(image, src) {
			var xhr = new XMLHttpRequest();
			xhr.open("GET", src);
			if (self.conf.user && self.conf.user.token) { // FIXME: this is just an OIDC test. We must properly deal with refresh tokens etc
				var bearer_token = "Bearer " + self.conf.user.token;
				xhr.setRequestHeader('Authorization', bearer_token);
			}
			xhr.responseType = "blob";
			xhr.onload = function () {
				if (xhr.status == 401) {
					console.log(xhr.getAllResponseHeaders());
					messageBox.show("error", "Geoserver session has expired. Logout from gvSIG Online and login again to reset the session");
				}
				else if (xhr.status == 403) {
					console.log(xhr.getAllResponseHeaders());
					messageBox.show("error", "You are not allowed to read the layer or Geoserver session has expired. Logout from gvSIG Online and login again to reset the session");
				}
				else if (xhr.getResponseHeader("content-type").indexOf("application/vnd.ogc.se_xml") !== -1) {
					// returned in cross-domain requests instead of the 401 error
					console.log(xhr.status)
					console.log(xhr.getAllResponseHeaders());
					const reader = new FileReader();

					// This fires after the blob has been read/loaded.
					reader.addEventListener('loadend', (e) => {
						const text = reader.result;
						var parser = new DOMParser();
						xmlDoc = parser.parseFromString(text, "text/xml");
						var exception = xmlDoc.getElementsByTagName("ServiceException");
						if (exception && exception.length>0) {
							if (exception[0].getAttribute('code') == 'LayerNotDefined') {
								messageBox.show("error", "The layer does not exists or Geoserver session has expired. Logout from gvSIG Online and login again to reset the session");
							}
						}
					});
					reader.readAsText(this.response);
				}
				var urlCreator = window.URL || window.webkitURL;
				var imageUrl = urlCreator.createObjectURL(this.response);
				image.getImage().src = imageUrl;
			};
			xhr.send();
		};
		if (layerConf.single_image) {
			var wmsSource = new ol.source.ImageWMS({
				url: url,
				visible: layerConf.visible,
				params: {'LAYERS': layerConf.workspace + ':' + layerConf.name, 'FORMAT': format, 'VERSION': '1.1.1'},
				serverType: 'geoserver'
			});
			if (self.conf.user && self.conf.user.token) { // FIXME: this is just an OIDC test. We must properly deal with refresh tokens etc
				wmsSource.setImageLoadFunction(customLoadFunction);
			};
			wmsLayer = new ol.layer.Image({
				id: layerId,
				source: wmsSource,
				visible: visible
			});

		} else {
			if(url.endsWith('/gwc/service/wmts')){
				var default_srs = 'EPSG:3857';
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


				var wmtsSource = new ol.source.WMTS({
					layer: layerConf.workspace + ':' + layerConf.name,
					url: url,
					projection: projection,
					matrixSet: default_srs,
					format:format,
					tileGrid: tileGrid,
					wrapX: true
				});
				if (self.conf.user && self.conf.user.token) { // FIXME: this is just an OIDC test. We must properly deal with refresh tokens etc
					wmtsSource.setTileLoadFunction(customLoadFunction);
				};
		        var wmsLayer = new ol.layer.Tile({
			 		id: layerId,
			 		source: wmtsSource,
			 		visible: visible
			 	});
		        wmsLayer.baselayer = baselayer;
		        wmsLayer.layer_name=layerConf.workspace + ':' + layerConf.name;

			}else{
				var wmsParams = {
					'LAYERS': layerConf.workspace + ':' + layerConf.name,
					'FORMAT': format,
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
				if (self.conf.user && self.conf.user.token) { // FIXME: this is just an OIDC test. We must properly deal with refresh tokens etc
					wmsSource.setTileLoadFunction(customLoadFunction);
				};
				
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
			wmsLayer.id = layerId;
			wmsLayer.baselayer = baselayer;
			wmsLayer.layer_name = layerConf.name;
			wmsLayer.wms_url = layerConf.wms_url;
			wmsLayer.wms_url_no_auth = layerConf.wms_url_no_auth;
			wmsLayer.wfs_url = layerConf.wfs_url;
			wmsLayer.wcs_url = layerConf.wcs_url;
			wmsLayer.wfs_url_no_auth = layerConf.wfs_url_no_auth;
			wmsLayer.cache_url = layerConf.cache_url;
			wmsLayer.title = layerConf.title;
			wmsLayer.abstract = layerConf.abstract;
			wmsLayer.detailed_info_enabled = layerConf.detailed_info_enabled;
			wmsLayer.detailed_info_button_title = layerConf.detailed_info_button_title;
			wmsLayer.detailed_info_html = layerConf.detailed_info_html;
			wmsLayer.metadata = layerConf.metadata || '';
			wmsLayer.metadata_url = layerConf.metadata_url || '';
			wmsLayer.legend = layerConf.legend;
			wmsLayer.legend_no_auth = layerConf.legend_no_auth;
			wmsLayer.legend_graphic = layerConf.legend_graphic;
			wmsLayer.legend_graphic_no_auth = layerConf.legend_graphic_no_auth;
			wmsLayer.queryable = layerConf.queryable;
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
			wmsLayer.external = false;
			wmsLayer.imported = false;
			wmsLayer.allow_download = layerConf.allow_download;

			var latLong = new Array();
			for (i in layerConf.latlong_extent.split(',')) {
				latLong.push(parseFloat(layerConf.latlong_extent.split(',')[i]));
			}
			wmsLayer.latlong_extent = latLong;
			wmsLayer.time_resolution = layerConf.time_resolution;

			wmsLayer.setOpacity(layerConf.opacity);
			this.map.addLayer(wmsLayer);

			wmsLayer.getSource().layer_name = layerConf.name;

			if (checkTileLoadError) {
				wmsLayer.getSource().loadend = false;
				wmsLayer.getSource().on('tileloadstart', function() {
					var time = 0;
					var pid;
					var _this = this;

					var iLayer = null;
					self.map.getLayers().forEach(function(layer){
						if (layer.layer_name) {
							if (layer.layer_name === _this.layer_name) {
								iLayer = layer;
							}
						}
												
					}, _this);
					self._setTileLoadError(false, iLayer);

					pid = setInterval(function() {
						if (time < layerConf.timeout) {
							time += 1000;
						} else {
							if (!_this.loadend) {
								clearInterval(pid);
								if (iLayer) {
									self._setTileLoadError(true, iLayer);
								}

							}
		
						}
					}, 1000);
				
				});
				wmsLayer.getSource().on('tileloadend', function() {
					this.loadend = true;
				
				});
				wmsLayer.getSource().on('tileloaderror', function(e){
					console.log(e);
					var aux = self._check_error_is_TileOutOfRange(e.tile);
					if (aux){
						return;
					}
					var iLayer = null;
					self.map.getLayers().forEach(function(layer){
						if (layer.layer_name) {
							if (layer.layer_name === this.layer_name) {
								iLayer = layer;
							}
						}						
					}, this);								
					if (iLayer) {
						self._setTileLoadError(true, iLayer);
					}								
				});	
			}

			if (layerConf.real_time) {
				var updateInterval = layerConf.update_interval;
				setInterval(function() {
					wmsLayer.getSource().updateParams({"_time": Date.now()});
				}, updateInterval);
			}
		}
	},

	_setTileLoadError: function(tileLoadError, layer){
		/*$('#' + eLayer.id).parent().css('color', '#ff0000');
		$('#' + eLayer.id).parent().children('input').prop( "checked", false );
		$('#' + eLayer.id).parent().children('input').css( "display", 'none' );
		var exclamation = $('#' + eLayer.id).parent().find('i.fa-exclamation-triangle');
		if (!exclamation) {
			$('#' + eLayer.id).parent().prepend('<i style="font-color: red;" class="fa fa-exclamation-triangle"></i>');
		}*/
		if (tileLoadError) {
			$('#' + layer.id).parent().css('color', '#ff0000');
			$('#' + layer.id).parent().children('input').prop( "checked", false );
			//$('#' + layer.id).parent().prepend('<i style="font-color: red;" class="fa fa-exclamation-triangle"></i>');
			layer.setVisible(false);

		} else {
			$('#' + layer.id).parent().css('color', '#444');

		}
	},

	//check if tile error is caused by a TileOutOfRange
	_check_error_is_TileOutOfRange: function(tile){
		var is_tileoutofrange;
		var tile_url = tile.getImage().src;
		$.ajax({
			url: tile_url,
			async: false,
			timeout: 3000,
			method: 'GET',
			//headers: {
			//	"Authorization": "Basic " + btoa(self.conf.user.credentials.username + ":" + self.conf.user.credentials.password)
			//},
			error: function(error){
				if (error.responseText && error.responseText.indexOf("TileOutOfRange") == -1){
					is_tileoutofrange =  false;
					//TileState.ERROR = 3
					//tile.setState(3);
				}else{
					is_tileoutofrange = true;
				}
			},
			success: function(resp){
				is_tileoutofrange = false;
			}
		});
		return is_tileoutofrange;		
	},

	_loadLayerGroups: function() {
		var self = this;
		for (var i=0; i<this.conf.layerGroups.length; i++) {
			var group = this.conf.layerGroups[i];
			if (!group.basegroup && group.allows_getmap) {
				var url = null;
				var params = null;
				var cached = group.cached;

				if (cached) {
					url = group.cache_endpoint;
					params = {'LAYERS': group.groupName, 'FORMAT': 'image/png', 'VERSION': '1.1.1', 'TILED': 'TRUE', 'WIDTH': '256', 'HEIGHT': '256'};
				} else {
					url = group.wms_endpoint;
					params = {'LAYERS': group.groupName, 'FORMAT': 'image/png', 'VERSION': '1.1.0', 'WIDTH': '256', 'HEIGHT': '256'};
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
		}
	},

	_loadTools: function() {
		if (this.ifToolInConf('gvsigol_tool_navigationhistory')) {
			this.tools.push(new navigationHistory(this.map, this.conf));
		}
		if (this.ifToolInConf('gvsigol_tool_zoom')) {
			this.tools.push(new projectZoom(this.map, this.conf));
			this.tools.push(new DragZoomControl(this.map, this.conf));
		}
		if (this.ifToolInConf('gvsigol_tool_info')) {
			this.tools.push(new getFeatureInfo(this.conf, this.map, this.conf.tools.get_feature_info_control.private_fields_prefix));
		}
		if (this.ifToolInConf('gvsigol_tool_measure')) {
			//this.tools.push(new measureLength(this.map));
			//this.tools.push(new measureArea(this.map));
			//this.tools.push(new measureAngle(this.map));
			
			new MeasureToolBar(this.map);
		}
		/*if (this.ifToolInConf('gvsigol_tool_export')) {
			this.tools.push(new exportToPDF(this.conf, this.map));
		}*/
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
			//this.tools.push(new selectFeature(this.map, this));
			//this.tools.push(new selectFeatureByBuffer(this.map, this));
			new SelectToolBar(this.map);
		}
		this.tools.push(new cleanMap(this.map, this));

    	this.map.tools = this.tools;
	},
	
	getSelectionTable: function() {
    	return this.selectionTable;
    },

	setSelectionTable: function(table) {
    	this.selectionTable = table;
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
    
    setActiveToolbar: function(activeToolBar){
    	this.activeToolbar = activeToolBar;
    },
    
    getActiveToolbar: function(activeToolBar){
    	return this.activeToolbar;
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
    },
    

	getDownloadManager: function() {
		if (this.downloadManager === undefined) {
			this.downloadManager = new DownloadManagerUI();
		}
		return this.downloadManager;
	},

	disableTools: function(exceptTool, disableEditionControls) {
		if (disableEditionControls != false) { //in case not defined
			disableEditionControls = true;
		}
		if (exceptTool instanceof ol.control.Control) {
			var exceptToolObj = exceptTool;
			var exceptToolId = null;
		}
		else {
			var exceptToolObj = null;
			var exceptToolId = exceptTool;
		}
		for (var i=0; i<this.tools.length; i++){
			if (!exceptToolId || (exceptToolId != this.tools[i].id)) {
				if (this.tools[i].deactivable == true) {
					if (this.tools[i].active) {
						this.tools[i].deactivate();
					}
				}
			}
		}
		if (viewer.core.getActiveToolbar() != null) {
			var activeControls = viewer.core.getActiveToolbar().getActiveControls();
			for (i=0; i<activeControls.length; i++) {
				if (!exceptToolObj || (exceptToolObj != activeControls[i])) {
					activeControls[i].setActive(false);
				}
			}
		}
		if (disableEditionControls && this.layerTree.getEditionBar()) {
			this.layerTree.getEditionBar().deactivateControls();
		}
	}
}
