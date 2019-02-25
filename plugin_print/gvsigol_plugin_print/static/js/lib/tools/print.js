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
var print = function(printProvider, conf, map) {
	var self = this;
	this.printProvider = printProvider;
	this.conf = conf;
	this.map = map;

	this.id = "print";
	this.$button = $("#print");

	this.detailsTab = $('#details-tab');

	this.lastAngle = 0;
	this.extentLayer = null;
	this.capabilities = null;

	var this_ = this;
	var handler = function(e) {
		this_.handler(e);
	};

	this.$button.on('click', handler);
	this.$button.on('touchstart', handler);

};

/**
 * TODO
 */
print.prototype.active = false;

/**
 * TODO
 */
print.prototype.deactivable = true;

/**
 * @param {Event} e Browser event.
 */
print.prototype.handler = function(e) {
	e.preventDefault();
	var self = this;

	if (!this.active) {
		this.extentLayer = new ol.layer.Vector({
			source: new ol.source.Vector()
		});
		this.map.addLayer(this.extentLayer);

		this.showDetailsTab();
		this.detailsTab.empty();

		this.capabilities = this.getCapabilities('a4_landscape');
		this.renderPrintExtent(this.capabilities.layouts[0].attributes[3].clientInfo);
		var eventKey = this.map.getView().on('propertychange', function() {
	        self.extentLayer.getSource().clear();
	        self.lastAngle = 0;
	        self.renderPrintExtent(self.capabilities.layouts[0].attributes[3].clientInfo);
	    });

		var templates = this.getTemplates();

		var ui = '';
		ui += '<div class="box box-default">';
		ui += 	'<div class="box-header with-border">';
		ui += 		'<h3 class="box-title">' + gettext('Print params') + '</h3>';
		ui += 	'</div>';
		ui += 	'<div class="box-body">';
		ui += 		'<div id="field-errors" class="row"></div>';
		ui += 		'<div class="row">';
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Select print template') + '</label>';
		ui += 				'<select id="print-template" class="form-control">';
		ui += 					'<option disabled selected value="empty"> -- ' + gettext('Select template') + ' -- </option>';
		for (var i=0; i<templates.length; i++) {
			if (templates[i] != 'default' && templates[i] != 'a4_landscape_att') {
				if (templates[i] == 'a4_landscape') {
					ui += 	'<option value="' + templates[i] + '" selected>' + templates[i] + '</option>';
				} else {
					ui += 	'<option value="' + templates[i] + '">' + templates[i] + '</option>';
				}
			}
		}
		ui += 				'</select>';
		ui += 			'</div>';
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Title') + '</label>';
		ui += 				'<input id="print-title" type="text" class="form-control" value="' + this.conf.project_title + '">';
		ui += 			'</div>';
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Resolution') + '</label>';
		ui += 				'<select id="print-dpi" class="form-control">';
		ui += 					'<option value="180">180 dpi</option>';
		ui += 					'<option selected value="240">240 dpi</option>';
		ui += 					'<option value="320">320 dpi</option>';
		ui += 					'<option value="400">400 dpi</option>';
		ui += 				'</select>';
		ui += 			'</div>';
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Rotation') + '</label>';
		ui += 				'<input id="print-rotation" type="number" step="any" class="form-control" value="0">';
		ui += 			'</div>';
		ui += 			'<div class="col-md-12 form-group">';
		ui += 				'<label>' + gettext('Legal warning') + '</label>';
		ui += 				'<textarea class="form-control" name="print-legal" id="print-legal" rows="5">' + this.printProvider.legal_advice + '</textarea>';
		ui += 			'</div>';
		ui += 		'</div>';
		ui += 	'</div>';
		ui += 	'<div class="box-footer clearfix">';
		ui += 		'<a href="javascript:void(0)" id="accept-print" class="btn btn-sm btn-primary btn-flat pull-right"><i class="fa fa-print margin-r-5"></i>' + gettext('Print') + '</a>';
		ui += 		'<a href="javascript:void(0)" id="cancel-print" class="btn btn-sm btn-danger btn-flat pull-right margin-r-10"><i class="fa fa-times margin-r-5"></i>' + gettext('Cancel') + '</a>';
		ui += 	'</div>';
		ui += '</div>';

		this.detailsTab.append(ui);
		$.gvsigOL.controlSidebar.open();

		$('#print-template').on('change', function(e) {
			var template = $('#print-template').val();
			self.capabilities = self.getCapabilities(template);

			self.extentLayer.getSource().clear();
	        self.lastAngle = 0;
	        self.renderPrintExtent(self.capabilities.layouts[0].attributes[3].clientInfo);
		});

		$('#print-rotation').on('change', function(e) {
			var feature = self.extentLayer.getSource().getFeatures()[0];
		    var center = self.map.getView().getCenter();
		    var radiansAngle = (this.value * 2 * Math.PI) / 360;
		    var radiansLastAngle = ((360-self.lastAngle) * 2 * Math.PI) / 360;
		    feature.getGeometry().rotate(radiansLastAngle, center);
			feature.getGeometry().rotate(radiansAngle, center);
			self.extentLayer.getSource().dispatchEvent('change');
			self.lastAngle = this.value;
		});

		$('#accept-print').on('click', function () {
			var template = $('#print-template').val();
			if (template != null) {
				$("body").overlay();
				self.createPrintJob(template);
			} else {
				messageBox.show('warning', gettext('You must select a template'));
			}

		});

		$('#cancel-print').on('click', function () {
			ol.Observable.unByKey(eventKey);
			self.removeExtentLayer();
			self.showLayersTab();
			self.capabilities = null;
			self.active = false;
		});

		this.active = true;
	}
};

/**
 * TODO
 */
print.prototype.createPrintJob = function(template) {
	var self = this;
	var title = $('#print-title').val();
	var legalWarning = $('#print-legal').val();
	var rotation = $('#print-rotation').val();
	var dpi = $('#print-dpi').val();

	var mapLayers = this.map.getLayers().getArray();
	var printLayers = new Array();
	var legends = new Array();
	for (var i=0; i<mapLayers.length; i++) {
		if (!mapLayers[i].baselayer && mapLayers[i].layer_name != 'plg_catastro' && !(mapLayers[i] instanceof ol.layer.Vector)) {
			if (mapLayers[i].getVisible()) {
				var layer = null;
				if(mapLayers[i].getSource() instanceof ol.source.WMTS){
					var initialScale = 559082263.950892933;
					var scale = 0;
					var matrices = new Array();
					var tileGrid = mapLayers[i].getSource().getTileGrid();
					var lastSize = 1;
					for (var z = 0; z < 18; ++z) {
						var matrixSize = new Array();
						if (z == 0) {
							matrixSize.push(1);
							matrixSize.push(1);
							scale = initialScale;

						} else if (z >= 1) {
							lastSize = lastSize*2;
							matrixSize.push(lastSize*2);
							matrixSize.push(lastSize*2);
							scale = scale / 2;
						}
						matrices.push({
				            "identifier": tileGrid.getMatrixId(z),
				            "matrixSize": matrixSize,
				            "scaleDenominator": scale,
				            //"tileSize": [tileGrid.getTileSize(), tileGrid.getTileSize()],
				            "tileSize": tileGrid.tmpSize_,
				            "topLeftCorner": [-2.003750834E7, 2.0037508E7]
						});
					}

					layer = {
							"type": "WMTS",
					        "baseURL":mapLayers[i].getSource().getUrls()[0],
					        "opacity": mapLayers[i].getOpacity(),
					        "layer": mapLayers[i].getSource().getLayer(),
					        "version": "1.0.0",
					        "requestEncoding": "KVP",
					        "dimensions": mapLayers[i].getSource().getDimensions(),
					        "dimensionParams": {},
					        "matrixSet": mapLayers[i].getSource().getMatrixSet(),
					        "matrices": matrices,
					        "customParams": {
				  				"TRANSPARENT": "true"
				  			},
					        "imageFormat": "image/png"
				  	    };
					if (mapLayers[i].getSource().getStyle()) {
						layer['styles'] = [mapLayers[i].getSource().getStyle()];
					}
//					if (mapLayers[i].getSource().getDimensions() && "TIME" in mapLayers[i].getSource().getDimensions()) {
//						layer['customParams']['TIME'] = mapLayers[i].getSource().getDimensions()['TIME'];
//					}
//					if (mapLayers[i].isLayerGroup) {
//						layer['layers'] = [mapLayers[i].layer_name];
//					} else {
//						layer['layers'] = [mapLayers[i].workspace + ':' + mapLayers[i].layer_name];
//					}
				}else{
					layer = {
							//"baseURL": "http://localhost/gs-local/ws_jrodrigo/wms",
							"baseURL": mapLayers[i].wms_url_no_auth,
					  	    "opacity": mapLayers[i].getOpacity(),
					  	    "type": "WMS",
				  			"imageFormat": "image/png",
				  			"customParams": {
				  				"TRANSPARENT": "true"
				  			},
							"mergeableParams": {},
				  	    };
					if (mapLayers[i].getSource().getParams()['STYLES']) {
						layer['styles'] = [mapLayers[i].getSource().getParams()['STYLES']];
					}
					if (mapLayers[i].getSource().getParams()['TIME']) {
						layer['customParams']['TIME'] = mapLayers[i].getSource().getParams()['TIME'];
					}
					if (mapLayers[i].isLayerGroup) {
						layer['layers'] = [mapLayers[i].layer_name];
					} else {
						layer['layers'] = [mapLayers[i].workspace + ':' + mapLayers[i].layer_name];
					}
				}

				if(layer){
					printLayers.push(layer);
				}

				var legend = {
					"name": mapLayers[i].title,
		            "icons": [mapLayers[i].legend_no_auth]
		        };
				/*var legend = {
					"name": mapLayers[i].title,
			        "icons": ["http://localhost:8080/geoserver/ws_jrodrigo/wms?SERVICE=WMS&VERSION=1.1.1&layer=lista_repetidores&REQUEST=getlegendgraphic&FORMAT=image/png"]
			    };*/
				legends.push(legend);
			}
		}
	}

	var baseLayers = this.map.getLayers().getArray();
	for (var i=0; i<baseLayers.length; i++) {
		if (baseLayers[i].baselayer) {
			if (baseLayers[i].getVisible()) {
				if (baseLayers[i].getSource().urls) {
					if(baseLayers[i].getSource().getUrls()[0].indexOf('data:image/gif;base64') == -1) {
						console.log(baseLayers[i]);
						if (baseLayers[i].getSource() instanceof ol.source.OSM) {
							printLayers.push({
								"baseURL": "http://a.tile.openstreetmap.org",
						  	    "type": "OSM",
						  	    "imageExtension": "png"
							});

						} else if (baseLayers[i].getSource() instanceof ol.source.WMTS) {
							var initialScale = 559082263.950892933;
							var scale = 0;
							var matrices = new Array();
							var tileGrid = baseLayers[i].getSource().getTileGrid();
							var lastSize = 1;
							for (var z = 0; z < 18; ++z) {
								var matrixSize = new Array();
								if (z == 0) {
									matrixSize.push(1);
									matrixSize.push(1);
									scale = initialScale;

								} else if (z >= 1) {
									lastSize = lastSize*2;
									matrixSize.push(lastSize*2);
									matrixSize.push(lastSize*2);
									scale = scale / 2;
								}
								var tileSize = 256;
								if (tileGrid.getTileSize()) {
									tileSize = tileGrid.getTileSize();
								}
								matrices.push({
						            "identifier": tileGrid.getMatrixId(z),
						            "matrixSize": matrixSize,
						            "scaleDenominator": scale,
						            "tileSize": [tileSize, tileSize],
						            //"tileSize": tileGrid.tmpSize_,
						            "topLeftCorner": [-2.003750834E7, 2.0037508E7]
								});
							}
							printLayers.push({
								"type": "WMTS",
						        "baseURL": baseLayers[i].getSource().getUrls()[0],
						        "opacity": 1.0,
						        "layer": baseLayers[i].getSource().getLayer(),
						        "version": "1.0.0",
						        "requestEncoding": "KVP",
						        "dimensions": null,
						        "dimensionParams": {},
						        "matrixSet": baseLayers[i].getSource().getMatrixSet(),
						        "matrices": matrices,
						        "imageFormat": "image/png"
							});

						} else if (baseLayers[i].getSource() instanceof ol.source.TileWMS) {
							printLayers.push({
								"type": "WMS",
						        "layers": [baseLayers[i].getSource().getParams()['LAYERS']],
						        "baseURL": baseLayers[i].getSource().getUrls()[0],
						        "imageFormat": baseLayers[i].getSource().getParams()['FORMAT'],
						        "version": baseLayers[i].getSource().getParams()['VERSION'],
						        "customParams": {
						        	"TRANSPARENT": "true"
						        }
							});

						} else if (baseLayers[i].getSource() instanceof ol.source.XYZ) {
							printLayers.push({
								"baseURL": baseLayers[i].getSource().getUrls()[0],
							    "type": "OSM",
							    "imageExtension": "jpg"
							});
						}
					}
				}
			}
		}
	}
	var f = self.renderPrintExtent(self.capabilities.layouts[0].attributes[3].clientInfo);
	$.ajax({
		type: 'POST',
		async: true,
	  	url: self.printProvider.url + '/print/' + template + '/report.pdf',
	  	processData: false,
	    contentType: 'application/json',
	  	data: JSON.stringify({
	  		"layout": self.capabilities.layouts[0].name,
		  	"outputFormat": "pdf",
		  	"attributes": {
		  		"title": title,
		  		"legalWarning": legalWarning,
		  		"map": {
		  			"projection": "EPSG:3857",
		  			"dpi": parseInt(dpi),
		  			"rotation": rotation,
		  			//"center": self.map.getView().getCenter(),
		  			"scale": self.getCurrentScale(parseInt(dpi)),
		  			"layers": printLayers,
		  			"bbox": f.getGeometry().getExtent()
		  	    },
		  	    "logo_url": self.conf.project_image,
		  	    //"logo_url": "https://demo.gvsigonline.com/media/images/igvsb.jpg",
		  	    "legend": {
		  	    	"name": "",
		            "classes": legends
		        },
		        "crs": "EPSG:3857",
		  	}
		}),
	  	success	:function(response){
	  		self.getReport(response);
	  	},
	  	error: function(){}
	});

};

print.prototype.getCurrentScale = function (dpi) {
    var resolution = this.map.getView().getResolution();
    var units = this.map.getView().getProjection().getUnits();
    var mpu = ol.proj.METERS_PER_UNIT[units];
    var scale = resolution * mpu * 39.37 * dpi;
    return Math.round(scale);
};

/**
 * TODO
 */
print.prototype.getReport = function(reportInfo) {
	var self = this;
	$.ajax({
		type: 'GET',
		async: true,
	  	url: self.printProvider.url + reportInfo.statusURL,
	  	success	:function(response){
	  		if (response.done) {
	  			$.overlayout();
	  			window.open(reportInfo.downloadURL);
	  		} else {
	  			window.setTimeout(self.getReport(reportInfo), 3000);
	  		}
	  	},
	  	error: function(){}
	});
};

/**
 * TODO
 */
print.prototype.getTemplates = function() {
	var templates = null;
	$.ajax({
		type: 'GET',
		async: false,
	  	url: this.printProvider.url + '/print/apps.json',
	  	success	:function(response){
	  		templates = response;
	  	},
	  	error: function(){}
	});
	return templates;
};

/**
 * TODO
 */
print.prototype.getCapabilities = function(template) {
	var capabilities = null;
	$.ajax({
		type: 'GET',
		async: false,
	  	url: this.printProvider.url + '/print/' + template + '/capabilities.json',
	  	success	:function(response){
	  		capabilities = response;
	  	},
	  	error: function(){}
	});
	return capabilities;
};

/**
 * TODO
 */
print.prototype.renderPrintExtent = function(clientInfo) {
    var mapComponentWidth = this.map.getSize()[0];
    var mapComponentHeight = this.map.getSize()[1];
    var currentMapRatio = mapComponentWidth / mapComponentHeight;
    var scaleFactor = 0.6;
    var desiredPrintRatio = clientInfo.width / clientInfo.height;
    var targetWidth;
    var targetHeight;
    var geomExtent;
    var feat;

    if (desiredPrintRatio >= currentMapRatio) {
        targetWidth = mapComponentWidth * scaleFactor;
        targetHeight = targetWidth / desiredPrintRatio;
    } else {
        targetHeight = mapComponentHeight * scaleFactor;
        targetWidth = targetHeight * desiredPrintRatio;
    }

    geomExtent = this.map.getView().calculateExtent([
        targetWidth,
        targetHeight
    ]);
    feat = new ol.Feature(ol.geom.Polygon.fromExtent(geomExtent));
    this.extentLayer.getSource().addFeature(feat);
    return feat;
};

/**
 * TODO
 */
print.prototype.deactivate = function() {
	this.$button.removeClass('button-active');
	this.active = false;
};

/**
 * TODO
 */
print.prototype.showDetailsTab = function(p,f) {
	$('.nav-tabs a[href="#details-tab"]').tab('show');
};

/**
 * @param {Event} e Browser event.
 */
print.prototype.removeExtentLayer = function() {
	this.extentLayer.getSource().clear();
	this.map.removeLayer(this.extentLayer);

};

/**
 * TODO
 */
print.prototype.showLayersTab = function(p,f) {
	this.detailsTab.empty();
	$('.nav-tabs a[href="#layer-tree-tab"]').tab('show');
};